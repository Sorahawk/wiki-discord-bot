
### LINUX ###

# absolute path to the project folder on the Linux cloud instance
# cannot use os.getcwd() because systemd service runs the script from root directory
LINUX_ABSOLUTE_PATH = '/home/ubuntu/wiki-bot/python-scripts'

# name of the bot service running on the Linux cloud instance
LINUX_SERVICE_NAME = 'wiki-bot.service'

# logger name
LOGGER_NAME = 'Wiki Bot Operations Log'

# logger object
OPERATION_LOGGER = None



### HTTP ###

# http session object
SESSION = None

# base URL for Wiki API
WIKI_BASE_URL = 'https://awakening.wiki/api.php'

# base URL for Mentat API
MENTAT_BASE_URL = 'https://mentat.wiki'

# standard headers for HTTP requests
STANDARD_HEADERS = { 'User-Agent': f'Sorabot/1.0 python-httpx' }

# async lock object to prevent race condition over the session
ASYNC_LOCK = None



### DISCORD ###

# list of elevated Discord roles
ELEVATED_USER_ROLES = [1204925713631813642, 1473396748478054420, 1204925888567844965, 1473734896957657209]

# dictionary of Discord server channel IDs
CHANNEL_IDS = {
	# Channel that will receive notifications
	'main': 1465756865127514162,

	# Channel that logs all Recent Changes on the wiki
	'feed': 1465745673486995642,

	# Channel that displays all the available Wiki Missions
	'available': 1393625122916798565,

	# Channel that displays all the ongoing Wiki Missions
	'ongoing': 1474360466003464243,
}

# automatically generate dictionary of channel runtime objects
CHANNELS = { key: None for key in CHANNEL_IDS }



### MAIN ###

# boolean toggle for sleep mode
SLEEP_MODE = False

# boolean toggle for adhoc scripts to avoid loading extended modules
THIN_MODE = False

# ID of Awakening Wiki Discord server in Mentat
GUILD_CONFIG_ID = 2

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
	'default': "You again, what now?",
	'update': "Stand by. Checking the mail for updates.",
	'sleep': "Your dull chatter is putting me to sleep.",
	'wake': "What did I miss? Wait, I don't care.",
}

BOT_REPLIES = [
	(['image help'], "1. Use any photo-editing software.\n\n2. Crop the height (top & bottom edges) first, leaving some buffer above the head and below the feet.\n\n3. Make sure to LOCK the aspect ratio, then scale the height to 1150px.\n\n4. Crop the sides down to 500px."),
	(['who are you'], "I am the fifth son of Graf Heino Flaxenraad of the Alpha Hydrae Flaxenraads, and the Imperial Treasurer here in Arrakeen."),
	(['tax'], "Taxes? His Imperial Highness has no want or need for your Solari. Now, leave me be, you nitwit."),
	(['solari', 'coin', 'money', 'cash'], "Your Solari is worthless here, peasant. Go about your own business and stop bothering me."),
	(['planetologist'], "Cyprian Io is our esteemed Imperial Planetologist right here on Arrakis."),
	(['cyprian'], "It is no secret that Cyprian Io is Grand Nephew to the Emperor. That is the most relevant qualification one can have."),
	(['bitter'], "Bitter? Cyprian and I are best mates."),
]


# dictionary of custom emojis
ACCEPTED_EMOJIS = {
	'delete': '🗑️',
	'rollback': '🔄',
}

# dictionary of blacklisted strings to prevent acting on certain pages or messages in feed channel
FEED_BLACKLIST = [
	':wave:',					# user registered
	':people_holding_hands:',	# user rights changed
	':truck:',					# page moved
	':wastebasket:',			# page deleted
	':lock:',					# page protection changed
	'Discord verification:all.json',
]
