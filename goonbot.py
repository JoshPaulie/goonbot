import logging
import random
import traceback
from functools import partial
from pathlib import Path
from typing import Iterator

import discord
from discord.ext import commands

from keys import Keys

# The main server
GOON_HQ = discord.Object(177125557954281472)
# The testing server
BOTTING_TOGETHER = discord.Object(510865274594131968)


class Goonbot(commands.Bot):
    keys = Keys

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

    @staticmethod
    def get_cogs() -> Iterator[str]:
        """
        Yields files names from cogs/ folders, formatted so discord.py can load them into the bot as extensions.

        Example
            cogs/general.py -> cogs.general
        """
        files = Path("cogs").rglob("*.py")
        for file in files:
            if not any(x in file.name for x in ["__init__", "template_cog"]):
                yield file.as_posix()[:-3].replace("/", ".")

    async def load_cogs(self) -> None:
        """Loads all of the files from cogs/ into the bot as extensions"""
        for cog in self.get_cogs():
            try:
                await self.load_extension(cog)
                logging.info(f"Loaded cog: {cog}!")
            except Exception as exc:
                logging.warning(f"Could not load extension {cog} due to {exc.__class__.__name__}: {exc}")
                print(f"{cog} failed to load: {exc.__class__.__name__}")

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


# Prefix commands
# Prefix commands are old school bot commands from years back. This bot uses "." as its prefix
# Nowadays, most commands are app_commands (aka /slash commands) and auto complete after you type "/"
# Prefix commands aren't listed in the app_command menu in discord, and were originally argrigated in the "help command"
# You'll notice the help command is disabled in the bot definition, as it's set to None. If it was enabled, users could see
# all of the prefix commands by typing ".help"


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
    await ctx.send(
        embed=goonbot.embed(title=f"{goonbot.user.name} commands synced to {ctx.guild.name}"),
        ephemeral=True,
    )
    await ctx.message.add_reaction("✅")


@goonbot.command(name="img")
@commands.is_owner()
async def test_image(ctx: commands.Context, image_url: str | None = None):
    """Test how images are displayed in an embed, mostly used for checking broken rats"""
    if not image_url:
        return await ctx.send(
            embed=goonbot.embed(title="You didn't include an image", color=discord.Color.red()),
            ephemeral=True,
        )

    try:
        await ctx.send(embed=goonbot.embed(title="Test image").set_image(url=image_url))
    except Exception as e:
        await ctx.send(
            embed=goonbot.embed(
                title="Something catastrophic happened",
                description=e.with_traceback,
                color=discord.Color.red(),
            )
        )


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
        traceback.print_exc()


# Context menus
# Context menus are most easily defined here, directly in the goonbot instance file
# Defining most of the general contexts menus here would make since
# but not for cog specific commands like cog/rats.report_rap.

# To make these "cog specific" context menu commands, read the following
# (written by the author of discord.py)
# https://github.com/Rapptz/discord.py/issues/7823#issuecomment-1086830458

# "What are context menus?"
# They're commands that you can bind to particular "contexts," namley messages or users.
# This enables you to right click either a message or a user, go to Apps,
# and a list will display with the available commands for that particular "context"


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
    trendy_affirmations = [
        "Stick out that gyatt",
        "You're so skibidi",
        "You're so fanum tax",
    ]
    affirmations = permenant_affirmations + trendy_affirmations
    affirmation = random.choice(affirmations)
    assert user
    await interaction.response.send_message(
        embed=goonbot.embed(
            title=affirmation,
        )
    )
