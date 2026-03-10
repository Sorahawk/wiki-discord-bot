from imports import *


# standard function for HTTP requests
async def make_http_request(method='GET', endpoint=BASE_API_URL, payload=None, retry=False):
	session = var_global.SESSION

	var_global.OPERATION_LOGGER.info(f'Making {method} request to {endpoint} with payload {payload}.')
	
	if not payload:
		payload = {}

	if var_secret.WIKI_CSRF_TOKEN and not payload.get('token'):
		payload['token'] = var_secret.WIKI_CSRF_TOKEN

	if method == 'POST':
		raw_response = await session.request('POST', endpoint, data=payload)
	else:
		raw_response = await session.request(method, endpoint, params=payload)

	data = raw_response.json()
	var_global.OPERATION_LOGGER.info(data)

	# retry once if token happened to expire before the periodic refresh
	if data.get('error', {}).get('code') in ['badtoken'] and not retry:
		payload['token'] = None

		await check_wiki_session()
		data = await make_http_request(method, endpoint, payload, True)

	return data


# retrieve token
async def get_wiki_token(token_type='csrf'):
	response = await make_http_request(payload={
		'action': 'query',
		'meta': 'tokens',
		'type': token_type,
		'format': 'json'
	})
	return response['query']['tokens'][f'{token_type}token']


# login to wiki
async def wiki_login():
	# lock login attempts
	async with var_global.ASYNC_LOCK:
		login_token = await get_wiki_token('login')

		response = await make_http_request('POST', payload={
			'action': 'login',
			'lgname': var_secret.WIKI_CREDS[0],
			'lgpassword': var_secret.WIKI_CREDS[1],
			'lgtoken': login_token,
			'format': 'json'
		})

		data = response['login']

		if data['result'] == 'Success':
			var_global.OPERATION_LOGGER.info(f'Successfully logged into Wiki as {var_secret.WIKI_CREDS[0]}.')
			var_secret.WIKI_CSRF_TOKEN = await get_wiki_token()
		else:
			raise Exception(f'Wiki login failed: {data['result']} - {data.get('reason', 'no reason specified')}')


# check if login session is still valid
async def check_wiki_session():
	response = await make_http_request(payload={
		'action': 'query',
		'meta': 'userinfo',
		'format': 'json'
	})

	user = response['query']['userinfo']

	# if session is expired, MediaWiki returns an anonymous user
	if user.get('anon') is not None:
		var_global.OPERATION_LOGGER.warning('Wiki session expired; now performing re-login.')
		await wiki_login()
	else:
		var_global.OPERATION_LOGGER.info(f'Wiki session still active as: {user['name']}')
		# refresh the CSRF token just in case
		var_secret.WIKI_CSRF_TOKEN = await get_wiki_token()


# API call to delete a page or file
async def delete_wiki_page(title, reason=''):
	return await make_http_request('POST', payload={
		'action': 'delete',
		'title': title,
		'reason': reason,
		'format': 'json'
	})

# API call to rollback all consecutive edits from a single user if they are the latest revisions
async def rollback_wiki_page(title, username, reason=''):
	await check_wiki_session()
	rollback_token = await get_wiki_token('rollback')

	return await make_http_request('POST', payload={
		'action': 'rollback',
		'title': title,
		'user': username,
		'summary': reason,
		'format': 'json',
		'token': rollback_token
	})
