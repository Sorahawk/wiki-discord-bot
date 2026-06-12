from imports import *


# handles messages
async def message_handler(bot, message):
	# process messages that mention the bot
	if bot.user in message.mentions:
		response = check_replies(message, BOT_REPLIES_ALWAYS) or check_replies(message, BOT_REPLIES_MENTIONED) or BOT_VOICELINES['default']
		return await message.channel.send(response)

	# check for any special trigger phrases if bot is not mentioned
	if response := check_replies(message, BOT_REPLIES_ALWAYS):
		await message.channel.send(response)


# handles message edits
async def message_edit_handler(bot, before, after):
	author = after.author

	# ignore messages sent by the bot itself
	if author == bot.user:
		return

	# ignore edits by elevated users
	if check_user_elevation(author):
		return

	message_link = f'https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id}'
	audit_header = f"<@{author.id}> edited message: {message_link}\n\n"

	old_content = before.content
	new_content = after.content

	if old_content == new_content:  # link previews technically edit the message when appearing but do not change the content
		return

	audit_message = audit_header + f"**Original:**\n{format_blockquotes(old_content)}\n\n"
	audit_message += f"**New**:\n{format_blockquotes(new_content)}"

	if len(audit_message) <= 2000:
		await var_global.CHANNELS['audit'].send(audit_message, allowed_mentions=discord.AllowedMentions.none())
	else:
		await var_global.CHANNELS['audit'].send(audit_header, file=generate_file(audit_message, 'audit_message.txt'), allowed_mentions=discord.AllowedMentions.none())


# handles message deletions
async def message_delete_handler(bot, message):
	author = message.author

	# ignore bot messages being deleted
	if author == bot.user or author.id == MENTAT_BOT_ID:
		return

	# fetch attachments immediately before Discord purges them
	files = []

	for file in message.attachments:
		response = await var_global.SESSION.get(file.url)

		if response.status_code == 200:
			files.append(discord.File(io.BytesIO(response.content), filename=file.filename))

	message_link = f'https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}'
	audit_header = ''

	# check audit log to find the deleter, might take a while to appear
	# self-deletions don't appear in the log
	await asyncio.sleep(2)

	async for entry in message.guild.audit_logs(action=discord.AuditLogAction.message_delete, limit=3):
		if entry.target.id == author.id and entry.extra.channel.id == message.channel.id:
			audit_header = f"<@{entry.user.id}> deleted a message by <@{author.id}>: {message_link}"
			break

	# if no matching audit logs, likely a self-deletion
	if not audit_header:

		# ignore self-deletions by elevated users
		if check_user_elevation(author):
			return

		audit_header = f"<@{author.id}> deleted their message: {message_link}"

	audit_message = audit_header + f'\n{format_blockquotes(message.content)}'

	if len(audit_message) <= 2000:
		await var_global.CHANNELS['audit'].send(audit_message, files=files, allowed_mentions=discord.AllowedMentions.none())
	else:
		await var_global.CHANNELS['audit'].send(audit_header, file=generate_file(audit_message, 'audit_message.txt'), allowed_mentions=discord.AllowedMentions.none())

		if files:
			await var_global.CHANNELS['audit'].send(files=files)


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
	# fetch user info because raw event only returns user ID
	user = await bot.fetch_user(user_id)

	# log event
	message = f"<@{user_id}> left the server - `{user_id}`  `@{user.name}`  `({user.display_name})`"

	var_global.OPERATION_LOGGER.info(message)
	await var_global.CHANNELS['audit'].send(message)

	avatar_url = user.display_avatar.with_size(128).url
	await var_global.CHANNELS['audit'].send(avatar_url)

	# check if user has any accepted missions, and abandon them
	missions = await mentat_request('/api/v1/missions', filters={
		'status_eq': 'accepted',
		'assignee_user_discord_uid_eq': user_id
	})
	for mission in missions:
		await abandon_mission_safely(mission)
