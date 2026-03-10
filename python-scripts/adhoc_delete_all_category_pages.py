from adhoc_common import *


CATEGORY_NAME = 'Discord Verifications'

async def main():
	await setup()

	response = await make_http_request({
		'action': 'query',
		'list': 'categorymembers',
		'cmtitle': f'Category:{CATEGORY_NAME}',
		'cmlimit': 'max',
		'format': 'json',
	}, 'POST')

	print(json.dumps(response, indent=4))

	for page in response['query']['categorymembers']:
		await delete_wiki_page(page['title'], f'Automated purge of {CATEGORY_NAME} pages by Sorabot')


if __name__ == '__main__':
    asyncio.run(main())
