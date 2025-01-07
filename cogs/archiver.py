import datetime as dt
import uuid

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot
from text_processing import join_lines

type DiscordID = int
type ReactionStr = str
type CommandName = str


class CommandUsage(commands.Cog):
    """
    Listeners used for tracking stats for an eventual "Goonbot Wrapped"
    """

    def __init__(self, bot: Goonbot):
        self.bot = bot
        self.db_path = "gbdb.sqlite"
        self.bot.loop.create_task(self.ensure_database())

    async def ensure_database(self):
        """Ensure database and tables exist"""

        async with aiosqlite.connect(self.db_path) as db:
            # command table
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

            # reaction table
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

            # message message
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
        # Only track Goon HQ
        if interaction.guild != self.bot.GOON_HQ:
            return

        timestamp = dt.datetime.now().isoformat()

        # Insert into database
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
            INSERT INTO command (id, userID, commandName, timestamp) 
            VALUES (?, ?, ?, ?)
            """,
                (str(uuid.uuid4()), interaction.user.id, command.name, timestamp),
            )
            await db.commit()

    @commands.Cog.listener("on_raw_reaction_add")
    async def reaction_used(self, payload: discord.RawReactionActionEvent):
        # Note: Opted to include bot reactions, maybe "who got chatted the most" in wrapped
        # Only track Goon HQ
        if payload.guild_id != self.bot.GOON_HQ.id:
            return

        timestamp = dt.datetime.now().isoformat()

        # Resolve reaction the literal emoji character (which is just a string) or
        # the name of the custom reaction
        reaction_str = payload.emoji if isinstance(payload.emoji, str) else payload.emoji.name

        # Insert into database
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
            INSERT INTO reaction (id, userID, reactionStr, messageID, timestamp) 
            VALUES (?, ?, ?, ?, ?)
            """,
                (str(uuid.uuid4()), payload.user_id, reaction_str, payload.message_id, timestamp),
            )
            await db.commit()

    @commands.Cog.listener("on_message")
    async def message_sent(self, message: discord.Message):
        # Only track Goon HQ & ignore bot messages
        if message.guild != self.bot.GOON_HQ or message.author == self.bot:
            return

        timestamp = dt.datetime.now().isoformat()

        # Insert into database
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
            INSERT INTO message (id, userID, messageID, channelID, timestamp) 
            VALUES (?, ?, ?, ?, ?)
            """,
                (str(uuid.uuid4()), message.author.id, message.id, message.channel.id, timestamp),
            )
            await db.commit()

    # TODO: archive this in some way, im sure it'll be good for later
    # TODO: This should just be total reactions and messages
    @app_commands.command(name="archiver", description="Get Goon HQ stats from this year!")
    async def archiver(self, interaction: discord.Interaction):

        async with aiosqlite.connect(self.db_path) as db:

            # Get command stats for the current year
            async with db.execute(
                """
            SELECT COUNT(*) as count
            FROM command
            WHERE strftime('%Y', timestamp) = strftime('%Y', 'now')
            GROUP BY commandName
            ORDER BY count DESC
            """
            ) as cursor:
                command_stats: list[tuple[CommandName, int]] = [
                    (row[0], row[1]) for row in await cursor.fetchall()
                ]

            # Get reaction stats
            async with db.execute(
                """
            SELECT reactionStr, COUNT(*) as count
            FROM reaction
            WHERE strftime('%Y', timestamp) = strftime('%Y', 'now')
            GROUP BY reactionStr
            ORDER BY count DESC
            """
            ) as cursor:
                reaction_stats: list[tuple[ReactionStr, int]] = [
                    (row[0], row[1]) for row in await cursor.fetchall()
                ]

            # Get message stats
            async with db.execute(
                """
            SELECT userID, COUNT(*) as count
            FROM message
            WHERE strftime('%Y', timestamp) = strftime('%Y', 'now')
            GROUP BY userID
            ORDER BY count DESC
            """
            ) as cursor:
                message_stats: list[tuple[DiscordID, int]] = [
                    (row[0], row[1]) for row in await cursor.fetchall()
                ]

        # Create the embed
        current_year = dt.datetime.now().year
        archiver_embed = self.bot.embed(title=f"{current_year} so far!")
        archiver_embed.set_footer(text=f"In-depth stats will be included for Goonbot {current_year} Wrapped")

        # Add command stats
        archiver_embed.add_field(
            name="Top Commands",
            value=join_lines([f"`/{command_name}`: {count}" for command_name, count in command_stats[:5]]),
        )

        # Add reaction stats
        archiver_embed.add_field(
            name="Top Reactions",
            value=join_lines([f"{reaction_str} {count}x" for reaction_str, count in reaction_stats[:5]]),
        )

        # Add message stats
        # Map user IDs to discord users, ensure they still exist, and add to a new list of only existing users
        message_stats_mapped_users: list[tuple[discord.User, int]] = []
        for discord_id, message_count in message_stats:
            discord_user = self.bot.get_user(discord_id)
            if discord_user:
                message_stats_mapped_users.append((discord_user, message_count))

        archiver_embed.add_field(
            name="Top Yappers",
            value=join_lines([f"{user.mention}: {count}" for user, count in message_stats_mapped_users[:3]]),
        )

        # Send it
        await interaction.response.send_message(embed=archiver_embed)


async def setup(bot):
    await bot.add_cog(CommandUsage(bot))
