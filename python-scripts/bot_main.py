from imports import *


# declare bot intents
# all() enables everything, including the privileged intents: presences, members and message_content
intents = discord.Intents.all()

# init client and slash command tree
bot = discord.ext.commands.Bot(command_prefix='.', intents=intents)
tree = bot.tree


@bot.event
async def on_ready():
	# on_ready() may be called more than once, typically whenever the bot momentarily loses connection to Discord 
	# check if this is first time bot is calling on_ready()
	if var_global.CHANNELS['main']:
		return

	# init logger
	var_global.OPERATION_LOGGER = init_logger()
	var_global.OPERATION_LOGGER.info(f'{bot.user} is online.')

	# init channel objects
	for key, item in var_global.CHANNELS.items():
		var_global.CHANNELS[key] = bot.get_channel(CHANNEL_IDS[key])

	# init requests session
	var_global.SESSION = httpx.AsyncClient(headers=STANDARD_HEADERS, timeout=15)

	if not var_secret.THIN_MODE:
		# init async lock
		var_global.ASYNC_LOCK = asyncio.Lock()

		# sync command tree
		await bot.load_extension("bot_commands")
		await tree.sync()

		# start tasks
		await bot.load_extension("bot_tasks")


# exception handlers

# covers all bot.events
@bot.event
async def on_error(event, *args, **kwargs):
	await send_traceback(sys.exc_info()[1])

# covers prefix commands
@bot.event
async def on_command_error(context, e):
	await send_traceback(getattr(e, 'original', e))

# covers slash commands
@tree.error
async def on_app_command_error(interaction, e):
	if var_global.SLEEP_MODE:
		return

	await send_traceback(getattr(e, 'original', e))


# handle emoji reacts
@bot.event
async def on_raw_reaction_add(payload):
	if not var_global.SLEEP_MODE:
		await reaction_handler(payload)


# handle messages
@bot.event
async def on_message(message):
	# check if message is a prefix command
	context = await bot.get_context(message)

	if context.valid:
		await bot.invoke(context)

	elif not var_global.SLEEP_MODE:
		await message_handler(bot, message)


# start bot
if __name__ == "__main__":
	bot.run(DISCORD_BOT_TOKEN)
