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
	max_len_wo_backticks = 1994

	full_trace = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
	var_global.OPERATION_LOGGER.error(full_trace)

	channel = channel or var_global.CHANNELS.get('main')
	if not channel:
		return

	if len(full_trace) <= max_len_wo_backticks:
		await channel.send(f'```{full_trace}```')
	else:
		error_truncated = str(e)[:max_len_wo_backticks] or type(e).__name__
		await channel.send(f'```{error_truncated}```', file=generate_file(full_trace, 'traceback.txt'))
