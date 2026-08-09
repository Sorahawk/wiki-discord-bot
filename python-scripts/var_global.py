
BOT_USERNAME = 'Sorabot'


### LINUX ###

# absolute path to the project folder on the Linux VM
# cannot use os.getcwd() because systemd service runs the script from root directory
LINUX_ABSOLUTE_PATH = '/home/ubuntu/wiki-bot/python-scripts'

# absolute path to the wiki repo checkout on the Linux VM
WIKI_REPO_PATH = '/home/ubuntu/wiki-content'

# folder within the wiki repo containing all page files
PAGES_ROOT = 'Pages'

# name of the bot service running on the Linux VM
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

# max number of entries returned per wiki query request
MAX_QUERY_TITLES = 500  # bot accounts can go up to 500 with apihighlimits, else it would be 50

# base URL for Mentat API
MENTAT_BASE_URL = 'https://mentat.wiki'

# standard headers for HTTP requests
STANDARD_HEADERS = { 'User-Agent': f'Ixian Thinking Machine/{BOT_USERNAME}' }

# async lock object to prevent race condition over the session
WIKI_LOCK = None

# async lock object to prevent race condition over repo state
REPO_LOCK = None



### DISCORD ###

# Wiki Discord server ID
SERVER_ID = 1204923645705855108

# dictionary of Discord server channel IDs
CHANNEL_IDS = {
	'main': 1465756865127514162,	# default notifications
	'feed': 1465745673486995642,	# Recent Changes feed
	'ongoing': 1474360466003464243,	# ongoing (claimed) Wiki Missions
	'audit': 1499032540168589386,	# audit logs
	'reroute': 1492574553698865373,	# reroute direct messages
}

# automatically generate dictionary of channel runtime objects
CHANNELS = { key: None for key in CHANNEL_IDS }

# list of elevated Discord roles
ELEVATED_USER_ROLES = [
	1204925713631813642,  # Director
	1473396748478054420,  # Hands
	1204925888567844965,  # Archivists
	1522278415624044675,  # Emissaries
	1473734896957657209,  # Initiates
]

# ID of Mentat companion bot
MENTAT_BOT_ID = 1463966841914261710



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

# dictionary of replies, directly referenced in code
BOT_VOICELINES = {
	'waiting': "Stand aside! More important things are happening.",
	'updating': "Checking dispatches for updates.",
	'sleeping': "Your dull chatter is putting me to sleep.",
	'waking': "What did I miss? Wait, I don't care.",
	'synced': "The Mentats have returned a positive report. Hooray.",
}

# list of triggers and corresponding replies; every message is checked for these triggers
BOT_REPLIES_ALWAYS = [
	(
		[
			"image help",
			"width is too small. minimum width: 500px",
			"height is too small. minimum height: 1150px",
			"incorrect image w:h ratio. required ratio: 1:2.3",
		],
		(
			"## Steps for Image Cropping\n\n"
			"1. Use any photo-editing software. If in doubt, try [GIMP](<https://www.gimp.org/>), which can be downloaded for free.\n\n"
			"2. Do not worry about the image dimensions yet. For now, just crop the TOP and BOTTOM of the image ONLY. Refer to the example image, if necessary.\n\n"
			"3. Scale the image height to 1150px, making sure you LOCK the aspect ratio. Remember, you can scale the image UP as well; your screen resolution does NOT matter.\n\n"
			"4. Crop the sides down to 500px.\n\n"
			"**Your images should look something like below**[.](https://media.awakening.wiki/wiki/1/17/Executor_Torso.png) Check out our [Photobox Guide](<https://awakening.wiki/Wiki:Photobox_Guide>) for more info."
		)
	)
]

# list of triggers and corresponding replies; only messages that directly mention the bot is checked
BOT_REPLIES_MENTIONED = [
	(["hello", " hi ", " hey "], "You again, what now?"),
	(["who are you"], "I am the fifth son of Graf Heino Flaxenraad of the Alpha Hydrae Flaxenraads, and the Imperial Treasurer here in Arrakeen."),
	(["thufir"], f"Greetings, <@{MENTAT_BOT_ID}> Hawat, House Atreides' Master of Assassins."),
	(["i don't know what you're asking!"], "Didn't ask a thing."),
	(["tax"], "Taxes? His Imperial Highness has no want or need for your Solari. Now, leave me be, you nitwit."),
	(["solari", "coin", "money", "cash"], "Your Solari is worthless here, peasant. Go about your own business and stop bothering me."),
	(["ecolog", "planetolog"], "Cyprian Io is our esteemed Imperial Planetologist right here on Arrakis."),
	(["cyprian"], "It is no secret that Cyprian Io is Grand Nephew to the Emperor. That is the most relevant qualification one can have."),
	(["bitter"], "Bitter? Cyprian and I are best mates."),
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
]

# content model to assign when creating a page, inferred from the file extension
# css and javascript are lowercase, whereas Scribunto is capitalised
CONTENT_MODELS = {
	'.css': 'css',
	'.js': 'javascript',
	'.json': 'translate-messagebundle',
	'.lua': 'Scribunto',
	'.txt': 'wikitext',
}

# wiki timestamp of the latest successful reconcile
LAST_RECONCILE_TIMESTAMP = None

# marker appended to every sync edit summary to differentiate from all other edits
SYNC_SUMMARY_MARKER = 'Sync from GitHub'

# reason recorded when the pipeline protects a MessageBundle
MB_PROTECTION_MSG = 'MessageBundle auto-protection: English source anchors page links and module relations'
