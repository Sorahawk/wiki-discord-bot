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


# returns True if the specified revision on the wiki was written by this pipeline
# this means that the repo is now the new version
def is_stale_sync_revision(revision):
	if not revision:
		return False

	user, comment = revision
	return user == BOT_USERNAME and SYNC_SUMMARY_MARKER in comment


# returns the reason a local file is unfit to sync, or None if it passes
def check_push_content(content):
	if not content.strip():
		return 'file is blank'

	if has_conflict_markers(content):
		return 'unresolved merge conflict markers'

	return None


# pushes local content to the wiki, and protects the page if it is a MessageBundle
async def push_page(title, content, full_path, rel_path, head_sha):
	commit_subject = await get_last_commit_subject(rel_path)
	summary = f'{commit_subject} ({SYNC_SUMMARY_MARKER} - {head_sha[:7]})'

	response = await edit_page(title, content, summary, content_model=get_content_model(full_path))

	if response.get('error'):
		raise RuntimeError(f"failed to edit {title}: {response['error']}")

	# lock main English source for all MessageBundles
	if title.startswith('MessageBundle:'):
		protection = await get_protection(title)

		if not any(entry['type'] == 'edit' for entry in protection):
			await protect_page(title, reason=MB_PROTECTION_MSG)


# determines which titles need comparing against the wiki this cycle
# returns the full set of titles to compare, the subset that changed in the repo, and the timestamp to store on success
# None for either set means compare everything
async def resolve_sync_scope(base_sha, full_scan):
	timestamp = await get_wiki_timestamp()

	if full_scan or not var_global.LAST_RECONCILE_TIMESTAMP:
		return None, None, timestamp

	changed_paths = await get_changed_paths(base_sha, PAGES_ROOT)

	# ancestry is broken, so the commit range is unusable and the whole tree must be compared
	if changed_paths is None:
		return None, None, timestamp

	repo_titles = { resolve_title(Path(path)) for path in changed_paths }
	titles = await get_recent_changes(var_global.LAST_RECONCILE_TIMESTAMP) | repo_titles

	return titles, repo_titles, timestamp


# reconciles the wiki repo against the wiki in both directions
# the repo wins where the wiki's latest edit was from this code, else the wiki wins
async def run_sync(full_scan=False):
	async with var_global.REPO_LOCK:
		base_sha = await get_head_sha()
		await reset_to_remote()
		head_sha = await get_head_sha()

		var_global.OPERATION_LOGGER.info(f'base={base_sha[:7]} head={head_sha[:7]} full_scan={full_scan}')

		titles, repo_titles, timestamp = await resolve_sync_scope(base_sha, full_scan)
		local_by_title, file_by_title = collect_local_pages(titles)

		changed, missing = await diff_against_wiki(local_by_title)
		revisions = await get_last_revisions(list(changed))

		pushed, pulled, created, skipped = [], [], [], []

		for title in missing:
			full_path, rel_path = file_by_title[title]
			local_content = local_by_title[title]

			if reason := check_push_content(local_content):
				skipped.append((title, f'Not created ({reason})'))
				continue

			await push_page(title, local_content, full_path, rel_path, head_sha)
			created.append(title)

		if not repo_titles:  # None means the whole tree is in scope, so no commit range is available to compare against
			repo_titles = set()

		for title, (local_content, live_content) in changed.items():
			full_path, rel_path = file_by_title[title]

			var_global.OPERATION_LOGGER.info(f'{title}: in_repo_titles={title in repo_titles} live_blank={not live_content.strip()} local_len={len(local_content)} revision={revisions.get(title)}')

			if is_stale_sync_revision(revisions.get(title)) or (title in repo_titles and not live_content.strip()):
				if reason := check_push_content(local_content):
					skipped.append((title, f'Push prevented ({reason})'))
					continue

				await push_page(title, local_content, full_path, rel_path, head_sha)
				pushed.append(title)
				continue

			if not live_content.strip():
				skipped.append((title, 'Pull prevented (Live page is blank)'))
				continue

			full_path.write_text(live_content, encoding='utf-8')
			pulled.append(title)

		if pulled:
			await commit_and_push(PAGES_ROOT, f'Pull from Wiki ({len(pulled)} pages)')

		# a full scan reports every current skip, whereas the loop reports each only once
		new_skips = skipped if full_scan else [entry for entry in skipped if entry not in var_global.REPORTED_SKIPS]
		var_global.REPORTED_SKIPS = set(skipped)

		await report_sync(pushed, pulled, created, new_skips)
		var_global.LAST_RECONCILE_TIMESTAMP = timestamp


# reports sync activity to Discord, staying silent when there was nothing to do
async def report_sync(pushed, pulled, created, skipped):
	if not (pushed or pulled or created or skipped):
		return

	var_global.OPERATION_LOGGER.info(f'Sync complete - {len(created)} created, {len(pushed)} pushed, {len(pulled)} pulled, {len(skipped)} skipped')

	sections = []

	for label, titles in (('Created on Wiki', created), ('Pushed to Wiki', pushed), ('Pulled to Repo', pulled)):
		if titles:
			sections.append(f'**{label}:**\n' + '\n'.join(f'- `{title}`' for title in titles))

	if skipped:
		sections.append('**Skipped:**\n' + '\n'.join(f'- `{title}` - {reason}' for title, reason in skipped))

	await send_audit_message(var_global.CHANNELS['main'], '**Wiki Sync Report**\n\n', '\n\n'.join(sections))
