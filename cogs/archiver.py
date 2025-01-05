import datetime as dt
import uuid

import aiosqlite
import discord
from discord.ext import commands

from goonbot import Goonbot


class CommandUsage(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot
        self.db_path = "gbdb.sqlite"
        self.bot.loop.create_task(self.ensure_database())

    async def ensure_database(self):
        # Ensure database and tables exist
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
            CREATE TABLE IF NOT EXISTS command (
                id TEXT PRIMARY KEY,
                userID INTEGER,
                commandName TEXT,
                timestamp TEXT
            )
            """
            )
            await db.execute(
                """
            CREATE TABLE IF NOT EXISTS reaction (
                id TEXT PRIMARY KEY,
                userID INTEGER,
                reactionStr TEXT,
                messageID INTEGER,
                timestamp TEXT
            )
            """
            )
            await db.execute(
                """
            CREATE TABLE IF NOT EXISTS message (
                id TEXT PRIMARY KEY,
                userID INTEGER,
                messageID INTEGER,
                channelID INTEGER,
                timestamp TEXT
            )
            """
            )
            await db.commit()

    @commands.Cog.listener("on_app_command_completion")
    async def app_command_used(self, interaction: discord.Interaction, command: discord.app_commands.Command):
        if interaction.guild != self.bot.GOON_HQ:
            return

        now = dt.datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
            INSERT INTO command (id, userID, commandName, timestamp) 
            VALUES (?, ?, ?, ?)
            """,
                (str(uuid.uuid4()), interaction.user.id, command.name, now),
            )
            await db.commit()

    @commands.Cog.listener("on_raw_reaction_add")
    async def reaction_used(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id != self.bot.GOON_HQ.id:
            return

        now = dt.datetime.now().isoformat()
        reaction_str = payload.emoji if isinstance(payload.emoji, str) else payload.emoji.name

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
            INSERT INTO reaction (id, userID, reactionStr, messageID, timestamp) 
            VALUES (?, ?, ?, ?, ?)
            """,
                (str(uuid.uuid4()), payload.user_id, reaction_str, payload.message_id, now),
            )
            await db.commit()

    @commands.Cog.listener("on_message")
    async def message_sent(self, message: discord.Message):
        if message.guild != self.bot.GOON_HQ or message.author == self.bot:
            return

        now = dt.datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
            INSERT INTO message (id, userID, messageID, channelID, timestamp) 
            VALUES (?, ?, ?, ?, ?)
            """,
                (str(uuid.uuid4()), message.author.id, message.id, message.channel.id, now),
            )
            await db.commit()


async def setup(bot):
    await bot.add_cog(CommandUsage(bot))
