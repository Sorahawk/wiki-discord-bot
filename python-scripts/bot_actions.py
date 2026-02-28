from imports import *


# acts on cross-mark emoji reactions by staff on messages in FEED_CHANNEL
async def feed_reverse_actions(payload):
	# only focus on FEED_CHANNEL and ignore all non-accepted emojis
	if payload.channel_id != FEED_CHANNEL_ID or payload.emoji.name not in ACCEPTED_EMOJIS['CrossMarks']:
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

	# grab relevant page title
	match = re.search(DELETE_REGEX, content)
	if match:
		title = match.group(1)

	# delete page
	response = delete_wiki_page(title, f'Deleted via Discord by {member.global_name}')
	print(response)
