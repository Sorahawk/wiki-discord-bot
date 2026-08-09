from imports import *


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
		raise RuntimeError(f"failed to edit {title}: {response['error']}")

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


# reconciles the wiki repo against the wiki in both directions
# the side that changed this cycle wins; if both changed or neither did, the page is held as a conflict
async def run_sync(full_scan=False):
	async with var_global.REPO_LOCK:
		await reset_to_remote()
		head_sha = await get_head_sha()

		repo_titles, wiki_titles, timestamp = await resolve_sync_scope(full_scan)
		scope = None if repo_titles is None else repo_titles | wiki_titles | var_global.TRACKED_CONFLICTS

		local_by_title, file_by_title = collect_local_pages(scope)
		changed, missing = await diff_against_wiki(local_by_title)

		pushed, pulled, created, conflicted, resolved = [], [], [], [], []

		# a missing page has nothing to conflict with, so it is always created
		for title in missing:
			full_path, rel_path = file_by_title[title]

			await push_page(title, local_by_title[title], full_path, rel_path, head_sha)
			created.append(title)
			var_global.TRACKED_CONFLICTS.discard(title)

		for title, (local_content, live_content) in changed.items():
			full_path, rel_path = file_by_title[title]

			repo_changed = repo_titles is not None and title in repo_titles
			wiki_changed = wiki_titles is not None and title in wiki_titles
			was_conflicted = title in var_global.TRACKED_CONFLICTS

			# both sides changed, or neither did, so there is no signal to arbitrate on
			if repo_changed == wiki_changed:
				if not was_conflicted:
					conflicted.append(title)

				var_global.TRACKED_CONFLICTS.add(title)
				continue

			if repo_changed:
				await push_page(title, local_content, full_path, rel_path, head_sha)
				pushed.append(title)
			else:
				full_path.write_text(live_content, encoding='utf-8')
				pulled.append(title)

			if was_conflicted:
				var_global.TRACKED_CONFLICTS.discard(title)
				resolved.append((title, 'repo' if repo_changed else 'wiki'))

		# both sides agree again, so any conflict on that title was resolved by hand
		missing_set = set(missing)
		for title in local_by_title:
			if title not in changed and title not in missing_set:
				var_global.TRACKED_CONFLICTS.discard(title)

		# a full scan is the only way to see the whole outstanding set, so list it in full
		if full_scan:
			conflicted = sorted(var_global.TRACKED_CONFLICTS)

		if pulled:
			await commit_and_push(PAGES_ROOT, f'{PULL_MARKER} ({len(pulled)} pages)')

		await report_sync(pushed, pulled, created, conflicted, resolved)

		var_global.LAST_RECONCILE_TIMESTAMP = timestamp
		var_global.LAST_RECONCILE_SHA = await get_head_sha()  # read after the pull commit so it stays out of the next diff


# resolves every tracked conflict in one direction, returning the titles acted on
async def resolve_conflicts(push_to_wiki):
	async with var_global.REPO_LOCK:
		if not var_global.TRACKED_CONFLICTS:
			return []

		await reset_to_remote()
		head_sha = await get_head_sha()

		titles = sorted(var_global.TRACKED_CONFLICTS)
		local_by_title, file_by_title = collect_local_pages(set(titles))

		if push_to_wiki:
			for title, local_content in local_by_title.items():
				full_path, rel_path = file_by_title[title]
				await push_page(title, local_content, full_path, rel_path, head_sha)

		else:
			live_by_title = await get_page_content(list(local_by_title))

			for title in local_by_title:
				live_content = live_by_title[title][0]

				if live_content is not None:
					file_by_title[title][0].write_text(live_content, encoding='utf-8')

			await commit_and_push(PAGES_ROOT, f'{PULL_MARKER} ({len(local_by_title)} pages)')

		var_global.TRACKED_CONFLICTS.clear()
		var_global.LAST_RECONCILE_SHA = await get_head_sha()

		return titles


# reports sync activity to Discord, staying silent when there was nothing to do
async def report_sync(pushed, pulled, created, conflicted, resolved):
	if not (pushed or pulled or created or conflicted or resolved):
		return

	var_global.OPERATION_LOGGER.info(
		f'Sync complete - {len(created)} created, {len(pushed)} pushed, {len(pulled)} pulled, {len(conflicted)} conflicted'
	)

	resolved_titles = {title for title, _ in resolved}
	sections = []

	for label, titles in (
		('Created on Wiki', created),
		('Pushed to Wiki', [title for title in pushed if title not in resolved_titles]),
		('Pulled to Repo', [title for title in pulled if title not in resolved_titles]),
		('Awaiting Resolution', conflicted),
	):
		if titles:
			sections.append(f'**{label}:**\n' + '\n'.join(f'- `{title}`' for title in titles))

	if resolved:
		lines = '\n'.join(f'- `{title}` overwritten by {side}' for title, side in resolved)
		sections.append(f'**Conflicts Resolved:**\n{lines}')

	await send_audit_message(var_global.CHANNELS['main'], '## Wiki Sync Report\n\n', '\n\n'.join(sections))
