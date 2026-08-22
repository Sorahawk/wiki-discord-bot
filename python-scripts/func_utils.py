from imports import *


# returns True if message author is elevated, otherwise False
def check_user_elevation(member):
	# elevation check will fail in DMs because there are no roles to verify permissions
	return any(role.id in ELEVATED_USER_ROLES for role in getattr(member, 'roles', []))


# returns a Discord File object
def generate_file(content, filename):
	return discord.File(io.StringIO(content), filename=filename)


# returns a matching reply, if any, from the specificed BOT_REPLIES list
def check_replies(message, reply_list):
	for reply in reply_list:
		if any(phrase.lower() in message.content.lower() for phrase in reply[0]):
			return reply[1]


# returns a string where every line is formatted to be a blockquote
def format_blockquotes(text):
	return '\n'.join(f'> {line}' for line in text.splitlines())


# fetches attachments as discord.File objects before Discord purges them
async def fetch_attachments_as_files(attachments):
	files = []

	for attachment in attachments:
		response = await var_global.SESSION.get(attachment.url)

		if response.status_code == 200:
			files.append(discord.File(io.BytesIO(response.content), filename=attachment.filename))

	return files


# converts a repo-relative path into its corresponding wiki page title
# the subfolder name becomes the title prefix, and loose root files get no prefix
def resolve_title(rel_path):
	parts = rel_path.parts
	prefix = f'{parts[0]}:' if len(parts) > 1 else ''

	return prefix + filename_to_title(rel_path)


# converts a filename into its corresponding page title
def filename_to_title(rel_path):
	# css and js extensions are retained because they form part of the real title
	stem = rel_path.name if rel_path.suffix in ('.css', '.js') else rel_path.stem

	# hashtags represent subpage separators, and underscores represent whitespaces
	return stem.replace('#', '/').replace('_', ' ')


# returns the content model to assign when creating a page, inferred from the file extension
def get_content_model(full_path):
	return CONTENT_MODELS.get(full_path.suffix)


# walks the wiki repo and returns two dicts keyed by page title:
# first one has corresponding file content as value
# second one has tuple (full path, relative path) as value
# specify a set of titles to filter only those files, or None to read the entire tree
def collect_local_pages(titles=None):
	repo_root = Path(REPO_PAGES_PATH)
	local_by_title, file_by_title = {}, {}

	for full_path in (repo_root).rglob('*'):
		if not full_path.is_file():
			continue

		rel_path = full_path.relative_to(repo_root)
		title = resolve_title(rel_path)

		if titles is not None and title not in titles:
			continue

		local_by_title[title] = full_path.read_text(encoding='utf-8')
		file_by_title[title] = (full_path, rel_path)

	return local_by_title, file_by_title
