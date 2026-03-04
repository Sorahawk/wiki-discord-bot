from imports import *


# declare bot intents
# all() enables everything, including the privileged intents: presences, members and message_content
intents = discord.Intents.all()

# init client
bot = discord.Client(intents=intents)


# automatically rotate bot's Discord status every 10 minutes
@loop(minutes=5)
async def task_rotate_status():
	activity, activity_type = random.choice(list(BOT_ACTIVITY_STATUSES.items()))

	if isinstance(activity_type, str):
		activity_status = discord.Streaming(url=activity_type, name=activity)
	else:
		activity_status = discord.Activity(type=activity_type, name=activity)

	await bot.change_presence(activity=activity_status)


# automatically rotate bot's Discord status every 10 minutes
@loop(minutes=10)
async def task_refresh_wiki_session():
	try:
		await check_wiki_session()

	except Exception as e:
		await send_traceback(e, var_global.MAIN_CHANNEL)


@bot.event
async def on_ready():
	# on_ready() may be called more than once, typically whenever the bot momentarily loses connection to Discord 
	# check if this is first time bot is calling on_ready()
	if var_global.MAIN_CHANNEL:
		return

	# init logger
	var_global.OPERATION_LOGGER = init_logger()
	var_global.OPERATION_LOGGER.info(f'{bot.user} is online.')

	# init main channel object
	var_global.MAIN_CHANNEL = bot.get_channel(MAIN_CHANNEL_ID)

	# init feed channel object
	var_global.FEED_CHANNEL = bot.get_channel(FEED_CHANNEL_ID)

	# init async lock
	var_global.ASYNC_LOCK = asyncio.Lock()

	# init requests session
	var_global.SESSION = httpx.AsyncClient(headers=STANDARD_HEADERS)

	# start tasks
	task_rotate_status.start()
	task_refresh_wiki_session.start()


@bot.event
async def on_raw_reaction_add(payload):
	try:
		await feed_actions(payload)

	except Exception as e:
		await send_traceback(e, var_global.MAIN_CHANNEL)


# start bot
bot.run(DISCORD_BOT_TOKEN)
