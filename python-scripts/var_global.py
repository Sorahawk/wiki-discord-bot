
### LINUX ###

# absolute path to the project folder on the Linux cloud instance
# cannot use os.getcwd() because systemd service runs the script from root directory
LINUX_ABSOLUTE_PATH = '/home/ubuntu/wiki-bot/python-scripts'

# name of the bot service running on the Linux cloud instance
LINUX_SERVICE_NAME = 'wiki-bot.service'

# logger object
OPERATION_LOGGER = None



### HTTP ###

# http session object
SESSION = None

# base URL for the API
BASE_API_URL = 'https://awakening.wiki/api.php'

# standard headers for HTTP requests
STANDARD_HEADERS = {'User-Agent': f'Sorabot/1.0 python-httpx'}

# async lock object to prevent race condition over the session
ASYNC_LOCK = None



### DISCORD ###

# list of elevated Discord roles
ELEVATED_USER_ROLES = [1204925713631813642, 1473396748478054420, 1204925888567844965, 1473734896957657209]

# ID of default Discord server channel that will receive notifications
MAIN_CHANNEL_ID = 1465756865127514162

# ID of Discord server channel that logs all Recent Changes on the wiki
FEED_CHANNEL_ID = 1465745673486995642

# main channel object
MAIN_CHANNEL = None

# feed channel object
FEED_CHANNEL = None



### MAIN ###

# dictionary of the available Discord statuses for the bot
# if activity (key) is meant to be a 'Streaming' activity, then corresponding value is a string URL
# otherwise corresponding value is the respective ActivityType
# available ActivityTypes: 0 is gaming (Playing), 1 is streaming (Streaming), 2 is listening (Listening to),
# 3 is watching (Watching), 4 is custom, 5 is competing (Competing in)
BOT_ACTIVITY_STATUSES = {
	"Dune: Awakening": 0,
	"Dune: Awakening OST": "https://www.youtube.com/watch?v=QEvBSxWOq4A&list=OLAK5uy_n283xB0dwMVYgIVA1ujI9Uk3sqMP_KWqI",
	"communinet radio shows": 2,
	"Dune": 3,
	"a staring competition": 5,
}

# dictionary of replies
BOT_VOICELINES = {
	'hello': "You again, what now?",
	'tax': "Taxes? His Imperial Highness' has no want or need for your Solari. Now, leave me be, you nitwit."
}

# dictionary of custom emojis
ACCEPTED_EMOJIS = {
	'delete': '🗑️',
	'rollback': '🔄',
}

# dictionary of blacklisted strings to prevent acting on certain pages or messages in FEED_CHANNEL
FEED_BLACKLIST = [
	':wave:',					# user registered
	':people_holding_hands:',	# user rights changed
	':truck:',					# page moved
	':wastebasket:',			# page deleted
	':lock:',					# page protection changed
	'Discord verification:all.json',
]
