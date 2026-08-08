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


# pushes local content to the wiki, applying safety guards and protecting MessageBundles
# returns True on success, False if the content failed a guard
async def push_page(title, content, full_path, rel_path, head_sha):
	if not content.strip() or has_conflict_markers(content):
		return False

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

	return True


# determines which titles need comparing against the wiki this cycle
# returns a set of titles (None means compare everything) and the timestamp to store on success
async def resolve_sync_scope(base_sha, full_scan):
	if full_scan or not var_global.LAST_RECONCILE_TIMESTAMP:
		return None, await get_wiki_timestamp()

	changed_paths = await get_changed_paths(base_sha, PAGES_ROOT)

	# ancestry is broken, so the commit range is unusable and the whole tree must be compared
	if changed_paths is None:
		return None, await get_wiki_timestamp()

	recent_titles, newest = await get_recent_changes(var_global.LAST_RECONCILE_TIMESTAMP)

	titles = set(recent_titles)
	for path in changed_paths:
		titles.add(resolve_title(Path(path)))

	return titles, newest or var_global.LAST_RECONCILE_TIMESTAMP


# reconciles the wiki repo against the wiki in both directions
# the repo wins where the wiki's latest edit was from this code, else the wiki wins
async def run_sync(full_scan=False):
	async with var_global.REPO_LOCK:
		base_sha = await get_head_sha()
		await reset_to_remote()
		head_sha = await get_head_sha()

		titles, timestamp = await resolve_sync_scope(base_sha, full_scan)
		local_by_title, file_by_title = collect_local_pages(titles)

		changed, missing = await diff_against_wiki(local_by_title)
		revisions = await get_last_revisions(changed)

		pushed, pulled, created, skipped = [], [], [], []

		for title in missing:
			full_path, rel_path = file_by_title[title]

			if await push_page(title, local_by_title[title], full_path, rel_path, head_sha):
				created.append(title)
			else:
				skipped.append(title)

		for title, (local_content, live_content) in changed.items():
			full_path, rel_path = file_by_title[title]

			# the latest live edit was our own sync, so the wiki is the stale side
			if is_stale_sync_revision(revisions.get(title)):
				if await push_page(title, local_content, full_path, rel_path, head_sha):
					pushed.append(title)
				else:
					skipped.append(title)

				continue

			if not live_content.strip():
				skipped.append(title)
				continue

			full_path.write_text(live_content, encoding='utf-8')
			pulled.append(title)

		if pulled:
			await commit_and_push(PAGES_ROOT, f'Pull from wiki ({len(pulled)} pages)')

		await report_sync(pushed, pulled, created, skipped)
		var_global.LAST_RECONCILE_TIMESTAMP = timestamp


# reports sync activity to Discord, staying silent unless something needs attention
async def report_sync(pushed, pulled, created, skipped):
	sections = []

	if created:
		sections.append('**Created on Wiki:**\n' + '\n'.join(f'- `{title}`' for title in created))

	if skipped:
		sections.append('**Skipped (failed safety checks):**\n' + '\n'.join(f'- `{title}`' for title in skipped))

	if not sections:
		if pushed or pulled:
			var_global.OPERATION_LOGGER.info(f'Sync complete - {len(pushed)} pushed, {len(pulled)} pulled')
		return

	sections.append(f'{len(pushed)} pushed, {len(pulled)} pulled')
	await var_global.CHANNELS['main'].send('\n\n'.join(sections))
