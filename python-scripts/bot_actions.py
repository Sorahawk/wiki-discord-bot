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
		match = re.search('created\\s+\\[([^\\]]+)\\]', content)
		if not match:
			return

		# delete page
		response = await delete_wiki_page(match.group(1), f'Deleted via Discord by {member.global_name}')
		var_global.OPERATION_LOGGER.info(response)

	# revert edit action
	elif payload.emoji.name in ACCEPTED_EMOJIS['revert']:
		# grab page title and oldid (change ID)
		match = re.search('edited\\s+\\[([^\\]]+)\\][^\n]*?oldid=(\\d+)', content)
		if not match:
			return

		print(match)
