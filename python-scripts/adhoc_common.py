from imports import *


async def setup():
	var_global.OPERATION_LOGGER = init_logger()
	var_global.ASYNC_LOCK = asyncio.Lock()
	var_global.SESSION = httpx.AsyncClient(headers=STANDARD_HEADERS, timeout=15)

	var_secret.WIKI_CREDS = WIKI_CREDS_LIST['scripts']

	await check_wiki_session()
