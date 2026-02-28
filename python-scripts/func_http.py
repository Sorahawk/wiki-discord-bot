from imports import *


# retrieve token
def get_wiki_token(token_type='csrf'):
	response = var_global.SESSION.get(BASE_API_URL, params={
		"action": "query",
		"meta": "tokens",
		"type": token_type,
		"format": "json"
	})
	return response.json()['query']['tokens'][f'{token_type}token']

# login to wiki
def wiki_login():
	login_token = get_wiki_token('login')

	response = var_global.SESSION.post(BASE_API_URL, data={
		"action": "login",
		"lgname": var_secret.WIKI_CREDS[0],
		"lgpassword": var_secret.WIKI_CREDS[1],
		"lgtoken": login_token,
		"format": "json"
	})

	data = response.json()['login']

	if data['result'] == 'Success':
		var_global.OPERATION_LOGGER.info(f'Successfully logged into Wiki as {data['lgusername']}.')
		return get_wiki_token()
	else:
		raise Exception(f'Wiki login failed: {data['result']} - {data.get('reason', 'no reason specified')}.')


# standard function for HTTP requests
def make_http_request(endpoint, method='GET', payload={}, retry=False):
	session = var_global.SESSION
	payload['token'] = var_secret.WIKI_CSRF_TOKEN

	var_global.OPERATION_LOGGER.info(f'Making {method} request to {endpoint} with payload {payload}.')
	if method == 'POST':
		response = session.request('POST', endpoint, data=payload)
	else:
		response = session.request(method, endpoint, params=payload)

	# if token expired, refresh token and retry request once
	data = response.json()
	if data.get('error') and not retry:
		var_secret.WIKI_CSRF_TOKEN = wiki_login()
		return make_http_request(endpoint, method, payload, True)

	return data


# API call to delete a page or file
def delete_wiki_page(title, reason=''):
	data = make_http_request(BASE_API_URL, 'POST', payload={
        "action": "delete",
        "title": title,
        "reason": reason,
        "format": "json"
	})

	return data
