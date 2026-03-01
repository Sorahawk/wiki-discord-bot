from imports import *


def init_logger():
	# check if script is running from Linux root directory (systemd service)
	filepath = os.getcwd()

	if filepath == '/':
		filepath = LINUX_ABSOLUTE_PATH

	handler_file = logging.FileHandler(f'{filepath}/status.log', mode='w', encoding='utf-8')
	handler_file.setFormatter(logging.Formatter(fmt='{asctime} {name} - [{levelname}] {message}', datefmt='%d/%m/%Y %I:%M:%S %p', style='{'))

	logger = logging.getLogger('Wiki Bot Operations Log')
	logger.setLevel(logging.DEBUG)
	logger.addHandler(handler_file)
	
	return logger
