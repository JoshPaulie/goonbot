import asyncio
import logging
import random
import re
import time
import traceback
from collections import defaultdict
from functools import partial
from pathlib import Path
from typing import Iterator

import discord
import humanize
from discord.ext import commands

from bex_tools import frontloaded_batched
from keys import Keys
from text_processing import acronymize, join_lines, md_codeblock


class Goonbot(commands.Bot):
    # Guilds
    GOON_HQ = discord.Object(177125557954281472, type=discord.Guild)  # Main ("production") server
    BOTTING_TOGETHER = discord.Object(510865274594131968, type=discord.Guild)  # Development server

    # Bot version
    VERSION = (6, 1, 3)

    # API secrets
    keys = Keys

    # Database path
    database_path = "gbdb.sqlite"

    # Used to calculate command execution times with on_interaction & on_app_command_completion
    command_timer_lock = asyncio.Lock()
    command_timer_journal = defaultdict(time.perf_counter)

    # A default embed that will sprinkled around (so I don't have to manually set the color every time)
    embed = partial(discord.Embed, color=discord.Color.blurple())

    def __init__(self, intents: discord.Intents, **kwargs):
        super().__init__(
            command_prefix=commands.when_mentioned_or("."),
            owner_id=177131156028784640,  # bexli
            help_command=None,
            intents=intents,
            **kwargs,
        )

    def ping_owner(self) -> str:
        return f"<@{self.owner_id}>"

    @staticmethod
    def get_cogs() -> Iterator[str]:
        """
        Yields files names from cogs/ folders, formatted so discord.py can load them into the bot as extensions.

        Example
            cogs/general.py -> cogs.general
        """
        files = Path("cogs").glob("*.py")
        for file in files:
            if not any(x in file.name for x in ["__init__", "template_cog", "utils"]):
                yield file.as_posix()[:-3].replace("/", ".")

    async def load_cogs(self) -> None:
        """Loads all of the files from cogs/ into the bot as extensions"""
        for cog in self.get_cogs():
            await self.load_extension(cog)
            logging.info(f"Loaded cog: {cog}!")

    async def setup_hook(self):
        """
        Called while the bot is logging in, but before it's ready to be used by users.
        Handles startup actions like call load_cogs()
        """
        await self.load_cogs()

    async def on_ready(self):
        """Called after the bot is finished logging in and is ready to use"""
        assert self.user
        logging.info(f"Logged on as {self.user} (ID: {self.user.id})")
        print(f"{self.user.name} is ready")


bot = commands.bot
# Bot instance
goonbot = Goonbot(
    # Gives the bot the ability to read messages, view profiles, etc
    intents=discord.Intents.all(),
)


# Generic last-resort error message to be sent, in hopes of negating all "interaction failed messages"
# (by effectively replacing it with a different error message lol)
# Doesn't catch "unknown interaction" failures
@goonbot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.HTTPException):
        if "fewer in length" in error.text:
            await interaction.followup.send(embed=goonbot.embed(title="This message was too long"))

    await interaction.followup.send(
        embed=goonbot.embed(
            title="An unknown error occurred. 😢",
            description=("Try again. If this happens many times, ping jarsh"),
        ),
        ephemeral=True,
    )
    logging.error(traceback.format_exc())


# Prefix commands
# Prefix commands are old school bot commands from years back. This bot uses "." as its prefix
# Nowadays, most commands are app_commands (aka /slash commands) and auto complete after you type "/"
# Prefix commands aren't listed in the app_command menu in discord, and were originally argrigated in the "help command"
# You'll notice the help command is disabled in the bot definition, as it's set to None. If it was enabled, users could see
# all of the prefix commands by typing ".help"


