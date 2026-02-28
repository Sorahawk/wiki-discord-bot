from imports import *


# returns True if message author is elevated, otherwise False
def check_user_elevation(member):
	try:
		for role in member.roles:
			if role.id in ELEVATED_USER_ROLES:
				return True
	except:
		# the try block will fail in DMs because there are no roles
		pass

	return False
