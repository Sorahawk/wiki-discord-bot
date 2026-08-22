from imports import *


async def push_to_wiki():
	async with var_global.REPO_LOCK:
		pass


async def pull_from_wiki():
	async with var_global.REPO_LOCK:
		pass


# reports sync activity to Discord
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
			sections.append(f'### {label}:\n' + ''.join(f'\n- `{title}`' for title in titles))

	for label, entries in (('Blocked', blocked), ('Conflicts Resolved', resolved)):
		if entries:
			lines = ''.join(f'\n- `{title.replace(' ', '_')}` - {detail}' for title, detail in entries)
			sections.append(f'### {label}:\n{lines}')

	await send_audit_message(channel or var_global.CHANNELS['main'], '## Wiki Sync Report\n', '\n'.join(sections))
	return True