@goonbot.command(name="sync", description="[Meta] Syncs commands to server")
@commands.is_owner()
@commands.dm_only()
async def sync(ctx: commands.Context):
    """
    This command syncs all of the bot's commands (names & descriptions) to a all servers its in.
    It must be called from within DMs.

    ---
    Including a sync prefix command is a newer standard for discord.py bots, and is required to
    quickly debug and develop new features. Without syncing the bot command tree to a server, it
    can take an hour (or longer) for changes to trickle to all the servers the bot is in.

    It might be tempting to add the bot.tree.sync() line in bot.setup_hook().
    However, if you sync your bot commands every time it restarts, especially during the development
    of new features when frequent restarts are necessary, you'll get rate-limited by Discord into next week.
    They really don't like people spamming app command syncs to servers.
    """
    # Sync commands to all guilds
    await goonbot.tree.sync()

    # Gather list of guilds bot is in
    goonbot_guilds = [g.name for g in goonbot.guilds]
    goonbot_guilds_str = ", ".join(goonbot_guilds)

    # Confirmation message
    assert goonbot.user
    await ctx.send(
        embed=goonbot.embed(
            title="Synced ✅",
            description=f"{goonbot.user.name} commands synced to {goonbot_guilds_str}",
        )
    )


@goonbot.command(name="restart", aliases=["stop", "update"], description="[Meta] Restart the bot")
@commands.is_owner()
@commands.dm_only()
async def restart(ctx: commands.Context):
    """
    "Restarts" the bot by turning it off, so the service responsible for updating
    and running the bot will notice it's off and restart it.
    """
    await ctx.send(
        embed=goonbot.embed(
            title="Stopping the bot...",
            description="The service responsible for running the bot will notice it's off and restart it.",
        )
    )

    # Kill the bot routine
    await goonbot.close()


@goonbot.command(name="log", description="[Meta] Sends bot log")
@commands.is_owner()
async def log(ctx: commands.Context, page_num: int = 1, str_filter: str | None = None):
    """
    Crude way for me to read logs remotely.

    Batched into "pages" of N lines
    """
    # How many lines of the log to include per 'page'
    page_line_length = 20

    # Read in log file and split into lines
    log_lines = Path("bot.log").read_text().splitlines()

    # Filter is needed
    if str_filter:
        log_lines = [line for line in log_lines if str_filter.lower() in line.lower()]

    # Similar to batched, but odd-numbered group is at the start
    # Otherwise, since the log pages are served back-to-front, the first page may just be a few lines
    log_pages = frontloaded_batched(log_lines, page_line_length)

    # Prevent out of bounds error
    if page_num > len(log_pages):
        return await ctx.send("Invalid page number.")

    # Because it's a log file, we serve back-to-front
    page = log_pages[-page_num]

    # Send "page" of log file (with backticks for formatting)
    try:
        await ctx.send(
            md_codeblock(
                join_lines(
                    page,
                )
            )
            + f"Page **{page_num}** of **{len(log_pages)}**",
        )
    except discord.HTTPException as e:
        if re.search(r"Must be \d+ or fewer in length", e.text):
            await ctx.send(
                embed=goonbot.embed(
                    title="This page exceeded the character limit.",
                    description=f"Discord says:\n>>> {e.text}",
                )
            )


# This catches and processes ext (or "prefixed") commands
@goonbot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.NotOwner):
        await ctx.reply(
            embed=goonbot.embed(
                title="This is an administrative command, sorry 🤭",
                color=discord.Color.greyple(),
            ),
        )
    elif isinstance(error, commands.PrivateMessageOnly):
        await ctx.reply(
            embed=goonbot.embed(
                title="This command must be called from within DMs",
                color=discord.Color.greyple(),
            ),
        )
    else:
        # Without this line, prefixed commands throwing exceptions that will get gobbled
        # up by this event and make me real mad later when I break something
        logging.error(error)


# The following commands are used to log command execution time. `track_command_start` adds a
# timestamp and interaction ID pair to `command_timer` when a command interaction begins, then
# `log_command_elapsed_time` finds this pair and calculates the elapsed time.
@goonbot.listen("on_interaction")
async def track_command_start(interaction: discord.Interaction):
    # Logs the time when an app command starts an interation
    async with goonbot.command_timer_lock:
        if interaction.type == discord.InteractionType.application_command:
            assert interaction.command
            goonbot.command_timer_journal[interaction.id] = time.perf_counter()


