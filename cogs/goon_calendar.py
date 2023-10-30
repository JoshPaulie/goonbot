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
        """Check if today has a special event!"""
        today = dt.date.today()
        events = get_events(today, remaining_only=True)
        todays_events = [e for e in events if e.is_today()]
        remaining_events = [e for e in events if not e.is_today()]
        next_event = remaining_events[0]
        # Create embed
        today_embed = self.bot.embed()
        # How many days until next event (default title)
        today_embed.title = f"{next_event.days_until} days until {next_event.name}"
        # If there's an event tomorrow, make it the highlight (might get overwritten later)
        tomorrow = today + dt.timedelta(days=1)
        if next_event.date == tomorrow:
            today_embed.title = f"Tomorrow is {next_event.name}"
        # Unless today has an event, then add a reminder (as a description)
        if next_event.date == tomorrow and todays_events:
            today_embed.description = f"and tomorrow is {next_event.name}"
        # If today has anything special going on, overwrite the default title
        if todays_events:
            todays_events_str = " and ".join(e.name for e in todays_events)
            today_embed.title = f"Today is {todays_events_str}"
        # Send it
        await interaction.response.send_message(embed=today_embed)


async def setup(bot):
    await bot.add_cog(GoonCalendar(bot=bot))
