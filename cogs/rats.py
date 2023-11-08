import pathlib

import discord
from discord import app_commands
from discord.ext import commands

from bex_tools import cycle_random
from goonbot import Goonbot


class Rats(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot
        self.rats = cycle_random(pathlib.Path("rats.txt").read_text().splitlines())
        self.report_rat_ctx_menu = app_commands.ContextMenu(
            name="Report Rat", callback=self.report_broken_rat
        )
        self.bot.tree.add_command(self.report_rat_ctx_menu)

    async def report_broken_rat(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        if any([not message.embeds, not message.author == self.bot.user]):
            await interaction.response.send_message(
                "This isn't a rat post.", ephemeral=True
            )
        if message.embeds[0].title == "Rat":
            await interaction.response.send_message("Rat post!")

    @app_commands.command(name="rat")
    async def rat(self, interaction: discord.Interaction):
        """Roll a rat 🐀"""
        next_rat = next(self.rats)
        await interaction.response.send_message(
            embed=self.bot.embed(title="Rat").set_image(url=next_rat),
        )


async def setup(bot):
    await bot.add_cog(Rats(bot))
