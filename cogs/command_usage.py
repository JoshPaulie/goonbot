import sqlite3

import discord
from discord.ext import commands

from goonbot import Goonbot

DATABASE_FILE_NAME = "command_usage.db"


def ensure_command_used_db():
    """Makes sure the database (and table) are present both when it starts, and when related commands are called"""
    # Connect to the database or create it if it doesn't exist
    conn = sqlite3.connect(DATABASE_FILE_NAME)
    cursor = conn.cursor()

    # Create the table if it doesn't exist
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS command_usage (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            command_name TEXT,
            usage_count INTEGER
        )
        """
    )


def track_command_usage(
    user_id,
    command_name,
):
    ensure_command_used_db()
    # Connect to the database or create it if it doesn't exist
    conn = sqlite3.connect(DATABASE_FILE_NAME)
    cursor = conn.cursor()

    # Check if the user and command exist in the table
    cursor.execute("SELECT * FROM command_usage WHERE user_id=? AND command_name=?", (user_id, command_name))
    existing_record = cursor.fetchone()

    if existing_record:
        # If the record exists, update the usage count
        cursor.execute(
            "UPDATE command_usage SET usage_count = usage_count + 1 WHERE id=?", (existing_record[0],)
        )
    else:
        # If the record doesn't exist, insert a new record
        cursor.execute(
            "INSERT INTO command_usage (user_id, command_name, usage_count) VALUES (?, ?, 1)",
            (user_id, command_name),
        )

    # Commit changes and close the connection
    conn.commit()
    conn.close()


def get_usage_statistics(
    user_id: None | int = None, command_name: None | str = None
) -> list[tuple[str, int, str, int]]:
    """
    Returns a list of records. By default, it returns every record.
    It can also optionally just return records for a specific command or users

    # Possible usage

    for record in get_usage_statistics():
        _, discord_id, commnad_name, count = record
        discord_user = self.bot.get_user(int(discord_id))

        print(discord_user.name if discord_user else "Unknown", commnad_name, count)
    """
    ensure_command_used_db()
    conn = sqlite3.connect(DATABASE_FILE_NAME)
    cursor = conn.cursor()

    if user_id:
        cursor.execute("SELECT * FROM command_usage WHERE user_id=?", (user_id,))
    elif command_name:
        cursor.execute("SELECT * FROM command_usage WHERE command_name=?", (command_name,))
    else:
        cursor.execute("SELECT * FROM command_usage")

    usage_statistics: list[tuple[str, int, str, int]] = cursor.fetchall()

    conn.close()
    return usage_statistics


class CommandUsage(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot
        ensure_command_used_db()

    @commands.Cog.listener("on_app_command_completion")
    async def app_command_used(self, interaction: discord.Interaction, command: discord.app_commands.Command):
        track_command_usage(interaction.user.id, command.name)


async def setup(bot):
    await bot.add_cog(CommandUsage(bot))
