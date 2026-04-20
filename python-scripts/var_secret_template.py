### Make a copy of this file, rename it var_secret.py, and fill it in

import sys


# (string) Discord bot token
DISCORD_BOT_TOKEN = ''

# (string) Mentat auth token
MENTAT_TOKEN = ''

# (dictionary of string tuples) Wiki login credentials
WIKI_CREDS_LIST = {
	'local': ('', ''),
	'remote': ('', ''),
	'scripts': ('', ''),
}

if sys.platform == 'linux':
	WIKI_CREDS = WIKI_CREDS_LIST['remote']
else:
	WIKI_CREDS = WIKI_CREDS_LIST['local']

# (dictionary of strings) Wiki session tokens, to init during runtime
WIKI_TOKENS = {
	'csrf': None,
	'rollback': None,
}
