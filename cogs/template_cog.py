import logging

import discord
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot


class TemplateCog(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="template_command")
    @app_commands.describe(first_argument="First argument description")
    async def basic_command(self, interaction: discord.Interaction, first_argument: bool = True):
        """Template command description"""
        await interaction.response.send_message(
            embed=self.bot.embed(
                title="This is a template command!",
            ),
        )


async def setup(bot):
    await bot.add_cog(TemplateCog(bot))
