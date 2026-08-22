from imports import *


# returns True if message author is elevated, otherwise False
def check_user_elevation(member):
	# elevation check will fail in DMs because there are no roles to verify permissions
	return any(role.id in ELEVATED_USER_ROLES for role in getattr(member, 'roles', []))


# returns a Discord File object
def generate_file(content, filename):
	return discord.File(io.StringIO(content), filename=filename)


# returns a matching reply, if any, from the specificed BOT_REPLIES list
def check_replies(message, reply_list):
	for reply in reply_list:
		if any(phrase.lower() in message.content.lower() for phrase in reply[0]):
			return reply[1]


# returns a string where every line is formatted to be a blockquote
def format_blockquotes(text):
	return '\n'.join(f'> {line}' for line in text.splitlines())


# fetches attachments as discord.File objects before Discord purges them
async def fetch_attachments_as_files(attachments):
	files = []

	for attachment in attachments:
		response = await var_global.SESSION.get(attachment.url)

		if response.status_code == 200:
			files.append(discord.File(io.BytesIO(response.content), filename=attachment.filename))

	return files
