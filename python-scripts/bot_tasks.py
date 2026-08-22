from imports import *


class TasksCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot


	# load and unload all defined tasks dynamically

	async def cog_load(self):
		await check_wiki_session()

		for name in dir(self):
			method = getattr(self, name)
			if hasattr(method, '_loop'):
				method.start()

	async def cog_unload(self):
		for name in dir(self):
			method = getattr(self, name)
			if hasattr(method, '_loop'):
				method.cancel()


	# rotate bot's Discord status
	@loop(minutes=5)
	async def task_rotate_status(self):
		activity, activity_type = random.choice(list(BOT_ACTIVITY_STATUSES.items()))

		if isinstance(activity_type, str):
			activity_status = discord.Streaming(url=activity_type, name=activity)
		else:
			activity_status = discord.Activity(type=activity_type, name=activity)

		await self.bot.change_presence(activity=activity_status)


	# refresh wiki tokens
	@loop(minutes=10)
	async def task_refresh_wiki_session(self):
		try:
			await check_wiki_session()

		except Exception as e:
			await send_traceback(e)


	# reconciles the wiki repo against the wiki in both directions
	@loop(seconds=30)
	async def task_sync_wiki(self):
		if sys.platform != 'linux' or var_global.SLEEP_MODE:
			return

		if var_global.REPO_LOCK.locked():
			var_global.OPERATION_LOGGER.warning('Sync still running, skipping this cycle')
			return

		try:
			await run_sync()

		except Exception as e:
			await send_traceback(e)



async def setup(bot):
	await bot.add_cog(TasksCog(bot))
