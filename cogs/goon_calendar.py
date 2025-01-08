import datetime as dt
import logging

import discord
from dateutil import tz
from discord import app_commands
from discord.ext import commands, tasks

from calendar_events import get_special_events
from goonbot import Goonbot
from text_processing import comma_list, join_lines

eight_am_cst = dt.time(hour=8, minute=0, second=0, tzinfo=tz.gettz("America/Chicago"))


class GoonCalendar(commands.Cog):
    # Basic in-memory cache. Keeps the bot from needing to calculate and create embeds
    # for each command more than once a day, so long as the bot isn't restarted
    today_command_last_called_date: dt.date | None = None
    today_embed_cache: discord.Embed | None = None

    calendar_command_last_called_date: dt.date | None = None
    calendar_embed_cache: discord.Embed | None = None

    def __init__(self, bot: Goonbot):
        self.bot = bot
        self.announce_birthdays.start()

    @app_commands.command(name="calendar")
    @app_commands.describe(show_remaining_only="Show only remaining events for this year??")
    async def calendar(self, interaction: discord.Interaction, show_remaining_only: bool = True):
        """Take a peak at the Goon Calendar"""
        today = dt.date.today()

        # See if cached embed is available
        if today == self.calendar_command_last_called_date and self.calendar_embed_cache:
            return await interaction.response.send_message(embed=self.calendar_embed_cache)

        # Create embed
        calendar_embed = self.bot.embed(title="Goon Calendar 📅")
        if show_remaining_only:
            calendar_embed.description = f"Events remaining for {today.year}!"
        else:
            calendar_embed.description = f"All events for {today.year}!"

        # Add events
        for event in get_special_events(today, show_remaining_only):
            calendar_embed.add_field(
                name=event.name,
                value=join_lines(
                    [
                        event.date.strftime("%A"),  # Day of the week. Format: Sunday, Monday, etc
                        event.date.strftime("%B %d"),  # Date. Format: January 1, February 18, etc
                    ]
                ),
            )

        # Send it
        await interaction.response.send_message(embed=calendar_embed)

    @app_commands.command(name="today", description="Check if today has any special events!")
    async def today(self, interaction: discord.Interaction):
        """Check if today has a special event!"""
        today = dt.date.today()

        # See if cached embed is available
        if today == self.today_command_last_called_date and self.today_embed_cache:
            return await interaction.response.send_message(embed=self.today_embed_cache)

        # Gather and sort events
        events = get_special_events(today, remaining_only=True)
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

        # No events today, but event tomorrow
        elif not today_events and tomorrow_events:
            today_embed.title = f"Tomorrow is {comma_list([e.name for e in tomorrow_events])}"

        # Events today, and tomorrow
        elif today_events and tomorrow_events:
            today_embed.title = f"Today is {comma_list([e.name for e in today_events])}"
            today_embed.description = f"...and tomorrow is {comma_list([e.name for e in tomorrow_events])}"

        # Event(s) today, but not tomorrow (arguably the default case)
        elif today_events and not tomorrow_events:
            today_embed.title = f"Today is {comma_list([e.name for e in today_events])}"

        # Because New Year's Eve and New Year's Day are tracked, I don't think this case would ever be
        # encountered. But if so, why not add a fun easter egg.
        else:
            logging.warning(f"Edge case encountered, is this a bug? Date: {today.isoformat}")
            today_embed.title = "There are no more events for this year."
            today_embed.description = f"Enjoy the rest of {today.year}."
            assert isinstance(interaction.channel, discord.TextChannel)
            await interaction.channel.send(
                embed=self.bot.embed(
                    title="Hey, look.",
                    description=f"It's that weird edge case <@{self.bot.owner_id}> thought he'd never be encountered.",
                ),
            )

        # Send it
        self.today_command_last_called_date = today
        self.today_embed_cache = today_embed
        await interaction.response.send_message(embed=today_embed)

    @tasks.loop(time=eight_am_cst)
    async def announce_birthdays(self):
        """Announces birthdays in the goonhq channel at 8am CST"""
        # Fresh date
        today = dt.date.today()

        # All birthdays today
        today_birthdays = [
            event
            for event in get_special_events(today, remaining_only=True)
            if event.is_today() and event.event_type == "birthday"
        ]

        # No birthdays today, exit early
        if not len(today_birthdays):
            logging.info("No birthdays today.")
            return

        # Fetch guild
        goonhq = self.bot.get_channel(177125557954281472)

        # Ensure it exists and is not a private channel
        assert isinstance(goonhq, (discord.abc.GuildChannel, discord.Thread))

        # Ensure correct channel type
        if goonhq.type != discord.ChannelType.text:
            return

        # Happy birthday embed
        today_birthday_embed = self.bot.embed()
        today_birthday_embed.title = f"Today is {comma_list([e.name for e in today_birthdays])}!"

        # Send it
        await goonhq.send(embed=today_birthday_embed)


async def setup(bot):
    await bot.add_cog(GoonCalendar(bot=bot))
