import datetime as dt
import logging

import discord
from discord import app_commands
from discord.ext import commands

from calendar_events import SpecialEvent, get_events
from goonbot import Goonbot
from text_processing import comma_list


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

    @app_commands.command(name="today", description="Check if today has any special events!")
    async def today(self, interaction: discord.Interaction):
        """Check if today has a special event!"""
        today = dt.date.today()

        # Gather and sort events
        events = get_events(today, remaining_only=True)
        today_events = [e for e in events if e.is_today()]
        tomorrow_events = [e for e in events if e.is_tomorrow()]
        remaining_events = [e for e in events if not e.is_today() and not e.is_tomorrow()]

        today_embed = self.bot.embed()
        # No events today or tomorrow
        if not today_events and not tomorrow_events:
            # Get the next event, that isn't today or tomorrow
            if remaining_events:
                next_event = remaining_events[0]
                today_embed.title = f"{next_event.days_until} days until {next_event}"
            # I don't think this would ever display the the end user,
            # but I'd rather cover all the edge cases
            today_embed.title = "There are no more events for this year."
            today_embed.description = f"Enjoy the rest of {today.year}."

        # No events today, but event tomorrow
        if not today_events and tomorrow_events:
            today_embed.title = f"Tomorrow is {comma_list([e.name for e in tomorrow_events])}"

        # Events today, and tomorrow
        if today_events and tomorrow_events:
            today_embed.title = f"Today is {comma_list([e.name for e in today_events])}"
            today_embed.description = f"...and tomorrow is {comma_list([e.name for e in tomorrow_events])}"

        # Event(s) today, but not tomorrow (arguably the default case)
        if today_events and not tomorrow_events:
            today_embed.title = f"Today is {comma_list([e.name for e in today_events])}"

        # Send it
        await interaction.response.send_message(embed=today_embed)


async def setup(bot):
    await bot.add_cog(GoonCalendar(bot=bot))
