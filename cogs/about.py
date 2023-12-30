import pathlib

import discord
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot
from text_processing import join_lines

docs_dir = pathlib.Path("docs")
docs_pages = sorted([p for p in docs_dir.glob("*.md") if "readme" not in p.name.lower()])


def _clean_header(header: str):
    header = header.replace("**", "")
    if header.startswith("# "):
        return header[2:]
    if header.startswith("## "):
        return header[3:]
    return header


def make_sections(text: str) -> list[list[str]]:
    lines = text.splitlines()

    sections = []
    current_section = []
    for line in lines:
        page_break = "---"
        if line != page_break:
            current_section.append(line)
            continue

        sections.append(current_section)
        current_section = []

    # make sure we append last section
    sections.append(current_section)
    return sections


type SectionDict = dict[str, list[str]]


def create_section_dict(sections: list[list[str]]) -> SectionDict:
    """Takes list of sections, creates a dict with each key being the first line of section (cleaned up a bit) and the value being section lines"""
    return {_clean_header(section[0]): section for section in sections}


class SectionDropdownPicker(discord.ui.Select):
    def __init__(self, sections: SectionDict, broadcast: bool):
        self.sections = sections
        self.broadcast = broadcast
        options = [discord.SelectOption(label=section) for section in self.sections.keys()]
        super().__init__(placeholder="Pick a section", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=join_lines(self.sections[self.values[0]]),
                color=discord.Color.blurple(),
            ),
            # Remove view if broadcasted
            view=None if self.broadcast else self.view,
        )


class PickSectionView(discord.ui.View):
    def __init__(self, sections: SectionDict, broadcast: bool):
        super().__init__()
        self.add_item(SectionDropdownPicker(sections=sections, broadcast=broadcast))


class About(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="about", description="Read a page from the goonbot documentation")
    @app_commands.describe(
        page="Pick a page from the documentation to read",
        broadcast="Select 'True' to post your result in chat. Select 'False' to see the page without posting it in chat",
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
        self,
        interaction: discord.Interaction,
        page: app_commands.Choice[str],
        broadcast: bool = False,
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

        sections = make_sections(docs_page_text)
        first_section = sections[0]
        if len(sections) > 1:
            section_dict = create_section_dict(sections)
            dropdown_view = PickSectionView(sections=section_dict, broadcast=broadcast)
            await interaction.response.send_message(
                embed=self.bot.embed(description=join_lines(first_section)),
                view=dropdown_view,
                ephemeral=not broadcast,
            )
        else:
            await interaction.response.send_message(
                embed=self.bot.embed(description=join_lines(first_section)),
                ephemeral=not broadcast,
            )


async def setup(bot):
    await bot.add_cog(About(bot))
