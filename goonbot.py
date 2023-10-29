import logging
from functools import partial
from pathlib import Path
from typing import Iterator

import discord
from discord.ext import commands

GOON_HQ = discord.Object(177125557954281472)
BOTTING_TOGETHER = discord.Object(510865274594131968)


class Goonbot(commands.Bot):
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
        for cog in self.get_cogs():
            try:
                await self.load_extension(cog)
                logging.info(f"Loaded cog: {cog}!")
            except Exception as exc:
                logging.warning(f"Could not load extension {cog} due to {exc.__class__.__name__}: {exc}")
                print(f"{cog} failed to load: {exc.__class__.__name__}")

    async def setup_hook(self):
        await self.load_cogs()
        # self.tree.copy_global_to(guild=GOON_HQ)
        self.tree.copy_global_to(guild=BOTTING_TOGETHER)

    async def on_ready(self):
        assert self.user
        logging.info(f"Logged on as {self.user} (ID: {self.user.id})")
        print(f"{self.user.name} is ready")


# Bot instance
goonbot = Goonbot(
    # Gives the bot the ability to read messages, view profiles, etc
    intents=discord.Intents.all(),
)


# Sync command
# - This is a new standard for modern discord.py bots
# - "Why?" Because of those fancy /slash commands discord forced on us
# - Anytime a new app_command is added, this must be manually ran from any server
#   you'd like to use the command (lest you wait up to an hour to start debugging)
# - "Can't you put the sync code in the startup command?" Discord will rate limit
#   you into next week
@goonbot.command(name="sync", description="[Meta] Syncs commands to server")
async def sync(ctx: commands.Context):
    if not await goonbot.is_owner(ctx.author):
        await ctx.reply("Only jarsh needs to use this 😬", ephemeral=True)
        return
    assert ctx.guild
    await goonbot.tree.sync(guild=ctx.guild)
    await ctx.reply(f"Bot commands synced to {ctx.guild.name}", ephemeral=True)
    await ctx.message.delete()
