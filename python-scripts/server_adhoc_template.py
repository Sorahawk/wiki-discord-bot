from imports import *

import bot_main
from bot_main import bot


async def adhoc_on_ready():
	var_secret.THIN_MODE = True
	await og_on_ready()

	# insert adhoc code BELOW




	# insert adhoc code ABOVE

	await bot.close()


og_on_ready = bot.on_ready
bot.on_ready = adhoc_on_ready
bot.run(DISCORD_BOT_TOKEN)
