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
	full_trace = ''.join(traceback.format_exception(type(e), e, e.__traceback__))

	var_global.OPERATION_LOGGER.error(full_trace)

	channel = channel or var_global.CHANNELS.get('main')
	if not channel:
		return

	if len(full_trace) <= 1994:
		await channel.send(f'```{full_trace}```')
	else:
		await channel.send(e, file=generate_file(full_trace, 'traceback.txt'))
