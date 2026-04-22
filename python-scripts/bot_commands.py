from imports import *


class CommandsCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot


	# prefix commands

	# pull latest code from GitHub and restart itself
	@commands.command(name='update')
	async def update_code(self, context):
		await context.send(BOT_VOICELINES['update'])
		subprocess.run(f"cd {LINUX_ABSOLUTE_PATH} && git reset --hard HEAD && git pull", shell=True)
		subprocess.run(['sudo', 'systemctl', 'restart', LINUX_SERVICE_NAME])


	# toggle sleep mode which disables slash commands as well as message and reaction handlers
	# the goal is to avoid shutting down the remote instance during local testing which defeats the purpose of the update prefix command
	@commands.command(name='sleep')
	async def sleep(self, context):
		var_global.SLEEP_MODE = not var_global.SLEEP_MODE
		await context.send(BOT_VOICELINES['sleep' if var_global.SLEEP_MODE else 'wake'])


	# slash commands

	# disable slash command execution during sleep mode or from unauthorised users
	async def interaction_check(self, interaction):
		var_global.OPERATION_LOGGER.info(f'@{interaction.user.display_name} used /{interaction.command.name}')
		return not var_global.SLEEP_MODE and check_user_elevation(interaction.user)


	# common function for abandon and submit commands
	async def act_on_missions(self, interaction, mission_id, action):
		await interaction.response.defer(ephemeral=True)

		mission = await mentat_request(f'/api/v1/missions/{mission_id}')

		if mission.get('error') == 'Mission not found':
			reply = f"There is no Wiki Mission with ID {mission_id}."

		# make sure mission is active and claimed
		elif mission.get('status') == 'accepted':

			if action == 'abandon':
				user_id = mission['assignee']
				reply = f"User <@{user_id}> has been removed from Wiki Mission {mission_id}."

			elif action == 'submit':
				reply = f"Wiki Mission {mission_id} has been sent for approval."

			await mentat_request(f'/api/v1/missions/{mission_id}/{action}', method='PUT')

		else:
			reply = f"Wiki Mission {mission_id} is not in progress."

		await interaction.followup.send(reply)


	@app_commands.command(name='unassign_mission', description='Clears the active assignee from an ongoing mission')
	@app_commands.default_permissions(manage_messages=True)
	@app_commands.guilds(SERVER_ID)
	async def unassign_mission(self, interaction: discord.Interaction, mission_id: int):
		await self.act_on_missions(interaction, mission_id, 'abandon')


	@app_commands.command(name='force_submit_mission', description='Manually send a mission for approval')
	@app_commands.default_permissions(manage_messages=True)
	@app_commands.guilds(SERVER_ID)
	async def force_submit_mission(self, interaction: discord.Interaction, mission_id: int):
		await self.act_on_missions(interaction, mission_id, 'submit')


	@app_commands.command(name='available_missions', description='Counts number of available missions left')
	@app_commands.default_permissions(manage_messages=True)
	@app_commands.guilds(SERVER_ID)
	async def available_missions(self, interaction: discord.Interaction):
		await interaction.response.defer()

		messages = [message async for message in var_global.CHANNELS['available'].history(limit=None)]

		await interaction.followup.send(f"There are {len(messages)}~ Wiki Missions left in <#{CHANNEL_IDS['available']}>.")


	@app_commands.command(name='cleanup_missions', description='Abandons ongoing missions whose assignees have left the server')
	@app_commands.default_permissions(manage_messages=True)
	@app_commands.guilds(SERVER_ID)
	async def cleanup_missions(self, interaction: discord.Interaction):
		await interaction.response.defer(ephemeral=True)

		messages = [message async for message in var_global.CHANNELS['ongoing'].history(limit=None)]
		for mission in messages:
			embed = mission.embeds[0]
			mission_id = re.search(r'\[(\d+)\]', embed.title).group(1)

			# check if mission has been claimed for longer than 2 weeks
			two_weeks = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(weeks=2)
			if embed.timestamp < two_weeks:
				await mentat_request(f'/api/v1/missions/{mission_id}/abandon', method='PUT')
				continue

			# check if user is still in the server
			assignee = embed.fields[-1].value
			assignee_id = int(re.search(r'<@(\d+)>', assignee).group(1))

			try:
				await interaction.guild.fetch_member(assignee_id)
			except discord.errors.NotFound:
				await mentat_request(f'/api/v1/missions/{mission_id}/abandon', method='PUT')

		await interaction.followup.send(f"Wiki Missions with absent assignees (i.e. left the server or MIA >2 weeks) have been force-abandoned.")


async def setup(bot):
	await bot.add_cog(CommandsCog(bot))
