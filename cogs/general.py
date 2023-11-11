import datetime as dt
import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot


class General(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(
        name="wni",
        description="Wow, no invite?",
    )
    async def wow_no_invite(self, interaction: discord.Interaction):
        """Make it known you would have loved whatever it is they're doing (without you)"""
        await interaction.response.send_message(
            embed=self.bot.embed(
                title="Wow, no invite?",
                description=random.choice(
                    [
                        "and good thing, I hate doing that with my friend.",
                        "dang and I really like doing that..",
                        "i was busy anyway.",
                        "did it get lost in the mail?",
                        "not shocked",
                        "i thought we were friends?",
                        "guess I'll hang out here..alone..",
                        "that's too bad, I'll be doing something much cooler"
                        "i'm starting to get the impression you don't actually want to hangout with me",
                        "are you mad at me?",
                    ]
                ),
            )
        )

    @app_commands.command(
        name="wie",
        description="Where is everybody?",
    )
    async def where_is_everybody(self, interaction: discord.Interaction):
        """Used to broadcast you're board and alone in VC"""
        day_of_the_week = dt.datetime.today()
        current_hour = dt.datetime.now().hour
        response = self.bot.embed(title="Where is everybody?")
        # 12AM to 4AM
        if current_hour in [n for n in range(0, 3 + 1)]:
            # Early morning should be night of the day after
            day_of_the_week -= dt.timedelta(days=1)
            response.description = f"It's a {day_of_the_week.strftime('%A')} night!"
        # 6AM to 12PM
        elif current_hour in [n for n in range(6, 11 + 1)]:
            response.description = f"It's a {day_of_the_week.strftime('%A')} morning!"
        # 1PM to 5PM
        elif current_hour in [n for n in range(13, 16 + 1)]:
            response.description = f"It's a {day_of_the_week.strftime('%A')} afternoon!"
        # 6PM to (effectively) 4AM
        else:
            response.description = f"It's a {day_of_the_week.strftime('%A')} night!"
        await interaction.response.send_message(embed=response)


async def setup(bot):
    await bot.add_cog(General(bot))
