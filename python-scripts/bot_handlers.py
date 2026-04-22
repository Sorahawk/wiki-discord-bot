from imports import *


# handles messages
async def message_handler(bot, message):
	# ignore messages sent by the bot itself
	if message.author == bot.user:
		return

	# only react to messages that mention the bot
	if bot.user in message.mentions:

		response = BOT_VOICELINES['default']
		for voiceline_data in BOT_REPLIES:
			if any(word in message.content.lower() for word in voiceline_data[0]):
				response = voiceline_data[1]
				break

		await message.channel.send(response)


# handles emoji reacts in feed channel
async def reaction_handler(payload):
	if payload.channel_id != CHANNEL_IDS['feed']:
		return

	# verify user is authorised
	member = payload.member
	if not check_user_elevation(member):
		return

	message = await var_global.CHANNELS['feed'].fetch_message(payload.message_id)
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

		response = await delete_wiki_page(title, f"Deleted via Discord by {member.display_name}")

		if response.get('error', {}).get('code') == 'missingtitle':
			await var_global.CHANNELS['feed'].send(f"<@{member.id}>, `{title}` no longer exists, thus cannot be deleted!")

	# rollback consecutive edits action
	elif payload.emoji.name in ACCEPTED_EMOJIS['rollback']:
		# grab user name and page title
		match = re.search(r':\[([^\]]+)\].*?\) edited \[([^\]]+)\]', content)
		if not match:
			return

		# rollback page
		username = match.group(1)
		title = match.group(2)

		response = await rollback_wiki_page(title, username, f"Latest edits by {username} rolled back via Discord by {member.display_name}")

		if response.get('error', {}).get('code') == 'alreadyrolled':
			await var_global.CHANNELS['feed'].send(f"<@{member.id}>, unable to rollback `{title}`! Page may have already been rolled back, or latest edit was not made by {username}.")


# clears in-progress wiki missions if assignee leaves the server
async def removed_member_handler(user_id):
	messages = [message async for message in var_global.CHANNELS['ongoing'].history(limit=None)]
	for mission in messages:
		embed = mission.embeds[0]
		mission_id = re.search(r'\[(\d+)\]', embed.title).group(1)

		# check if user matches
		assignee = embed.fields[-1].value
		if user_id == int(re.search(r'<@(\d+)>', assignee).group(1)):
			await mentat_request(f'/api/v1/missions/{mission_id}/abandon', method='PUT')
