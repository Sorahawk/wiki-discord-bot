from imports import *


class CommandsCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot


	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		return False if var_global.SLEEP_MODE else True


	# prefix commands

	# pull latest code from GitHub and restart itself
	@commands.command(name="update")
	@commands.has_permissions(administrator=True)
	async def update_code(self, context):

		# only act on remote instance
		if sys.platform == 'linux':
			await context.send("Stand by. Checking the mail for updates.")

			# reset any changes that could have been made to the project folder and pull latest code
			subprocess.run(f"cd {LINUX_ABSOLUTE_PATH} && git reset --hard HEAD && git pull", shell=True)

			# restart service
			subprocess.run(['sudo', 'systemctl', 'restart', LINUX_SERVICE_NAME])


	# toggle sleep mode which disables slash commands as well as message and reaction handlers
	# the goal is to avoid shutting down the remote instance during local testing which defeats the purpose of the update prefix command
	@commands.command(name="sleep")
	@commands.has_permissions(administrator=True)
	async def sleep(self, context):

		# only act on remote instance
		if sys.platform == 'linux':

			# flip boolean
			var_global.SLEEP_MODE = not var_global.SLEEP_MODE

			if var_global.SLEEP_MODE:
				reply = "Your dull chatter is putting me to sleep."
			else:
				reply = "What did I miss? Wait, I don't care."

			await context.send(reply)


	# slash commands

	@discord.app_commands.command(name="available_missions", description="Counts number of available missions left")
	async def available_missions(self, interaction: discord.Interaction):
		await interaction.response.defer()

		messages = [message async for message in var_global.CHANNELS['available'].history(limit=None)]
		num_missions = len(messages)

		await interaction.followup.send(f"There are {num_missions}~ Wiki Missions left in <#{CHANNEL_IDS['available']}>.")


	@discord.app_commands.command(name="cleanup_missions", description="Abandons ongoing missions whose assignees have left the server")
	async def cleanup_missions(self, interaction: discord.Interaction):
		await interaction.response.defer(ephemeral=True)

		messages = [message async for message in var_global.CHANNELS['ongoing'].history(limit=None)]
		for mission in messages:
			embed = mission.embeds[0]

			# check if user is still in the server
			assignee = embed.fields[-1].value
			user_id = re.search(r'<@(\d+)>', assignee).group(1)

			try:
				await interaction.guild.fetch_member(user_id)

			except discord.errors.NotFound:
				# abandon mission
				title = embed.title
				mission_id = re.search(r'\[(\d+)\]', title).group(1)

				await mentat_request(f'/api/v1/missions/{mission_id}/abandon', method='PUT')

		await interaction.followup.send(f"Wiki Missions with assignees who are no longer in the server have been force-abandoned.")


	@discord.app_commands.command(name="unassign_mission", description="Clears the active assignee from an ongoing mission")
	async def unassign_mission(self, interaction: discord.Interaction, mission_id: int):
		await interaction.response.defer(ephemeral=True)

		mission = await mentat_request(f'/api/v1/missions/{mission_id}')

		if mission.get('error') == 'Mission not found':
			reply = f"There is no Wiki Mission with ID {mission_id}."

		# make sure mission is active and claimed
		elif mission.get('status') == 'accepted':
			user_id = mission['assignee']
			reply = f"User <@{user_id}> has been removed from Wiki Mission {mission_id}."

			await mentat_request(f'/api/v1/missions/{mission_id}/abandon', method='PUT')

		else:
			reply = f"Wiki Mission {mission_id} is not in progress."

		await interaction.followup.send(reply)


	@discord.app_commands.command(name="force_submit_mission", description="Manually send a mission for approval")
	async def force_submit_mission(self, interaction: discord.Interaction, mission_id: int):
		await interaction.response.defer(ephemeral=True)

		mission = await mentat_request(f'/api/v1/missions/{mission_id}')

		if mission.get('error') == 'Mission not found':
			reply = f"There is no Wiki Mission with ID {mission_id}."

		# make sure mission is active and claimed
		elif mission.get('status') == 'accepted':
			await mentat_request(f'/api/v1/missions/{mission_id}/submit', method='PUT')

		else:
			reply = f"Wiki Mission {mission_id} is not in progress."

		await interaction.followup.send(reply)


async def setup(bot):
	await bot.add_cog(CommandsCog(bot))
