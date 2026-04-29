from imports import *


# declare bot intents
# all() enables everything, including the privileged intents: presences, members and message_content
intents = discord.Intents.all()

# init client and slash command tree
bot = discord.ext.commands.Bot(command_prefix='.', intents=intents)


@bot.event
async def on_ready():
	# on_ready() may be called more than once, typically whenever the bot momentarily loses connection to Discord 
	# check if this is first time bot is calling on_ready()
	if var_global.CHANNELS['main']:
		return

	# init logger
	var_global.OPERATION_LOGGER = init_logger()
	var_global.OPERATION_LOGGER.info(f"{bot.user} is online.")

	# init channel objects
	for key in var_global.CHANNELS:
		var_global.CHANNELS[key] = bot.get_channel(CHANNEL_IDS[key])

	# init requests session
	var_global.SESSION = httpx.AsyncClient(headers=STANDARD_HEADERS, timeout=15)

	# skip non-essential modules if running server adhoc scripts
	if not var_global.THIN_MODE:
		# init async lock
		var_global.ASYNC_LOCK = asyncio.Lock()

		# sync command tree
		await bot.load_extension('bot_commands')
		await bot.tree.sync(guild=bot.get_guild(SERVER_ID))

		# start tasks
		await bot.load_extension('bot_tasks')


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
@bot.tree.error
async def on_app_command_error(interaction, e):
	if not isinstance(e, app_commands.errors.CheckFailure):
		await send_traceback(getattr(e, 'original', e))


# handlers

# handle messages
@bot.event
async def on_message(message):
	# only remote instance should respond to prefix commands
	if sys.platform == 'linux' and message.author.guild_permissions.administrator:

		# check if message is a prefix command
		context = await bot.get_context(message)
		if context.valid:
			await bot.invoke(context)

	if not var_global.SLEEP_MODE:
		await message_handler(bot, message)


# handle message edits
@bot.event
async def on_raw_message_edit(payload):
	if not payload.guild_id or payload.guild_id != SERVER_ID:  # ignore events not in main server
		return

	if not var_global.SLEEP_MODE:
		await message_edit_handler(bot, payload)


# handle message deletions
@bot.event
async def on_raw_message_delete(payload):
	if not payload.guild_id or payload.guild_id != SERVER_ID:  # ignore events not in main server
		return

	if not var_global.SLEEP_MODE:
		await message_delete_handler(payload)


# handle emoji reacts
@bot.event
async def on_raw_reaction_add(payload):
	if not var_global.SLEEP_MODE:
		await reaction_handler(payload)


# handle removed members
@bot.event
async def on_raw_member_remove(payload):
	if payload.guild_id != SERVER_ID:  # ignore events not in main server
		return

	if not var_global.SLEEP_MODE:
		await removed_member_handler(payload.user.id)



# start bot
if __name__ == '__main__':
	bot.run(DISCORD_BOT_TOKEN)
