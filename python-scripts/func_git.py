from imports import *


# runs a git command in the wiki repo folder and returns the output
async def git_run(*args):
	process = await asyncio.create_subprocess_exec(
		'git', '-C', REPO_PAGES_PATH,
		'-c', 'core.quotePath=false', '-c', 'gc.auto=0',
		'-c', 'http.lowSpeedLimit=1000', '-c', 'http.lowSpeedTime=30',
		*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
	)

	stdout, stderr = await process.communicate()
	return stdout.decode().strip()


# returns the full SHA of the current head
async def get_head_sha():
	return await git_run('rev-parse', 'HEAD')


# discards any local changes and hard-resets the repo to the remote branch
async def reset_to_remote(branch='main'):
	await git_run('fetch', 'origin', branch)
	await git_run('reset', '--hard', f'origin/{branch}')


# returns the subject line of the most recent commit touching the given path
async def get_last_commit_subject(rel_path):
	return await git_run('log', '-1', '--format=%s', '--', str(rel_path))


# returns paths of files that changed between base_sha and HEAD
async def get_changed_paths(base_sha, subpath):
	try:
		await git_run('merge-base', '--is-ancestor', base_sha, 'HEAD')

	except RuntimeError:  # base_sha unreachable from HEAD, e.g. due to force-push, re-clone
		return None

	output = await git_run('diff', '--name-only', base_sha, 'HEAD', '--', subpath)
	return output.splitlines()


# stages the given subpath, commits if anything changed, and pushes
# returns True if a commit was made, otherwise False
async def commit_and_push(subpath, message, branch='main'):
	await git_run('add', subpath)

	if not await git_run('diff', '--cached', '--name-only'):  # file contents are identical to HEAD e.g. intermediate edits reverted
		return False

	await git_run('commit', '-m', message)
	await git_run('push', 'origin', branch)
	return True
