from imports import *


# standard function for HTTP requests
async def http_request(endpoint, payload=None, method='GET', headers=None, is_json=False):
	session = var_global.SESSION
	var_global.OPERATION_LOGGER.info(f"Making {method} request to {endpoint} with payload {payload}.")

	if not payload:  # handle empty payload
		payload = {}

	if method not in ('POST', 'PUT', 'PATCH'):
		kwarg = 'params'
	elif is_json:
		kwarg = 'json'
	else:
		kwarg = 'data'

	raw_response = await session.request(method, endpoint, **{kwarg: payload}, headers=headers)

	try:
		response = raw_response.json()
	except:
		response = raw_response

	var_global.OPERATION_LOGGER.info(response)
	return response


# mentat functions

# mentat request wrapper
async def mentat_request(path, method='GET', payload=None, filters=None):
	auth_header = { 'Authorization': f'Bearer {MENTAT_TOKEN}' }
	endpoint = f'{MENTAT_BASE_URL}/{path.lstrip('/')}'

	# convert filters to params format by wrapping in keys in q[]
	if filters and not payload:
		payload = {f'q[{key}]': value for key, value in filters.items()}

	return await http_request(endpoint, payload, method, auth_header, is_json=True)


# retrieve mission info
async def get_mission(mission_id):
	return await mentat_request(f'/api/v1/missions/{mission_id}')


# abandon wiki mission without checks
# this function should NOT be used without first affirming that the mission has state `accepted`
async def abandon_mission(mission_id):
	await mentat_request(f'/api/v1/missions/{mission_id}/abandon', 'PUT')


# abandon wiki mission, ensuring that mission is safe to abandon (e.g. not completed)
async def abandon_mission_safely(mission):
	mission_id = mission['id']
	var_global.OPERATION_LOGGER.info(f"Attempting to remove user {mission['assignee']} from mission {mission_id}")

	if mission['status'] == 'accepted':
		await abandon_mission(mission_id)
	else:
		var_global.OPERATION_LOGGER.warning(f"Mission {mission_id} is in '{mission['status']}' state, not 'accepted', and cannot be abandoned.")



# wiki functions

# wiki request wrapper
async def wiki_request(payload, method='GET', token_type=None, retry=False):
	if token_type:
		payload['token'] = var_secret.WIKI_TOKENS[token_type]

	response = await http_request(WIKI_BASE_URL, payload, method)

	# retry wiki request once if error
	if response.get('error', {}) and not retry:
		await check_wiki_session()
		response = await wiki_request(payload, method, token_type, retry=True)

	return response


# retrieve token
async def get_wiki_token(token_type='csrf'):
	response = await wiki_request({
		'action': 'query',
		'meta': 'tokens',
		'type': token_type,
		'format': 'json'
	})

	tokens = response['query']['tokens']
	return tokens if len(tokens) != 1 else tokens[f'{token_type}token']


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

		response = await wiki_request({
			'action': 'login',
			'format': 'json',
			'lgname': var_secret.WIKI_CREDS[0],
			'lgpassword': var_secret.WIKI_CREDS[1],
			'lgtoken': login_token
		}, 'POST')

		data = response['login']

		if data['result'] == 'Success':
			var_global.OPERATION_LOGGER.info(f"Successfully logged into Awakening Wiki as {var_secret.WIKI_CREDS[0]}.")
			await refresh_tokens()
		else:
			raise Exception(f"Wiki login failed: {data['result']} - {data.get('reason', 'no reason specified')}")


# check if login session is still valid
async def check_wiki_session():
	response = await wiki_request({
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
		var_global.OPERATION_LOGGER.info(f"Wiki session still active as: {user['name']}")
		await refresh_tokens()


# API call to delete a page or file
async def delete_page(title, reason=''):
	return await wiki_request({
		'action': 'delete',
		'title': title,
		'reason': reason,
		'format': 'json'
	}, 'POST', 'csrf')


# API call to rollback all consecutive edits from a single user if they are the latest revisions
async def rollback_page(title, username, reason=''):
	return await wiki_request({
		'action': 'rollback',
		'title': title,
		'user': username,
		'summary': reason,
		'format': 'json'
	}, 'POST', 'rollback')
