from imports import *


# describes which side won when a conflict was resolved
def resolution_label(from_repo):
	return f'Overwritten by {"Repo" if from_repo else "Wiki"}'


# holds a title until the underlying problem is fixed, recording it only on the first occurrence
def block_title(title, reason, blocked):
	if title not in var_global.TRACKED_BLOCKED:
		blocked.append((title, reason))

	var_global.TRACKED_BLOCKED[title] = reason
	var_global.TRACKED_UNDECIDED.discard(title)


# fetches live content for the specified titles and compares against local
# returns two items:
# a dict keyed by title, with corresponding value being a tuple (local content, live content)
# and a list of titles with no matching live page
async def diff_against_wiki(local_by_title):
	live_by_title = await get_page_content(list(local_by_title))
	changed, missing = {}, []

	for title, local_content in local_by_title.items():
		live_content = live_by_title[title][0]

		if live_content is None:
			missing.append(title)
		elif live_content != local_content:
			changed[title] = (local_content, live_content)

	return changed, missing


# pushes local content to the wiki, and protects the page if it is a MessageBundle
async def push_page(title, content, full_path, rel_path, head_sha):
	commit_subject = await get_last_commit_subject(rel_path)
	summary = f'{commit_subject} ({PUSH_MARKER} - {head_sha[:7]})'

	response = await edit_page(title, content, summary, content_model=get_content_model(full_path))

	if response.get('error'):
		error = response['error']
		var_global.OPERATION_LOGGER.error(f'Failed to edit {title}: {error}')
		return error.get('info') or error.get('code', 'Unknown error')

	# lock main English source for all MessageBundles
	if title.startswith('MessageBundle:'):
		protection = await get_protection(title)

		if not any(entry['type'] == 'edit' for entry in protection):
			await protect_page(title, reason=MB_PROTECTION_MSG)


# determines which titles changed on each side this cycle
# returns (repo titles, wiki titles, timestamp); None for both sets means compare everything
async def resolve_sync_scope(full_scan):
	timestamp = await get_wiki_timestamp()

	if full_scan or not var_global.LAST_RECONCILE_TIMESTAMP or not var_global.LAST_RECONCILE_SHA:
		return None, None, timestamp

	changed_paths = await get_changed_paths(var_global.LAST_RECONCILE_SHA, PAGES_ROOT)

	# ancestry is broken, so the commit range is unusable and the whole tree must be compared
	if changed_paths is None:
		return None, None, timestamp

	repo_titles = {resolve_title(Path(path)) for path in changed_paths}
	wiki_titles = await get_recent_changes(var_global.LAST_RECONCILE_TIMESTAMP)

	return repo_titles, wiki_titles, timestamp


# reconciles the wiki repo against the wiki in both directions; the side that changed this cycle wins
# if both changed, or neither did, the page is held as undecided
async def run_sync(full_scan=False):
	async with var_global.REPO_LOCK:
		await reset_to_remote()
		head_sha = await get_head_sha()

		repo_titles, wiki_titles, timestamp = await resolve_sync_scope(full_scan)
		scope = None if repo_titles is None else repo_titles | wiki_titles | var_global.TRACKED_UNDECIDED | var_global.TRACKED_BLOCKED.keys()

		local_by_title, file_by_title = collect_local_pages(scope)
		changed, missing = await diff_against_wiki(local_by_title)

		pushed, pulled, created, undecided, blocked, resolved = [], [], [], [], [], []

		# a missing page has nothing to conflict with, so it is always created
		for title in missing:
			full_path, rel_path = file_by_title[title]

			if error := await push_page(title, local_by_title[title], full_path, rel_path, head_sha):
				block_title(title, error, blocked)
				continue

			created.append(title)
			var_global.TRACKED_BLOCKED.pop(title, None)
			var_global.TRACKED_UNDECIDED.discard(title)

		for title, (local_content, live_content) in changed.items():
			full_path, rel_path = file_by_title[title]

			repo_changed = repo_titles and title in repo_titles
			wiki_changed = wiki_titles and title in wiki_titles
			was_undecided = title in var_global.TRACKED_UNDECIDED

			# no signal, or signals on both sides, so there is nothing to arbitrate on
			if repo_changed == wiki_changed:
				if not (was_undecided or title in var_global.TRACKED_BLOCKED):
					undecided.append(title)
					var_global.TRACKED_UNDECIDED.add(title)

				continue

			if repo_changed:
				# a file with merge conflicts is never safe to push, so hold it until the markers are gone
				if MERGE_CONFLICT_MARKER in local_content:
					block_title(title, 'Unresolved merge markers', blocked)
					continue

				if error := await push_page(title, local_content, full_path, rel_path, head_sha):
					block_title(title, error, blocked)
					continue

				pushed.append(title)

			else:
				full_path.write_text(live_content, encoding='utf-8')
				pulled.append(title)

			# the write succeeded, so whatever was holding this title is cleared
			var_global.TRACKED_BLOCKED.pop(title, None)

			if was_undecided:
				var_global.TRACKED_UNDECIDED.discard(title)
				resolved.append((title, resolution_label(repo_changed)))

		# both sides agree again, so anything held on that title was resolved by hand
		missing_set = set(missing)
		for title in local_by_title:
			if title not in changed and title not in missing_set:
				var_global.TRACKED_UNDECIDED.discard(title)
				var_global.TRACKED_BLOCKED.pop(title, None)

		# a full scan is the only way to see the whole outstanding set, so list it in full
		if full_scan:
			undecided = sorted(var_global.TRACKED_UNDECIDED)
			blocked = sorted(var_global.TRACKED_BLOCKED.items())

		# re-read HEAD only when a pull commit moved it, so it stays out of the next diff
		if pulled:
			await commit_and_push(PAGES_ROOT, f'{PULL_MARKER} ({len(pulled)} pages)')
			head_sha = await get_head_sha()

		var_global.LAST_RECONCILE_SHA = head_sha
		var_global.LAST_RECONCILE_TIMESTAMP = timestamp

		return await report_sync(pushed, pulled, created, undecided, blocked, resolved)


