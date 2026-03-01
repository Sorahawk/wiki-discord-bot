from imports import *


# reacts to emoji responses in FEED_CHANNEL
async def feed_actions(payload):
	if payload.channel_id != FEED_CHANNEL_ID:
		return

	# verify user is staff
	member = payload.member
	if not check_user_elevation(member):
		return

	message = await var_global.FEED_CHANNEL.fetch_message(payload.message_id)
	content = message.content

	# ignore blacklisted messages
	for blacklist_string in FEED_BLACKLIST:
		if blacklist_string in content:
			return

	# delete page action
	if payload.emoji.name in ACCEPTED_EMOJIS['delete']:
		# grab page title
		match = re.search(r'\) created \[([^\]]+)\]', content)
		if not match:
			return

		# delete page
		title = match.group(1)

		response = await delete_wiki_page(title, f'Deleted via Discord by {member.global_name}')

		if response.get('error', {}).get('code') == 'missingtitle':
			await var_global.FEED_CHANNEL.send(f'<@{member.id}>, `{title}` no longer exists, thus cannot be deleted!')

	# rollback consecutive edits action
	elif payload.emoji.name in ACCEPTED_EMOJIS['rollback']:
		# grab user name and page title
		match = re.search(r':\[([^\]]+)\].*?\) edited \[([^\]]+)\]', content)
		if not match:
			return

		# rollback page
		username = match.group(1)
		title = match.group(2)

		response = await rollback_wiki_page(title, username, f'Latest edits by {username} rolled back via Discord by {member.global_name}')

		if response.get('error', {}).get('code') == 'alreadyrolled':
			await var_global.FEED_CHANNEL.send(f'<@{member.id}>, unable to rollback `{title}`! Page may have already been rolled back, or latest edit was not made by {username}.')
