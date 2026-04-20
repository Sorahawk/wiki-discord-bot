from imports import *


# returns True if message author is elevated, otherwise False
def check_user_elevation(member):
	# elevation check will fail in DMs because there are no roles to verify permissions
	return any(role.id in ELEVATED_USER_ROLES for role in getattr(member, 'roles', []))


# returns a Discord File object
def generate_file(content, filename):
	return discord.File(io.StringIO(content), filename=filename)
