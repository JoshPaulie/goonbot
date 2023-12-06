import pathlib

import discord
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot

docs_dir = pathlib.Path("docs")
docs_pages = sorted([p for p in docs_dir.glob("*.md") if "readme" not in p.name.lower()])


class About(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="about", description="Read a page from the goonbot documentation")
    @app_commands.describe(
        page="Pick a page from the documentation to read",
        broadcast="Post this page to the chat?",
    )
    @app_commands.choices(
        page=[
            app_commands.Choice(
                name=page.name[:-3].title().replace("-", " "),
                value=page.as_posix(),
            )
            for page in docs_pages
        ]
    )
    async def about(
        self, interaction: discord.Interaction, page: app_commands.Choice[str], broadcast: bool = False
    ):
        """Read a page from the goonbot documentation!"""
        docs_page = pathlib.Path(page.value)
        docs_page_text = docs_page.read_text()
        if not docs_page_text:
            return await interaction.response.send_message(
                embed=self.bot.embed(
                    title=f"{docs_page.name} is unavailable",
                    description=f"Check back later.",
                    color=discord.Color.greyple(),
                ),
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=self.bot.embed(description=docs_page_text),
            ephemeral=not broadcast,
        )


async def setup(bot):
    await bot.add_cog(About(bot))
