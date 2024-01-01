import discord
from discord import ui


class BugReportModal(ui.Modal, title="Bug Report"):
    details = ui.TextInput(label="Details", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Thanks for your bug report", ephemeral=True)
