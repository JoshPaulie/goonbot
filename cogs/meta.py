import asyncio
import logging
import pathlib
import platform
import sqlite3
import time

import discord
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot
from text_processing import join_lines

COMMANDS_PROCESSED_FILE_NAME = "commands-processed.txt"


def get_cache_file_count() -> int | None:
    cache_dir_path = pathlib.Path("cache")
    if not cache_dir_path.exists():
        return None
    cache_files = [file for file in cache_dir_path.glob("*") if file.is_dir()]
    return len(cache_files)


def matches_cached(path: str) -> list[str]:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT key FROM Cache")
    keys = cur.fetchall()
    keys = [key for key in keys if "match/v5/matches" in key[0]]
    conn.close()
    return keys


def total_matches_cached(cache_file_count: int) -> int:
    all_links = []
    for n in range(cache_file_count):
        all_links.extend(matches_cached(f"cache/{n:03}/cache.db"))
    # At time of writing, the cache doesn't store duplicate entries.
    # In the event the pulsefire author implements some sort of redundancy, let's make sure
    # we're only counting unique matches
    return len(set(all_links))


def timestamp(seconds: int) -> str:
    hours, minutes = divmod(seconds, 3600)
    minutes, remaining_seconds = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{remaining_seconds:02}"


def get_host_info() -> dict[str, str]:
    info = {}
    # info["Name"] = platform.node()
    info["OS"] = f"{platform.system()} {platform.release()}"
    info["Processor"] = platform.processor()
    # info["Architecture"] = platform.machine()
    return info


def create_processed_file():
    """Create the file that tallies how many commands have been processed, if it doesn't exist"""
    file = pathlib.Path(COMMANDS_PROCESSED_FILE_NAME)
    if not file.exists():
        logging.info(f"{COMMANDS_PROCESSED_FILE_NAME} not found...")
        with open(COMMANDS_PROCESSED_FILE_NAME, mode="w") as new_file:
            new_file.write("0")
    logging.info(f"Created {COMMANDS_PROCESSED_FILE_NAME}")


def get_commands_processed_value():
    create_processed_file()
    with open(COMMANDS_PROCESSED_FILE_NAME, mode="r") as file:
        counter_value = file.read()
        return int(counter_value)


def inc_processed_file(amount: int = 1):
    create_processed_file()
    with open(COMMANDS_PROCESSED_FILE_NAME, mode="r") as file:
        counter_value = file.read()
    counter_value = int(counter_value)
    new_value = counter_value + amount
    with open(COMMANDS_PROCESSED_FILE_NAME, mode="w") as file:
        file.write(str(new_value))


class Meta(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot
        self.startup_time = time.perf_counter()
        self.counter_file_lock = asyncio.Lock()

    def count_app_commands(self) -> int:
        command_count = 0
        for _, cog in self.bot.cogs.items():
            command_count += len(cog.get_app_commands())
        return command_count

    @commands.Cog.listener("on_app_command_completion")
    async def counter_ticker(self, interaction: discord.Interaction, command: app_commands.Command):
        # Don't add another tally if in dev channel
        dev_guild_id = 510865274594131968
        assert interaction.guild
        if interaction.guild.id == dev_guild_id:
            return
        async with self.counter_file_lock:
            inc_processed_file()

    @app_commands.command(name="meta")
    async def meta(self, interaction: discord.Interaction):
        """Fun meta stats pertaining to the bot itself"""
        meta_embed = self.bot.embed(title="Goonbot")
        meta_embed.description = (
            "**"
            + ", ".join(
                [
                    "[Project Repo](https://github.com/JoshPaulie/goonbot/)",
                    "[Changelog](https://github.com/JoshPaulie/goonbot/blob/main/changelog.md)",
                ]
            )
            + "**"
        )

        # Bot version
        meta_embed.add_field(name="Version", value=".".join(map(str, self.bot.VERSION)))

        # Total commands
        meta_embed.add_field(name="Commands", value=self.count_app_commands())

        # Commands served
        amount = get_commands_processed_value()
        meta_embed.add_field(name="Served", value=f"{amount:,}")

        # Bot uptime
        now = time.perf_counter()
        uptime = round(now - self.startup_time)
        meta_embed.add_field(name="Uptime", value=timestamp(uptime))

        # Latency
        meta_embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000, 2)}ms")

        # League matches cached
        if cache_file_count := get_cache_file_count():
            meta_embed.add_field(name="League Games\nCached", value=total_matches_cached(cache_file_count))

        # Host info
        meta_embed.add_field(
            name="Hosted on Raspberry Pi <:rpi:1194061870831763486>",
            value=join_lines(
                ["[Model 4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)"]
                + [f"**{name}** {value}" for name, value in get_host_info().items()]
            ),
            inline=False,
        )

        # "Help"
        meta_embed.add_field(
            name="Need help?",
            value="Explore the new `/about` command",
            inline=False,
        )

        assert self.bot.user
        if self.bot.user.avatar:
            meta_embed.set_thumbnail(url=self.bot.user.avatar.url)

        await interaction.response.send_message(embed=meta_embed)

    # todo suggestion


async def setup(bot):
    await bot.add_cog(Meta(bot))
