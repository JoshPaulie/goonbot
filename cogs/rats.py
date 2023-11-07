import logging
import pathlib
import random
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bex_tools import cycle_random
from goonbot import Goonbot


class ReportRat(discord.ui.View):
    """Allows users to notify me of "broken rats" (images don't load for whatever reason)"""

    def __init__(self, rat: str, bot: Goonbot):
        super().__init__(timeout=12)
        self.rat = rat
        self.bot = bot
        self.is_broken_rat = False

    async def on_timeout(self) -> None:
        self.stop()

    @discord.ui.button(label="Pet Rat", emoji="👋", style=discord.ButtonStyle.blurple)
    async def pet_rat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=self.bot.embed(
                title="🐀👋",
                url=self.rat,
            ),
            ephemeral=True,
        )
        self.stop()

    @discord.ui.button(label="Broken Rat", emoji="🚔", style=discord.ButtonStyle.grey)
    async def report_broken_rat(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Respond to suer
        await interaction.response.send_message(
            embed=self.bot.embed(
                title="Thanks for the report!",
                description="We'll take him out back.. 😵",
            ),
            ephemeral=True,
        )
        # Send DM to owner
        owner_id = self.bot.owner_id
        assert owner_id
        owner = self.bot.get_user(owner_id)
        assert owner
        await owner.send(
            embed=self.bot.embed(title="Broken rat 🐀", description=self.rat).set_footer(
                text=f"Reported by {interaction.user.name} (narc)"
            )
        )
        self.is_broken_rat = True
        alert_channel = discord.Object(id=1171291004175912980, type=discord.TextChannel)
        self.stop()


class Rats(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot
        self.rats = cycle_random(pathlib.Path("rats.txt").read_text().splitlines())

    @app_commands.command(name="rat")
    async def rat(self, interaction: discord.Interaction):
        next_rat = next(self.rats)
        report_rat = ReportRat(next_rat, self.bot)
        await interaction.response.send_message(
            embed=self.bot.embed(title="Rat").set_image(url=next_rat),
            view=report_rat,
        )
        await report_rat.wait()
        if report_rat.is_broken_rat:
            return await interaction.edit_original_response(
                embed=discord.Embed(title="This rat was broken", color=discord.Color.greyple()),
                view=None,
            )
        return await interaction.edit_original_response(view=None)


async def setup(bot):
    await bot.add_cog(Rats(bot))
