from imports import *


# standard function for HTTP requests
async def make_http_request(payload=None, method='GET', token_type=None, endpoint=BASE_API_URL, retry=False):
	session = var_global.SESSION

	var_global.OPERATION_LOGGER.info(f'Making {method} request to {endpoint} with payload {payload}.')
	
	if not payload:
		payload = {}

	if token_type:
		payload['token'] = var_secret.WIKI_TOKENS[token_type]

	if method == 'POST':
		raw_response = await session.request(method, endpoint, data=payload)
	else:
		raw_response = await session.request(method, endpoint, params=payload)

	response = raw_response.json()
	var_global.OPERATION_LOGGER.info(response)

	# retry once if error
	if response.get('error', {}) and not retry:
		await check_wiki_session()
		response = await make_http_request(payload, method, token_type, endpoint, True)

	return response


# retrieve token
async def get_wiki_token(token_type='csrf'):
	response = await make_http_request({
		'action': 'query',
		'meta': 'tokens',
		'type': token_type,
		'format': 'json'
	})

	tokens = response['query']['tokens']

	if len(tokens) != 1:
		return tokens

	return tokens[f'{token_type}token']


# refresh all wiki tokens
async def refresh_tokens():
	tokens = await get_wiki_token('|'.join(var_secret.WIKI_TOKENS.keys()))

	for token_type in var_secret.WIKI_TOKENS:
		var_secret.WIKI_TOKENS[token_type] = tokens[f'{token_type}token']


# login to wiki
async def wiki_login():
	# lock login attempts
	async with var_global.ASYNC_LOCK:
		login_token = await get_wiki_token('login')

		response = await make_http_request({
			'action': 'login',
			'format': 'json',
			'lgname': var_secret.WIKI_CREDS[0],
			'lgpassword': var_secret.WIKI_CREDS[1],
			'lgtoken': login_token
		}, 'POST')

		data = response['login']

		if data['result'] == 'Success':
			var_global.OPERATION_LOGGER.info(f'Successfully logged into Wiki as {var_secret.WIKI_CREDS[0]}.')
			await refresh_tokens()
		else:
			raise Exception(f'Wiki login failed: {data['result']} - {data.get('reason', 'no reason specified')}')


# check if login session is still valid
async def check_wiki_session():
	response = await make_http_request({
		'action': 'query',
		'meta': 'userinfo',
		'format': 'json'
	})

	user = response['query']['userinfo']

	# if session is expired, MediaWiki returns an anonymous user
	if user.get('anon') is not None:
		var_global.OPERATION_LOGGER.warning('Wiki session expired; now performing re-login.')
		await wiki_login()

	# even if session is still valid, just refresh tokens to be safe
	else:
		var_global.OPERATION_LOGGER.info(f'Wiki session still active as: {user['name']}')
		await refresh_tokens()


# API call to delete a page or file
async def delete_wiki_page(title, reason=''):
	return await make_http_request({
		'action': 'delete',
		'title': title,
		'reason': reason,
		'format': 'json'
	}, 'POST', 'csrf')

# API call to rollback all consecutive edits from a single user if they are the latest revisions
async def rollback_wiki_page(title, username, reason=''):
	return await make_http_request({
		'action': 'rollback',
		'title': title,
		'user': username,
		'summary': reason,
		'format': 'json'
	}, 'POST', 'rollback')
