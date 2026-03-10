from adhoc_common import *


WILDCARD_SEARCH = '/User Claim'

async def main():
	await setup()

	response = await make_http_request({
		"action": "query",
		"list": "search",
		"srsearch": '"User Claim"',
		"srnamespace": 2,
		"srlimit": "max",
		"format": "json"
	}, 'POST')

	print(json.dumps(response, indent=4))

	for page in response['query']['search']:
		await delete_wiki_page(page['title'], f'Automated purge of {WILDCARD_SEARCH} pages by Sorabot')


if __name__ == '__main__':
	asyncio.run(main())
