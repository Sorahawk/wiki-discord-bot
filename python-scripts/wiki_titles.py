from imports import *


# converts a repo-relative path into its corresponding wiki page title
# the subfolder name becomes the title prefix, and loose root files get no prefix
def resolve_title(rel_path):
	parts = rel_path.parts[1:]
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
	repo_root = Path(WIKI_REPO_PATH)
	local_by_title, file_by_title = {}, {}

	for full_path in (repo_root / PAGES_ROOT).rglob('*'):
		if not full_path.is_file():
			continue

		rel_path = full_path.relative_to(repo_root)
		title = resolve_title(rel_path)
		if titles is not None and title not in titles:
			continue

		local_by_title[title] = full_path.read_text(encoding='utf-8')
		file_by_title[title] = (full_path, rel_path)

	return local_by_title, file_by_title


# checks content for unresolved merge conflict markers
def has_conflict_markers(content):
	has_opening, has_closing, has_separator = False, False, False

	# look for a pair of opening and closing markers or a lone marker alongside a bare separator line
	# this is to prevent false-positives from decorative '=======' in comments or wikitext
	for line in content.splitlines():
		if line.startswith('<<<<<<<') or line.startswith('|||||||'):
			has_opening = True
		elif line.startswith('>>>>>>>'):
			has_closing = True
		elif line.rstrip() == '=======':
			has_separator = True

	return (has_opening and has_closing) or ((has_opening or has_closing) and has_separator)
