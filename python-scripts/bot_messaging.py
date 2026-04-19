from imports import *


# obtains full traceback of given exception and outputs to specified channel
async def send_traceback(e, channel=None):
	full_trace = log_traceback(e)

	if not channel:
		channel = var_global.CHANNELS['main']

	if len(full_trace) <= 1994:
		await channel.send(f'```{full_trace}```')
	else:
		await channel.send(e, file=generate_file(full_trace, 'traceback.txt'))


# respond to messages
async def message_handler(bot, message):
	# ignore messages sent by the bot itself
	if message.author == bot.user:
		return

	# only react to messages that mention the bot
	if bot.user in message.mentions:

		response = DEFAULT_VOICELINE
		for voiceline_data in BOT_VOICELINES:
			if any(word in message.content.lower() for word in voiceline_data[0]):
				response = voiceline_data[1]
				break

		await message.channel.send(response)
