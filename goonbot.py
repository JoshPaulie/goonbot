import asyncio
import logging
import pathlib
import random
import time
import traceback
from collections import defaultdict
from functools import partial
from pathlib import Path
from typing import Iterator

import discord
from discord.ext import commands

from keys import Keys
from text_processing import acronymize, join_lines

GOON_HQ = discord.Object(177125557954281472)  # The main ("production") server
BOTTING_TOGETHER = discord.Object(510865274594131968)  # The development server


class Goonbot(commands.Bot):
    keys = Keys
    timer_lock = asyncio.Lock()
    command_timer = defaultdict(time.perf_counter)

    # A default embed that will sprinkled around (so I don't have to manually set the color every time)
    embed = partial(discord.Embed, color=discord.Color.blurple())

    def __init__(self, intents: discord.Intents, **kwargs):
        super().__init__(
            command_prefix=commands.when_mentioned_or("."),
            help_command=None,
            intents=intents,
            **kwargs,
        )
        self.owner_id = 177131156028784640  # bexli boy

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
        Handles startup actions like call load_cogs(), and copy all the commands to
        both servers, allowing for new features and changes to be used immediately

        > "What's the difference between 'syncing' and 'copying' commands to a server?"
        I'm not super sure at this time. Copy seems to be a primer for sync in some way.
        What I do know for sure is that copying can be done added to the startup_hook(),
        while syncing shouldn't. (Citation needed)
        """
        await self.load_cogs()
        guilds = [
            # Goon HQ will be uncommented once the bot is ready for "production"
            # GOON_HQ,
            BOTTING_TOGETHER,
        ]
        for guild in guilds:
            self.tree.copy_global_to(guild=guild)

    async def on_ready(self):
        """Called after the bot is finished logging in and is ready to use"""
        assert self.user
        logging.info(f"Logged on as {self.user} (ID: {self.user.id})")
        print(f"{self.user.name} is ready")


# Bot instance
goonbot = Goonbot(
    # Gives the bot the ability to read messages, view profiles, etc
    intents=discord.Intents.all(),
)

# Generic last-resort error message to be sent, in hopes of negating all "interaction failed messages"
# (by effectively replacing it with a different error message lol)
# Doesn't catch "unknown interaction" failures
command_tree = goonbot.tree


@command_tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
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


@goonbot.command(name="log")
async def log(ctx: commands.Context, line_count: int = 10):
    log_file = pathlib.Path("bot.log")
    if not log_file.exists():
        return
    log_file_text = log_file.read_text().splitlines()
    log_file_text_slice = log_file_text[-line_count:]
    log_file_text_slice_no_timestamp = [line[22:] for line in log_file_text_slice]
    await ctx.reply(
        embed=goonbot.embed(
            title="Log",
            description=join_lines(
                ["```", "\n".join(log_file_text_slice_no_timestamp), "```"],
            ),
        ),
        ephemeral=True,
    )


@goonbot.command(name="sync", description="[Meta] Syncs commands to server")
@commands.is_owner()
async def sync(ctx: commands.Context):
    """
    This command syncs all of the bot's commands (names & descriptions) to a given server

    It's a newer standard for discord.py bots, and is required to quickly debug and develop new features.
    Without syncing the bot command tree to a server, it can take an hour (or longer) for changes to
    trickle to all the servers the bot is in.

    It might be tempting to add the bot.tree.sync(guild) line in bot.setup_hook().
    However, if you sync your bot commands every time it restarts, especially during the development
    of new features when frequent restarts are necessary, you'll get rate-limited by Discord into next week.
    They really don't like people spamming app command syncs to servers.
    """
    assert ctx.guild
    await goonbot.tree.sync(guild=ctx.guild)
    assert goonbot.user
    await ctx.send(embed=goonbot.embed(title=f"{goonbot.user.name} commands synced to {ctx.guild.name}"))


# This catches and processes ext (or "prefixed") commands
@goonbot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.NotOwner):
        await ctx.reply(
            embed=goonbot.embed(
                title="This is an administrative command, sorry 🤭",
                color=discord.Color.greyple(),
            ),
            ephemeral=True,
        )
        await ctx.message.add_reaction("❌")
    else:
        # Without this line, prefixed commands throwing exceptions that will get gobbled
        # up by this event and make me real mad later when I break something
        logging.error(traceback.format_exc())


@goonbot.event
async def on_interaction(interaction: discord.Interaction):
    async with goonbot.timer_lock:
        if interaction.type == discord.InteractionType.application_command:
            assert interaction.command
            goonbot.command_timer[interaction.id] = time.perf_counter()


@goonbot.event
async def on_app_command_completion(interaction: discord.Interaction, command: discord.app_commands.Command):
    async with goonbot.timer_lock:
        if command_start_time := goonbot.command_timer.get(interaction.id):
            del goonbot.command_timer[interaction.id]
            command_end_time = time.perf_counter()
            command_elapsed_time = command_end_time - command_start_time
            logging.info(f"{command.name} execution time: {command_elapsed_time}")


# Context menus
# Context menus are most easily defined here, directly in the goonbot instance file
# Defining most of the general contexts menus here would make since
# but not for cog specific commands like cog/rats.report_rap.

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
    assert user
    await interaction.response.send_message(
        embed=goonbot.embed(
            title=affirmation,
        )
    )
