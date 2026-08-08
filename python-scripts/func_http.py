from imports import *


# standard function for HTTP requests
async def http_request(endpoint, payload=None, method='GET', headers=None, is_json=False, no_log=False):
	session = var_global.SESSION

	if not payload:  # handle empty payload
		payload = {}

	if method not in ('POST', 'PUT', 'PATCH'):
		kwarg = 'params'
	elif is_json:
		kwarg = 'json'
	else:
		kwarg = 'data'

	log_message = f"Making {method} request to {endpoint}"
	if not no_log:
		log_message += f" with payload {payload}"

	var_global.OPERATION_LOGGER.info(log_message)

	raw_response = await session.request(method, endpoint, **{kwarg: payload}, headers=headers)

	if 'application/json' in raw_response.headers.get('Content-Type', ''):
		response = raw_response.json()
	else:
		response = raw_response.text

	if not no_log:
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
		message = f"WARNING: Mission {mission_id} is in '{mission['status']}' state, not 'accepted', and cannot be abandoned."

		var_global.OPERATION_LOGGER.warning(message)
		await var_global.CHANNELS['audit'].send(message)



# wiki functions

# wiki request wrapper
async def wiki_request(payload, method='GET', token_type=None, retry=False, no_log=False):
	payload['bot'] = 1  # mark as bot edit
	payload['format'] = 'json'  # set output as json
	payload['formatversion'] = 2  # set output format to recommended version

	# populate required token
	if token_type:
		payload['token'] = var_secret.WIKI_TOKENS[token_type]

	response = await http_request(WIKI_BASE_URL, payload, method, no_log=no_log)

	# verify the response type is a dict
	if not isinstance(response, dict):
		raise Exception(f"Wiki API returned a non-JSON response (possible server error):\n\n{response}")

	# retry wiki request once if error
	if response.get('error', {}) and not retry:
		await check_wiki_session()
		response = await wiki_request(payload, method, token_type, retry=True, no_log=no_log)

	return response


