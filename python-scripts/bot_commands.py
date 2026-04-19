from imports import *


class CommandsCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot


	# prefix commands

	@commands.command(name="update")
	@commands.has_permissions(administrator=True)
	async def update_code(self, context):

		# only need to update remote instance
		if sys.platform == 'linux':
			await context.send("Stand by. Checking the mail for updates.")

			# reset any changes that could have been made to the project folder and pull latest code
			subprocess.run(f"cd {LINUX_ABSOLUTE_PATH} && git reset --hard HEAD && git pull", shell=True)

			# restart service
			subprocess.run(['sudo', 'systemctl', 'restart', LINUX_SERVICE_NAME])

		else:
			await context.send("No updates are required in this instance.")


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

		await interaction.followup.send(f"Missions with assignees who are no longer in the server have been force-abandoned.")


async def setup(bot):
	await bot.add_cog(CommandsCog(bot))
