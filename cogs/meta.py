import datetime as dt
import logging
import os
import pathlib
import platform
import time

import aiosqlite
import discord
import humanize
from dateutil import tz
from discord import app_commands
from discord.ext import commands, tasks

from goonbot import Goonbot
from text_processing import join_lines

eight_am_cst = dt.time(hour=8, minute=0, second=0, tzinfo=tz.gettz("America/Chicago"))


async def get_cache_file_count() -> int | None:
    """
    The diskcache used for Pulsefire is made up of a series of directories, eaching having a database
    file. This function returns the count of these directories, if any.
    """
    cache_dir_path = pathlib.Path("cache")
    if not cache_dir_path.exists():
        return None
    cache_files = [file for file in cache_dir_path.glob("*") if file.is_dir()]
    return len(cache_files)


async def matches_cached(path: str) -> list[str]:
    """
    The diskcache used for Pulsefire is made up of a series of directories, eaching having a database
    file. This function takes the path to one of these database files and returns a list rows, each
    row being a cached league match.
    """
    async with aiosqlite.connect(path) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT key FROM Cache")
            keys = await cur.fetchall()
            keys = [key for key in keys if "match/v5/matches" in key[0]]
    return [key[0] for key in keys]


async def total_league_matches_cached(cache_file_count: int) -> int:
    """
    In congution with the `matches_cached` function, this function takes the count of cache files
    (provided by `get_cache_file_count`) and returns the total number of league matches cached across
    all of them.
    """
    all_links = []
    for n in range(cache_file_count):
        # The database file path format "cache/001/cache.db"
        path = f"cache/{n:03}/cache.db"
        all_links.extend(await matches_cached(path))

    # At time of writing, the cache doesn't store duplicate entries.
    # In the event the pulsefire author implements some sort of redundancy, let's make sure
    # we're only counting unique matches
    return len(set(all_links))


def uptime_timestamp(input_seconds: int) -> str:
    """Converts seconds to a human readable timestamp"""
    seconds_in_day = 60 * 60 * 24
    days, remaining_seconds = divmod(input_seconds, seconds_in_day)
    hours, minutes = divmod(remaining_seconds, 3600)
    minutes, seconds = divmod(minutes, 60)
    output = f"{hours:02}:{minutes:02}:{seconds:02}"
    if not days:
        return output
    return f"{days} {'day' if days == 1 else 'days'},\n" + output


def get_host_info() -> dict[str, str]:
    info = {}
    # info["Name"] = platform.node() # this just says "raspberry"
    info["OS"] = f"{platform.system()} {platform.release()}"
    issue_file = pathlib.Path("/etc/issue")
    if issue_file.exists():
        issue_file_text = issue_file.read_text()
        info["OS"] = issue_file_text[: -issue_file_text.find("Linux")]
    return info


class Meta(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot
        self.db_size_check.start()

        # Get precise timestamp for uptime
        self.startup_time = time.perf_counter()

    async def cog_load(self):
        await self.ensure_command_usage_legacy_table()

    def count_app_commands(self) -> int:
        """Returns how many app (or "slash") commands are registered in all of the cogs"""
        command_count = 0
        for _, cog in self.bot.cogs.items():
            command_count += len(cog.get_app_commands())
        return command_count

    async def ensure_command_usage_legacy_table(self):
        async with aiosqlite.connect(self.bot.database_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS command_usage_legacy (
                    id INTEGER PRIMARY KEY,
                    count INTEGER
                )
                """
            )

            # Create the single row, with id 1, value of 0
            # Existing row error ignored
            await db.execute(
                """
                INSERT OR IGNORE INTO command_usage_legacy (id, count) 
                VALUES (1, 0)
                """
            )
            await db.commit()

    async def get_count(self):
        async with aiosqlite.connect(self.bot.database_path) as db:
            async with db.execute("SELECT count FROM command_usage_legacy WHERE id = 1") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def increment_count(self):
        async with aiosqlite.connect(self.bot.database_path) as db:
            await db.execute("UPDATE command_usage_legacy SET count = count + 1 WHERE id = 1")
            await db.commit()

    @commands.Cog.listener("on_app_command_completion")
    async def counter_ticker(self, interaction: discord.Interaction, command: app_commands.Command):
        """Increments the processed commands tally each time a command is successfully used"""
        # Ignore dev guild
        if interaction.guild:
            if interaction.guild == self.bot.BOTTING_TOGETHER:
                return

        # Inc commands processed file
        await self.increment_count()

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
        amount = await self.get_count()
        meta_embed.add_field(name="Served", value=f"{amount:,}")

        # Bot uptime
        now = time.perf_counter()
        uptime = round(now - self.startup_time)
        meta_embed.add_field(name="Uptime", value=uptime_timestamp(uptime))

        # Latency
        meta_embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000, 2)}ms")

        # League matches cached
        if cache_file_count := await get_cache_file_count():
            matches_cached_count = await total_league_matches_cached(cache_file_count)
            meta_embed.add_field(
                name="League Games\nCached",
                value=matches_cached_count,
            )

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

    @tasks.loop(time=eight_am_cst)
    async def db_size_check(self):
        """Log database size, message josh if database exceeds limit"""
        assert self.bot.owner_id
        owner = self.bot.get_user(self.bot.owner_id)
        assert owner

        # Size limit
        gigabyte_in_bytes = 1_000_000_000
        size_limit = 10 * gigabyte_in_bytes

        # Get database size
        db_size = os.path.getsize(self.bot.database_path)

        # Log size
        logging.info(f"DB size: {humanize.naturalsize(db_size)}")

        # Notify owner if database exceeds size limit
        if db_size > size_limit:
            await owner.send(f"Database size exceeds {size_limit}GB")


async def setup(bot):
    await bot.add_cog(Meta(bot))
