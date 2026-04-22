from wiki_adhoc_common import *


async def main():
	await setup()

	# insert adhoc code BELOW
	response = await wiki_request({}, method='GET', token_type=None)
	print(json.dumps(response, indent=4))



	# insert adhoc code ABOVE



asyncio.run(main())
