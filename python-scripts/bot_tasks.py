from imports import *


class TasksCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot


	# load and unload all defined tasks dynamically

	async def cog_load(self):
		for name in dir(self):
			method = getattr(self, name)
			if hasattr(method, '_loop'):
				method.start()

	async def cog_unload(self):
		for name in dir(self):
			method = getattr(self, name)
			if hasattr(method, '_loop'):
				method.cancel()


	# automatically rotate bot's Discord status
	@loop(minutes=5)
	async def task_rotate_status(self):
		activity, activity_type = random.choice(list(BOT_ACTIVITY_STATUSES.items()))

		if isinstance(activity_type, str):
			activity_status = discord.Streaming(url=activity_type, name=activity)
		else:
			activity_status = discord.Activity(type=activity_type, name=activity)

		await self.bot.change_presence(activity=activity_status)


	# automatically refresh wiki tokens
	@loop(minutes=10)
	async def task_refresh_wiki_session(self):
		try:
			await check_wiki_session()

		except Exception as e:
			await send_traceback(e)


async def setup(bot):
	await bot.add_cog(TasksCog(bot))
