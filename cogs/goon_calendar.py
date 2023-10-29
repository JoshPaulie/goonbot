import datetime as dt
import logging

import discord
from discord import app_commands
from discord.ext import commands

from calendar_events import get_events
from goonbot import Goonbot


class GoonCalendar(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="calendar")
    @app_commands.describe(show_remaining_only="Show only remaining events for this year??")
    async def calendar(self, interaction: discord.Interaction, show_remaining_only: bool = True):
        """Take a peak at the Goon Calendar"""
        today = dt.date.today()
        # Create embed
        calendar_embed = self.bot.embed(title="Goon Calendar 📅")
        if show_remaining_only:
            calendar_embed.description = f"Events remaining for {today.year}!"
        # Add events
        for event in get_events(today, show_remaining_only):
            calendar_embed.add_field(
                name=event.name,
                value=event.date.strftime("%B %d (%a)"),
            )
        # Send it
        await interaction.response.send_message(embed=calendar_embed)

    @app_commands.command(name="today")
    async def today(self, interaction: discord.Interaction):
        today = dt.date.today()
        today_embed = self.bot.embed()
        events = get_events(today, remaining_only=True)
        todays_events = [e for e in events if e.is_today]
        if todays_events:
            todays_events_str = " and ".join(e.name for e in todays_events if e.is_today)
            today_embed.title = f"Today is {todays_events_str}!"
            await interaction.response.send_message(embed=today_embed)


async def setup(bot):
    await bot.add_cog(GoonCalendar(bot=bot))
