from imports import *


# runs a git command in the wiki repo folder and returns the output
async def git_run(*args):
	var_global.OPERATION_LOGGER.info(f"Executing in local repo: git {' '.join(args)}")

	process = await asyncio.create_subprocess_exec(
		'git', '-C', REPO_PAGES_PATH,
		'-c', 'core.quotePath=false', '-c', 'gc.auto=0',
		'-c', 'http.lowSpeedLimit=1000', '-c', 'http.lowSpeedTime=30',
		*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
	)

	stdout, stderr = await process.communicate()

	if process.returncode:
		raise RuntimeError(f"git {' '.join(args)} failed ({process.returncode}): {stderr.decode().strip()}")

	output = stdout.decode().strip()
	var_global.OPERATION_LOGGER.info(output)
	return output


# returns the full SHA of the current head
async def get_head_sha():
	return await git_run('rev-parse', 'HEAD')


# returns the SHA origin/main currently points to, without fetching any objects
async def get_remote_head_sha():
	output = await git_run('ls-remote', 'origin', 'main')
	return output.split()[0] if output else None


# discards any local changes and hard-resets the repo to the remote branch
async def reset_to_remote():
	await git_run('fetch', 'origin', 'main')
	await git_run('reset', '--hard', f'origin/main')


# returns the subject line of the most recent commit touching the given path
async def get_last_commit_subject(rel_path):
	return await git_run('log', '-1', '--format=%s', '--', str(rel_path))


# returns paths of files that changed between base_sha and HEAD
async def get_changed_paths(base_sha):
	try:
		await git_run('merge-base', '--is-ancestor', base_sha, 'HEAD')

	except RuntimeError:  # base_sha unreachable from HEAD, e.g. due to force-push, re-clone
		return None

	output = await git_run('diff', '--name-only', '--relative', base_sha, 'HEAD')
	return output.splitlines()


# stages the repo, commits if anything changed, and pushes
# returns True if a commit was made, otherwise False
async def commit_and_push(message):
	await git_run('add', '.')

	if not await git_run('diff', '--cached', '--name-only'):  # file contents are identical to HEAD e.g. intermediate edits reverted
		return False

	await git_run('commit', '-m', message)
	await git_run('push', 'origin', 'main')
	return True
