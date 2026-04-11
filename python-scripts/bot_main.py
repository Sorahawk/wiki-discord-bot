from imports import *


# declare bot intents
# all() enables everything, including the privileged intents: presences, members and message_content
intents = discord.Intents.all()

# init client and slash command tree
bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)

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

	# init channel objects
	var_global.MAIN_CHANNEL = bot.get_channel(MAIN_CHANNEL_ID)
	var_global.FEED_CHANNEL = bot.get_channel(FEED_CHANNEL_ID)
	var_global.MISSIONS_CHANNEL = bot.get_channel(MISSIONS_CHANNEL_ID)

	# init async lock
	var_global.ASYNC_LOCK = asyncio.Lock()

	# init requests session
	var_global.SESSION = httpx.AsyncClient(headers=STANDARD_HEADERS, timeout=15)

	# sync command tree
	await tree.sync()

	# start tasks
	task_rotate_status.start()
	task_refresh_wiki_session.start()


@bot.event
async def on_raw_reaction_add(payload):
	try:
		await reaction_handler(payload)

	except Exception as e:
		await send_traceback(e, var_global.MAIN_CHANNEL)


@bot.event
async def on_message(message):
	try:
		await message_handler(bot, message)

	except Exception as e:
		await send_traceback(e, var_global.MAIN_CHANNEL)


@tree.command(name="available_missions", description="Counts number of missions left in #missions-board")
async def available_missions(interaction: discord.Interaction):
	await interaction.response.defer()

	messages = [message async for message in var_global.MISSIONS_CHANNEL.history(limit=None)]
	num_messages = len(messages)

	await interaction.followup.send(f"There are {num_messages}~ Wiki Missions left in <#{MISSIONS_CHANNEL_ID}>.")


@tree.command(name="update_code", description="Pulls new code from GitHub and restarts bot")
@discord.app_commands.default_permissions(administrator=True)
async def update_code(interaction: discord.Interaction):
	await interaction.response.send_message("Standby. Checking the mail for updates.")

	# reset any changes that could have been made to the project folder and pull latest code
	subprocess.run(f"cd {LINUX_ABSOLUTE_PATH} && git reset --hard HEAD && git pull", shell=True)

	# restart service
	subprocess.run(['sudo', 'systemctl', 'restart', LINUX_SERVICE_NAME])


# start bot
bot.run(DISCORD_BOT_TOKEN)
