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
		if any(phrase in message.content.lower() for phrase in reply[0]):
			return reply[1]


# returns a string where every line is formatted to be a blockquote
def format_blockquotes(text):
	return '\n'.join(f'> {line}' for line in text.splitlines())
