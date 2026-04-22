from imports import *

import bot_main
from bot_main import bot


async def adhoc_on_ready():
	var_global.THIN_MODE = True
	await orig_on_ready()

	# insert adhoc code BELOW
	response = await mentat_request('/api/v1/...', 'GET', payload=None)
	print(response)



	# insert adhoc code ABOVE

	await bot.close()



orig_on_ready = bot.on_ready
bot.on_ready = adhoc_on_ready
bot.run(DISCORD_BOT_TOKEN)
