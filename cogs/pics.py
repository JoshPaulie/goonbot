import pathlib

import discord
from discord import app_commands
from discord.ext import commands

from bex_tools import cycle_random
from goonbot import Goonbot


class Pics(commands.Cog):
    rat_links = cycle_random(pathlib.Path("image_links/rats.txt").read_text().splitlines())
    cat_links = cycle_random(pathlib.Path("image_links/cats.txt").read_text().splitlines())
    paranormal_links = cycle_random(pathlib.Path("image_links/real.txt").read_text().splitlines())

    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="rat", description="Roll a rat 🐀")
    async def rat(self, interaction: discord.Interaction):
        """A goonbot classic, the /rat command sends a random image of a rat from a list, hand curated by community member Ectoplax"""
        next_rat = next(self.rat_links)
        await interaction.response.send_message(next_rat)

    @app_commands.command(name="cat", description=":3")
    async def cat(self, interaction: discord.Interaction):
        next_cat = next(self.cat_links)
        await interaction.response.send_message(next_cat)

    @app_commands.command(name="real", description="Sends a random paranormal video. Is it real?")
    async def real(self, interaction: discord.Interaction):
        next_paranormal_photo = next(self.rat_links)
        await interaction.response.send_message(next_paranormal_photo)
        message = await interaction.original_response()
        await message.add_reaction("✅")
        await message.add_reaction("❌")


async def setup(bot):
    await bot.add_cog(Pics(bot))