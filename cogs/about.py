import pathlib

import discord
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot

# This should be outside docs_pages_autocomplete(). With how autocomplete works,
# if this was within the function, the pathlib lookup would occur everytime a user
# entered a new character. This has the slight disadvantage needing to restart the bot
# when a new page is added.
docs_dir = pathlib.Path("docs")
docs_pages = sorted([p for p in docs_dir.glob("*.md") if "readme" not in p.name.lower()])


async def doc_pages_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(
            # Cleans up file names for the end user
            # goon_calendar.md -> Goon Calendar
            name=page.name[:-3].title().replace("-", " "),
            value=page.as_posix(),
        )
        for page in docs_pages
        if current.lower() in page.name[:-3].lower().replace("-", " ")
    ]


class About(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="about")
    @app_commands.autocomplete(page=doc_pages_autocomplete)
    async def about(self, interaction: discord.Interaction, page: str, broadcast: bool = False):
        """Read a page from the goonbot documentation!"""
        docs_page = pathlib.Path(page)
        await interaction.response.send_message(
            embed=self.bot.embed(description=docs_page.read_text()),
            ephemeral=not broadcast,
        )


async def setup(bot):
    await bot.add_cog(About(bot))
