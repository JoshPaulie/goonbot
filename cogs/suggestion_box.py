import datetime as dt
import time

import aiosqlite
import discord
import humanize
from dateutil import tz
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot


class SuggestionModal(discord.ui.Modal, title="Suggestion"):
    details = discord.ui.TextInput(label="Suggestion details", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        # Parse user suggestion
        details = self.details.value

        # Get timestamp
        timestamp = dt.datetime.now().isoformat()

        # Make entry in database
        async with aiosqlite.connect(Goonbot.database_path) as db:
            await db.execute(
                """
                INSERT INTO suggestion (id, userID, details, devNotes, timestamp) 
                VALUES (?, ?, ?, ?, ?)
                """,
                (interaction.id, interaction.user.id, details, None, timestamp),
            )
            await db.commit()

        # Send confirmation
        await interaction.response.send_message(
            embed=Goonbot.embed(
                title=f"Thanks for your suggestion!",
                description="Suggestion has been added to the database and Josh has been notified.",
            ),
            ephemeral=True,
        )


class SuggestionBox(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

        # Get precise timestamp for uptime
        self.startup_time = time.perf_counter()

    async def cog_load(self):
        await self.ensure_suggestion_table()

    async def ensure_suggestion_table(self):
        async with aiosqlite.connect(self.bot.database_path) as db:
            # Ensure "suggestion" table exists
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS suggestion (
                    id INTEGER PRIMARY KEY,
                    userID INTEGER,
                    details TEXT,
                    devNotes TEXT,
                    timestamp TEXT
                )
                """
            )
            # Commit changes
            await db.commit()

    @app_commands.command(name="suggest", description="Suggest a feature or improvement")
    async def suggest(self, interaction: discord.Interaction):
        suggestion_modal = SuggestionModal()
        await interaction.response.send_modal(suggestion_modal)
        await suggestion_modal.wait()

        # Alert owner of new suggestion
        assert self.bot.owner_id
        owner = self.bot.get_user(self.bot.owner_id)
        assert owner
        await owner.send(
            embed=self.bot.embed(
                title=f"{interaction.user.name} suggests:",
                description=suggestion_modal.details.value,
            )
        )


async def setup(bot):
    await bot.add_cog(SuggestionBox(bot))
