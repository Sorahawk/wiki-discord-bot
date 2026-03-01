from imports import *


# standard function for HTTP requests
def make_http_request(method='GET', endpoint=BASE_API_URL, payload={}, retry=False):
	session = var_global.SESSION
	if var_secret.WIKI_CSRF_TOKEN and not payload.get('token'):
		payload['token'] = var_secret.WIKI_CSRF_TOKEN

	var_global.OPERATION_LOGGER.info(f'Making {method} request to {endpoint} with payload {payload}.')
	if method == 'POST':
		response = session.request('POST', endpoint, data=payload)
	else:
		response = session.request(method, endpoint, params=payload)

	# retry once if token happened to expire before the periodic refresh
	if response.json().get('error', {}).get('code') in ['badtoken'] and not retry:
		check_wiki_session()
		response = make_http_request(method, endpoint, payload, True)

	return response


# retrieve token
def get_wiki_token(token_type='csrf'):
	response = make_http_request(payload={
		'action': 'query',
		'meta': 'tokens',
		'type': token_type,
		'format': 'json'
	})
	return response.json()['query']['tokens'][f'{token_type}token']


# login to wiki
def wiki_login():
	login_token = get_wiki_token('login')

	response = make_http_request('POST', payload={
		'action': 'login',
		'lgname': var_secret.WIKI_CREDS[0],
		'lgpassword': var_secret.WIKI_CREDS[1],
		'lgtoken': login_token,
		'format': 'json'
	})

	data = response.json()['login']

	if data['result'] == 'Success':
		var_global.OPERATION_LOGGER.info(f'Successfully logged into Wiki as {data['lgusername']}.')
		var_secret.WIKI_CSRF_TOKEN = get_wiki_token()
	else:
		raise Exception(f'Wiki login failed: {data['result']} - {data.get('reason', 'no reason specified')}.')


# check if login session is still valid
def check_wiki_session():
    response = make_http_request(payload={
        'action': 'query',
        'meta': 'userinfo',
        'format': 'json'
    })

    user = response.json()['query']['userinfo']

    # if session is expired, MediaWiki returns an anonymous user
    if user.get('anon') is not None:
        var_global.OPERATION_LOGGER.warning('Wiki session expired; now performing re-login.')
        wiki_login()
    else:
        var_global.OPERATION_LOGGER.info(f'Wiki session still active as: {user['name']}')
        # refresh the CSRF token just in case
        var_secret.WIKI_CSRF_TOKEN = get_wiki_token()


# API call to delete a page or file
def delete_wiki_page(title, reason=''):
	return make_http_request('POST', payload={
        'action': 'delete',
        'title': title,
        'reason': reason,
        'format': 'json'
	}).json()
