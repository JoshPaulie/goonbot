import logging
from dataclasses import dataclass
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot


@dataclass
class Creator:
    name: str
    youtube_username: Optional[str]
    twitch_username: Optional[str]


class CreatorView(discord.ui.View):
    def __init__(
        self,
        *,
        timeout: float | None = 180,
        creator_name: str,
        youtube_channel_id: Optional[str],
        twitch_username: Optional[str]
    ):
        super().__init__(timeout=timeout)

        if youtube_channel_id and not twitch_username:
            # Send latest youtube, remove view
            pass

        if twitch_username and not youtube_channel_id:
            # Send if they are live, remove view
            pass


class CreatorWatch(commands.Cog):
    """Quickly link to selected creator's youtube or twitch"""

    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="template_command")
    @app_commands.describe(first_argument="First argument description")
    async def basic_command(
        self, interaction: discord.Interaction, first_argument: bool = True
    ):
        """Template command description"""
        await interaction.response.send_message(
            embed=self.bot.embed(
                title="This is a template command!",
            ),
        )


async def setup(bot):
    await bot.add_cog(CreatorWatch(bot))
