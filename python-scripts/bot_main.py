from imports import *


# declare bot intents
# all() enables everything, including the privileged intents: presences, members and message_content
intents = discord.Intents.all()

# initialise client
bot = discord.Client(intents=intents)


# automatically rotate bot's Discord status every 10 minutes
@loop(minutes=10)
async def task_rotate_status():
	activity, activity_type = random.choice(list(BOT_ACTIVITY_STATUSES.items()))

	if isinstance(activity_type, str):
		activity_status = discord.Streaming(url=activity_type, name=activity)
	else:
		activity_status = discord.Activity(type=activity_type, name=activity)

	await bot.change_presence(activity=activity_status)


@bot.event
async def on_ready():
	# on_ready() may be called more than once, typically whenever the bot momentarily loses connection to Discord 
	# check if this is first time bot is calling on_ready()
	if var_global.MAIN_CHANNEL:
		return

	var_global.OPERATION_LOGGER = getLogger('Wiki Bot Operations Log')
	var_global.OPERATION_LOGGER.info(f"{bot.user} is online.")

	# initialise global main channel object
	var_global.MAIN_CHANNEL = bot.get_channel(MAIN_CHANNEL_ID)

	# initialise global feed channel object
	var_global.FEED_CHANNEL = bot.get_channel(FEED_CHANNEL_ID)

	# start tasks
	task_rotate_status.start()

	try:
		# initialise requests session
		var_global.SESSION = requests.Session()
		var_global.SESSION.headers.update(STANDARD_HEADERS)

		# login to wiki and store CSRF token
		var_secret.WIKI_CSRF_TOKEN = wiki_login()

	except Exception as e:
		await send_traceback(e, var_global.MAIN_CHANNEL)


@bot.event
async def on_raw_reaction_add(payload):
	try:
		await feed_reverse_actions(payload)

	except Exception as e:
		await send_traceback(e, var_global.MAIN_CHANNEL)


@bot.event
async def on_message(message):
	try:
		prefix_length = len(BOT_COMMAND_PREFIX)  # prefix might not always be single character

		# ignore messages if bot is not ready, and messages sent by the bot itself, and messages that don't start with the command prefix
		if not bot.is_ready() or message.author == bot.user or message.content[:prefix_length] != BOT_COMMAND_PREFIX:
			return

		# check for any valid command if the message starts with the prefix symbol
		result = check_command(message.content[prefix_length:])
		if not result:
			return

		command_method, user_input = result[0], result[1]

		# check for presence of any command flags
		# in the process also removes any excess whitespace
		flag_presence, user_input = check_flags(user_input)
		await eval(command_method)(message, user_input, flag_presence)

	except Exception as e:
		await send_traceback(e, message.channel)


# get current directory
filepath = os.getcwd()

# check if script is running from Linux root directory (systemd service)
if filepath == '/':
	filepath = LINUX_ABSOLUTE_PATH

# initialise logging module
init_logger(filepath)

# start bot
bot.run(DISCORD_BOT_TOKEN)
