import datetime as dt
import logging

import discord
from discord import app_commands
from discord.ext import commands

import calendar_events
from goonbot import Goonbot


class GoonCalendar(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="calendar")
    @app_commands.describe(show_remaining_only="Show only remaining events for this year??")
    async def calendar(self, interaction: discord.Interaction, show_remaining_only: bool = True):
        """Take a peak at the Goon Calendar"""
        calendar_embed = self.bot.embed(title="Goon Calendar 📅")

        events = calendar_events.SORTED_CALENDAR_EVENTS
        if show_remaining_only:
            calendar_embed.description = "Events remaining for the year!"
            events = {event: date for event, date in events.items() if date > dt.date.today()}

        for event, event_date in events.items():
            calendar_embed.add_field(
                name=event,
                value=event_date.strftime("%B %d (%a)"),
                inline=False,
            )
        await interaction.response.send_message(embed=calendar_embed)


async def setup(bot):
    await bot.add_cog(GoonCalendar(bot=bot))