# resolves conflicted pages in the specified direction
# returns two lists: the titles written, and the titles still held
async def resolve_conflicts(push_to_wiki):
	async with var_global.REPO_LOCK:
		if push_to_wiki:
			titles = sorted(var_global.TRACKED_UNDECIDED | var_global.TRACKED_BLOCKED.keys())
		else:
			titles = sorted(var_global.TRACKED_UNDECIDED)

		if not titles:
			return [], []

		await reset_to_remote()
		head_sha = await get_head_sha()

		local_by_title, file_by_title = collect_local_pages(set(titles))
		side = resolution_label(push_to_wiki)
		resolved, blocked = [], []

		# can attempt to push blocked pages again
		if push_to_wiki:
			for title, local_content in local_by_title.items():
				full_path, rel_path = file_by_title[title]

				if MERGE_CONFLICT_MARKER in local_content:
					block_title(title, 'Unresolved merge markers', blocked)
					continue

				if error := await push_page(title, local_content, full_path, rel_path, head_sha):
					block_title(title, error, blocked)
					continue

				resolved.append((title, side))
				var_global.TRACKED_BLOCKED.pop(title, None)
				var_global.TRACKED_UNDECIDED.discard(title)

		else:
			live_by_title = await get_page_content(list(local_by_title))

			for title in local_by_title:
				live_content = live_by_title[title][0]

				# nothing to pull, so the title stays held until the repo side is pushed or fixed
				if live_content is None:
					continue

				file_by_title[title][0].write_text(live_content, encoding='utf-8')

				resolved.append((title, side))
				var_global.TRACKED_BLOCKED.pop(title, None)
				var_global.TRACKED_UNDECIDED.discard(title)

			if resolved:
				await commit_and_push(PAGES_ROOT, f'{PULL_MARKER} ({len(resolved)} pages)')

		var_global.LAST_RECONCILE_SHA = await get_head_sha()

		return resolved, blocked


# reports sync activity to Discord, staying silent when there was nothing to do
async def report_sync(pushed, pulled, created, undecided, blocked, resolved, channel=None):
	if not (pushed or pulled or created or undecided or blocked or resolved):
		return False

	var_global.OPERATION_LOGGER.info(''.join([
		'Sync complete - ',
		f'{len(created)} created, ',
		f'{len(pushed)} pushed, ',
		f'{len(pulled)} pulled, ',
		f'{len(undecided)} undecided, ',
		f'{len(blocked)} blocked'
	]))

	resolved_titles = {title for title, _ in resolved}
	sections = []

	for label, titles in (
		('Created on Wiki', created),
		('Pushed to Wiki', [title for title in pushed if title not in resolved_titles]),
		('Pulled to Repo', [title for title in pulled if title not in resolved_titles]),
		('Awaiting Resolution', undecided),
	):
		if titles:
			sections.append(f'**{label}:**\n' + '\n'.join(f'- `{title}`' for title in titles))

	for label, entries in (('Blocked', blocked), ('Conflicts Resolved', resolved)):
		if entries:
			lines = '\n'.join(f'- `{title}` - {detail}' for title, detail in entries)
			sections.append(f'**{label}:**\n{lines}')

	await send_audit_message(channel or var_global.CHANNELS['main'], '## Wiki Sync Report\n\n', '\n\n'.join(sections))
	return True
