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
	if var_global.MAIN_CHANNEL:
		return

	# init logger
	var_global.OPERATION_LOGGER = init_logger()
	var_global.OPERATION_LOGGER.info(f'{bot.user} is online.')

	# init channel objects
	var_global.MAIN_CHANNEL = bot.get_channel(MAIN_CHANNEL_ID)
	var_global.FEED_CHANNEL = bot.get_channel(FEED_CHANNEL_ID)
	var_global.MISSIONS_CHANNEL = bot.get_channel(MISSIONS_CHANNEL_ID)

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


@bot.event
async def on_raw_reaction_add(payload):
	try:
		await reaction_handler(payload)

	except Exception as e:
		await send_traceback(e, var_global.MAIN_CHANNEL)


@bot.event
async def on_message(message):
	try:
		context = await bot.get_context(message)
		if context.valid:
			await bot.invoke(context)
		else:
			await message_handler(bot, message)

	except Exception as e:
		await send_traceback(e, var_global.MAIN_CHANNEL)


# start bot
if __name__ == "__main__":
	bot.run(DISCORD_BOT_TOKEN)
