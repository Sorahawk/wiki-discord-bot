from adhoc_common import *


WILDCARD_SEARCH = 'Patent'
NAMESPACENUMBER = 0

async def main():
	await setup()

	response = await make_http_request({
		"action": "query",
		"list": "search",
		"srsearch": f'{WILDCARD_SEARCH}',
		"srnamespace": NAMESPACENUMBER,
		"srlimit": "max",
		"format": "json"
	}, 'POST')

	print(json.dumps(response, indent=4))

	for page in response['query']['search']:
		await delete_wiki_page(page['title'], f'Automated purge of {WILDCARD_SEARCH} pages by Sorabot')


if __name__ == '__main__':
	asyncio.run(main())
