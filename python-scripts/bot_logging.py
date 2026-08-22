from imports import *


# initialises logger
def init_logger():
	# check if script is running from Linux root directory (systemd service)
	filepath = os.getcwd()

	if filepath == '/':
		filepath = LINUX_ABSOLUTE_PATH

	handler_file = logging.FileHandler(f'{filepath}/status.log', mode='w', encoding='utf-8')
	handler_file.setFormatter(logging.Formatter(fmt='{asctime} {name} - [{levelname}] {message}', datefmt='%d/%m/%Y %I:%M:%S %p', style='{'))

	logger = logging.getLogger(LOGGER_NAME)
	logger.setLevel(logging.DEBUG)
	logger.addHandler(handler_file)

	return logger


# obtains full traceback of given exception and outputs to specified channel
async def send_traceback(e, channel=None):
	full_trace = ''.join(format_exception(type(e), e, e.__traceback__))
	var_global.OPERATION_LOGGER.error(full_trace)

	channel = channel or var_global.CHANNELS['main']
	header = f'```{type(e).__name__}```'
	body = f'```{full_trace}```'

	await send_audit_message(channel, header, body)


# sends an audit message, offloading to a text file if it exceeds Discord's char limit
async def send_audit_message(channel, header, body, files=None):
	if files is None:
		files = []

	full_message = header + body

	if len(full_message) <= 2000:
		await channel.send(full_message, files=files, allowed_mentions=discord.AllowedMentions.none())
	else:
		await channel.send(header, file=generate_file(full_message, 'audit_message.txt'), allowed_mentions=discord.AllowedMentions.none())
		if files:
			await channel.send(files=files)