@goonbot.listen("on_app_command_completion")
async def log_command_elapsed_time(interaction: discord.Interaction, command: discord.app_commands.Command):
    # When an app command is done processing and ready to send, check the command timer dict for the
    # interaction id. If interaction id present, we can calculate the execution time for the log
    async with goonbot.command_timer_lock:
        if command_start_time := goonbot.command_timer_journal.get(interaction.id):
            del goonbot.command_timer_journal[interaction.id]
            command_end_time = time.perf_counter()
            command_elapsed_time = command_end_time - command_start_time
            logging.info(f"{command.name} execution time: {round(command_elapsed_time, 3)}s")


# Context menus
# Context menus are most easily defined here, directly in the goonbot instance file
# Defining most of the general contexts menus here would make since
# but not for cog specific commands.

# For more on cog specific commands
# https://github.com/Rapptz/discord.py/issues/7823#issuecomment-1086830458

# > "What are context menus?"
# They're commands that you can bind to particular "contexts," namley messages or users.
# This enables you to right click either a message or a user, go to Apps,
# and a list will display with the available commands for that particular "context"


@goonbot.tree.context_menu(name="Delete")
async def delete_bot_message(interaction: discord.Interaction, message: discord.Message):
    """Allows community to clean up (delete) Goonbot messages"""
    # Make sure it's a goonbot message
    assert goonbot.user
    if not message.author == goonbot.user:
        return await interaction.response.send_message(
            embed=goonbot.embed(
                description=f"This command is meant to be used to delete {goonbot.user.mention} messages only 😡",
                color=discord.Color.greyple(),
            ),
            ephemeral=True,
        )

    if message.interaction and message.interaction.user.id != interaction.user.id:
        return await interaction.response.send_message(
            embed=goonbot.embed(
                description=f"Only {message.interaction.user.mention} can delete this message",
                color=discord.Color.greyple(),
            ),
            ephemeral=True,
        )

    # Send response to satisfy the discord interaction (without this the user gets "Interaction failed")
    await interaction.response.send_message(embed=goonbot.embed(title="🚮"), ephemeral=True)
    # Delete selected message
    await message.delete()


@goonbot.tree.context_menu(name="MA (Make Acronym)")
async def make_acronym(interaction: discord.Interaction, message: discord.Message):
    message_content = message.content
    if message.embeds:
        if message.embeds[0].title:
            message_content = message.embeds[0].title
    await interaction.response.send_message(embed=goonbot.embed(title=acronymize(message_content)))


@goonbot.tree.context_menu(name="How long ago")
async def message_age(interaction: discord.Interaction, message: discord.Message):
    created_at_utc = message.created_at
    created_ago = humanize.naturaltime(created_at_utc)
    await interaction.response.send_message(
        embed=goonbot.embed(description=f"This message was created {created_ago}")
    )


@goonbot.tree.context_menu(name="Profile pic")
async def pfp(interaction: discord.Interaction, user: discord.User):
    """
    Get the profile picture of a user

    For whatever reason, you can't really magnify profile pictures in the discord client.
    This supplements as the functionality in the meantime, and lets you download
    """
    assert user.avatar
    await interaction.response.send_message(
        embed=goonbot.embed(title=user.name).set_image(url=user.avatar.url)
    )


@goonbot.tree.context_menu(name="Send love")
async def send_love(interaction: discord.Interaction, user: discord.User):
    """
    Classic goonbot command, used to send an affirmation to a user

    We're an affectionate group, lol.
    """
    permenant_affirmations = [
        "I love you",
        "You are my friend",
        "I like hanging out with you",
    ]
    # Temporary affirmations/affirmations I think will get old eventually
    trendy_affirmations = []
    affirmations = permenant_affirmations + trendy_affirmations
    affirmation = random.choice(affirmations)
    await interaction.response.send_message(
        embed=goonbot.embed(
            title=affirmation,
            description=join_lines(
                [
                    f"From: {interaction.user.mention}",
                    f"To: {user.mention}",
                ]
            ),
        )
    )
