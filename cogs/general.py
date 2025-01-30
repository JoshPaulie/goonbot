import datetime as dt

import discord
from discord import app_commands
from discord.ext import commands

from bex_tools import CycleRandom
from goonbot import Goonbot


class General(commands.Cog):
    wow_no_invite_responses = CycleRandom(
        [
            "and good thing, I hate doing that with my friend.",
            "dang and I really like doing that..",
            "i was busy anyway.",
            "did it get lost in the mail?",
            "not shocked",
            "i thought we were friends?",
            "guess I'll hang out here..alone..",
            "that's too bad, I'll be doing something much cooler",
            "i'm starting to get the impression you don't actually want to hangout with me",
            "are you mad at me?",
        ]
    )

    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="wni", description="Wow, no invite?")
    async def wow_no_invite(self, interaction: discord.Interaction):
        """Make it known you would have loved whatever it is they're doing (without you)"""
        await interaction.response.send_message(
            embed=self.bot.embed(
                title="Wow, no invite?",
                description=next(self.wow_no_invite_responses),
            )
        )

    @app_commands.command(name="wie", description="Where is everybody?")
    async def where_is_everybody(self, interaction: discord.Interaction):
        """
        Used to broadcast you're board and want to hang out/play games in VC.

        Sends a message indicating the general time of day (morning, afternoon, night) based on the current hour.

        The time of day is determined as follows:
        - 12AM to 3AM is considered the previous day's night.
          - For example, 2AM Sunday is treated as Saturday night.
        - 4AM to 11AM is considered morning.
        - 12PM to 5PM is considered afternoon.
        - 6PM to 11:59PM is considered night.
        """
        today = dt.datetime.today()
        current_hour = dt.datetime.now().hour
        response = self.bot.embed(title="Where is everybody?")

        # 12AM to 3AM (Night of previous day)
        if 0 <= current_hour <= 3:
            today -= dt.timedelta(days=1)
            response.description = f"It's a {today.strftime('%A')} night!"
        # 4AM to 11AM
        elif 4 <= current_hour <= 11:
            response.description = f"It's a {today.strftime('%A')} morning!"
        # 12PM to 5PM
        elif 12 <= current_hour <= 17:
            response.description = f"It's a {today.strftime('%A')} afternoon!"
        # 6PM to 11:59PM
        else:
            response.description = f"It's a {today.strftime('%A')} night!"

        await interaction.response.send_message(embed=response)


async def setup(bot):
    await bot.add_cog(General(bot))