# retrieve token
async def get_wiki_token(token_type='csrf'):
	response = await wiki_request({
		'action': 'query',
		'meta': 'tokens',
		'type': token_type
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
	async with var_global.WIKI_LOCK:
		login_token = await get_wiki_token('login')

		response = await wiki_request({
			'action': 'login',
			'lgname': var_secret.WIKI_CREDS[0],
			'lgpassword': var_secret.WIKI_CREDS[1],
			'lgtoken': login_token,
		}, 'POST')

		data = response['login']

		if data['result'] == 'Success':
			var_global.OPERATION_LOGGER.info(f"Successfully logged into Awakening Wiki as {var_secret.WIKI_CREDS[0]}")
			await refresh_tokens()
		else:
			raise Exception(f"**Wiki login failed: {data['result']} - {data.get('reason', 'no reason specified')}**")


# check if login session is still valid
async def check_wiki_session():
	response = await wiki_request({
		'action': 'query',
		'meta': 'userinfo',
	})

	user = response['query']['userinfo']

	# if session is expired, MediaWiki returns an anonymous user
	if user.get('anon') is not None:
		var_global.OPERATION_LOGGER.warning('Wiki session expired; now performing re-login')
		await wiki_login()

	# even if session is still valid, just refresh tokens to be safe
	else:
		var_global.OPERATION_LOGGER.info(f"Wiki session still active as: {user['name']}")
		await refresh_tokens()


# API call to fetch content and content model for one or more titles
# accepts a single title string or a list of titles
# returns a dict keyed by page title, with corresponding value (content, content_model), or (None, None) for missing pages
async def get_page_content(titles):
	if isinstance(titles, str):
		titles = [titles]

	results = {}

	for i in range(0, len(titles), MAX_QUERY_TITLES):
		batch = titles[i:i + MAX_QUERY_TITLES]

		response = await wiki_request({
			'action': 'query',
			'titles': '|'.join(batch),
			'prop': 'revisions',
			'rvslots': 'main',
			'rvprop': 'content|contentmodel',
		}, no_log=True)

		for page in response['query']['pages']:
			if page.get('missing'):
				results[page['title']] = (None, None)
			else:
				slot = page['revisions'][0]['slots']['main']
				results[page['title']] = (slot['content'], slot['contentmodel'])

	return results


# API call to edit or create a page
# pass nocreate=True to refuse the edit if the page does not already exist
# pass content_model to set the content model explicitly when creating a new page (e.g. 'translate-messagebundle')
async def edit_page(title, content, reason='', nocreate=False, content_model=None):
	payload = {
		'action': 'edit',
		'title': title,
		'text': content,
		'summary': reason,
	}
	if nocreate:
		payload['nocreate'] = 1
	if content_model:
		payload['contentmodel'] = content_model

	return await wiki_request(payload, 'POST', 'csrf')


# API call to move a page
async def move_page(old_title, new_title, reason='', noredirect=True):
	payload = {
		'action': 'move',
		'from': old_title,
		'to': new_title,
		'reason': reason,
	}
	if noredirect:
		payload['noredirect'] = 1

	return await wiki_request(payload, 'POST', 'csrf')


# API call to delete a page, file, or a specific file version
async def delete_page(title, reason='', old_image=None):
	payload = {
		'action': 'delete',
		'title': title,
		'reason': reason,
	}
	if old_image:
		payload['oldimage'] = old_image

	return await wiki_request(payload, 'POST', 'csrf')


# API call to rollback all consecutive edits from a single user if they are the latest revisions
async def rollback_page(title, username, reason=''):
	return await wiki_request({
		'action': 'rollback',
		'title': title,
		'user': username,
		'summary': reason,
	}, 'POST', 'rollback')


# API call to revert a file to its previous version while deleting the latest version
async def revert_image(title, member_name):
	file_title = f'File:{title}'

	# fetch the two most recent versions, but archivename only shows up for old versions
	response = await wiki_request({
		'action': 'query',
		'titles': file_title,
		'prop': 'imageinfo',
		'iiprop': 'archivename',
		'iilimit': 2,
	})

	versions = response['query']['pages'][0]['imageinfo']
	to_revert = versions[1]['archivename']

	# revert to the previous version
	response = await wiki_request({
		'action': 'filerevert',
		'filename': title,
		'archivename': to_revert,
		'comment': f"Reverted to previous version via Discord by {member_name}",
	}, 'POST', 'csrf')

	if response.get('error'):
		return response

	# fetch again to get the archivename of the target version to delete
	response = await wiki_request({
		'action': 'query',
		'titles': file_title,
		'prop': 'imageinfo',
		'iiprop': 'archivename',
		'iilimit': 2,
	})

	versions = response['query']['pages'][0]['imageinfo']
	to_delete = versions[1]['archivename']

	# delete the target version
	response = await delete_page(file_title, f"Deleted target version via Discord by {member_name}", to_delete)

	if response.get('error'):
		return response

	# delete the now-redundant duplicate version
	return await delete_page(file_title, f"Deleted duplicate version via Discord by {member_name}", to_revert)


# API call to list all page titles in a namespace, optionally filtered by title prefix
async def list_pages(namespace, prefix=None):
	payload = {
		'action': 'query',
		'list': 'allpages',
		'apnamespace': namespace,
		'aplimit': 'max',
	}
	if prefix:
		payload['apprefix'] = prefix.split(':', 1)[-1] if ':' in prefix and namespace != 0 else prefix

	titles = []
	cont = None

	while True:
		if cont:
			payload['apcontinue'] = cont

		response = await wiki_request(payload)
		for page in response['query']['allpages']:
			titles.append(page['title'])

		cont = response.get('continue', {}).get('apcontinue')
		if not cont:
			break

	return titles


# API call to list all page titles belonging to a category, optionally filtered by namespace
async def list_category_members(category, namespace=None):
	payload = {
		'action': 'query',
		'list': 'categorymembers',
		'cmtitle': f'Category:{category}',
		'cmlimit': 'max',
	}
	if namespace is not None:
		payload['cmnamespace'] = namespace

	titles = []
	cont = None

	while True:
		if cont:
			payload['cmcontinue'] = cont

		response = await wiki_request(payload)
		for page in response['query']['categorymembers']:
			titles.append(page['title'])

		cont = response.get('continue', {}).get('cmcontinue')
		if not cont:
			break

	return titles


# API call to check a page's current protection levels
async def get_protection(title):
	response = await wiki_request({
		'action': 'query',
		'titles': title,
		'prop': 'info',
		'inprop': 'protection',
	})
	return response['query']['pages'][0].get('protection', [])


# API call to protect a page
async def protect_page(title, edit_level='sysop', move_level='sysop', expiry='infinite', reason=''):
	return await wiki_request({
		'action': 'protect',
		'title': title,
		'protections': f'edit={edit_level}|move={move_level}',
		'expiry': f'{expiry}|{expiry}',
		'reason': reason,
	}, 'POST', 'csrf')


# returns the wiki server's current timestamp, used to anchor the reconcile timestamp
async def get_wiki_timestamp():
	response = await wiki_request({
		'action': 'query',
		'meta': 'siteinfo',
		'siprop': 'general',
	}, no_log=True)
	return response['query']['general']['time']


# fetches titles edited or created on the wiki since the given timestamp
# returns the set of titles and the newest timestamp seen, else None if there were no changes
async def get_recent_changes(since_timestamp):
	cont = {}
	titles = set()
	newest = None

	while True:
		response = await wiki_request({
			'action': 'query',
			'list': 'recentchanges',
			'rcstart': since_timestamp,
			'rcdir': 'newer',
			'rctype': 'edit|new',
			'rcprop': 'title|timestamp',
			'rclimit': 'max',
			**cont
		})

		for change in response['query']['recentchanges']:
			titles.add(change['title'])
			newest = max(newest, change['timestamp']) if newest else change['timestamp']

		# check if there are more changes to retrieve
		if not (cont := response.get('continue', {})):
			break

	return titles, newest


# batch-fetches the author and summary of the latest revision for the given titles
# returns a dict of title -> (user, comment); missing pages are omitted
async def get_last_revisions(titles):
	titles = list(titles)
	results = {}

	for i in range(0, len(titles), MAX_QUERY_TITLES):
		response = await wiki_request({
			'action': 'query',
			'titles': '|'.join(titles[i:i + MAX_QUERY_TITLES]),
			'prop': 'revisions',
			'rvprop': 'user|comment',
		}, no_log=True)

		for page in response['query']['pages']:
			if not page.get('missing'):
				revision = page['revisions'][0]
				results[page['title']] = (revision['user'], revision.get('comment', ''))

	return results
