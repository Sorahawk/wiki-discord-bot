from imports import *


# handles messages
async def message_handler(bot, message):
	# ignore messages sent by the bot itself
	if message.author == bot.user:
		return

	# process messages that mention the bot
	if bot.user in message.mentions:
		response = check_replies(message, BOT_REPLIES_MENTIONED) or BOT_VOICELINES['default']
		return await message.channel.send(response)

	# check for any special trigger phrases if bot is not mentioned
	if response := check_replies(message, BOT_REPLIES_ALWAYS):
		await message.channel.send(response)


# handles message edits
async def message_edit_handler(bot, payload):
	message = payload.message
	author = message.author

	# ignore messages sent by the bot itself
	if author == bot.user:
		return

	# ignore edits by elevated users
	if check_user_elevation(author):
		return

	message_link = f'https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}'
	audit_message = f"<@{author.id}> edited message: {message_link}\n\n"

	new_content = message.content

	# try to get original message content which will be present if it was still in the cache
	if cached := payload.cached_message:
		old_content = cached.content
		if old_content == new_content:  # link previews technically edit the message when appearing but do not change the content
			return

		audit_message += f"**Original:**\n{format_blockquotes(old_content)}\n\n"

	else:
		audit_message += "**Original:**\n```Content unavailable in cache.```\n"

	audit_message += f"**New**:\n{format_blockquotes(new_content)}"

	await var_global.CHANNELS['audit'].send(audit_message)


# handles message deletions
async def message_delete_handler(payload):
	pass


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

		response = await delete_page(title, f"Deleted via Discord by {member.display_name}")

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

		response = await rollback_page(title, username, f"Latest edits by {username} rolled back via Discord by {member.display_name}")

		if response.get('error', {}).get('code') == 'alreadyrolled':
			await var_global.CHANNELS['feed'].send(f"<@{member.id}>, unable to rollback `{title}`! Page may have already been rolled back, or latest edit was not made by {username}.")


# checks for any in-progress wiki missions when assignee leaves the server
async def removed_member_handler(bot, user_id):
	# fetch user info
	user = await bot.fetch_user(user_id)
	user_name = user.display_name

	# log event
	message = f"User {username} (<@{user_id}>) left the server."

	var_global.OPERATION_LOGGER.info(message)
	await var_global.CHANNELS['audit'].send(message)

	# check if user has any accepted missions, and abandon them
	missions = await mentat_request('/api/v1/missions', filters={
		'status_eq': 'accepted',
		'assignee_user_discord_uid_eq': user_id
	})
	for mission in missions:
		await abandon_mission_safely(mission)
