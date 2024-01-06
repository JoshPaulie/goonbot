import pathlib

import discord
from discord import app_commands
from discord.ext import commands

from bex_tools import CycleRandom
from goonbot import Goonbot


class Pics(commands.Cog):
    # > Why not have a generator here? it'd be much more memory efficient
    # Because users can add new images on the fly, I want them to be able to add images directly into the live queue of images
    # without disrupting the cycle by starting over
    rat_links = CycleRandom(pathlib.Path("image_links/rats.txt").read_text().splitlines())
    cat_links = CycleRandom(pathlib.Path("image_links/cats.txt").read_text().splitlines())
    paranormal_links = CycleRandom(pathlib.Path("image_links/real.txt").read_text().splitlines())

    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="addpic", description="Add a new image link to car, rat, or real")
    @app_commands.describe(link="Add the image/gif link here")
    @app_commands.describe(categories="Specify which category your link should be added to")
    @app_commands.choices(
        categories=[
            app_commands.Choice(name="Rat", value="rats"),
            app_commands.Choice(name="Cat", value="cats"),
            app_commands.Choice(name="Real", value="real"),
        ]
    )
    async def add_pic(
        self, interaction: discord.Interaction, link: str, categories: app_commands.Choice[str]
    ):
        file_path = "image_links/"
        match categories.value:
            case "rats":
                file_path += f"{categories.value}.txt"
                self.rat_links.items.append(link)
            case "cats":
                file_path += f"{categories.value}.txt"
                self.cat_links.items.append(link)
            case "real":
                file_path += f"{categories.value}.txt"
                self.paranormal_links.items.append(link)

        with open(file_path, mode="a") as file:
            file.write(f"\n{link}")

        await interaction.response.send_message(
            embed=self.bot.embed(
                title="Thanks for your addition!",
                description=f"Your link has been added to **{categories.value}**",
            )
        )

    @app_commands.command(name="rat", description="Roll a rat 🐀")
    async def rat(self, interaction: discord.Interaction):
        """A goonbot classic, the /rat command sends a random image of a rat from a list, hand curated by community member Ectoplax"""
        next_rat = next(self.rat_links)
        await interaction.response.send_message(next_rat)

    @app_commands.command(name="cat", description=":3")
    async def cat(self, interaction: discord.Interaction):
        next_cat = next(self.cat_links)
        await interaction.response.send_message(next_cat)

    @app_commands.command(name="real", description="Sends a random paranormal video. Is it real?")
    async def real(self, interaction: discord.Interaction):
        next_paranormal_photo = next(self.paranormal_links)
        await interaction.response.send_message(next_paranormal_photo)
        message = await interaction.original_response()
        await message.add_reaction("✅")
        await message.add_reaction("❌")

    @app_commands.command(name="huh", description="?")
    async def huh(self, interaction: discord.Interaction):
        stoner_cat_gif = "https://media.tenor.com/YYw8_Cvr-wQAAAAd/stoned-cat.gif"
        await interaction.response.send_message(stoner_cat_gif)

    @app_commands.command(name="peepotlak", description=":O")
    async def chatting(self, interaction: discord.Interaction):
        chatting = "https://c.tenor.com/pVgjcy0GDoAAAAAC/tenor.gif"
        await interaction.response.send_message(chatting)


async def setup(bot):
    await bot.add_cog(Pics(bot))
