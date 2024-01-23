from typing import Any, Coroutine
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot
from text_processing import join_lines


def fix_link(url: str, use_gallery_view: bool = False) -> str:
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc  # ie. website.tld
    if "x" in netloc:
        fixed_netloc = "fixupx.com"
    elif "twitter" in netloc:
        fixed_netloc = "fxtwitter.com"
    else:
        raise ValueError(f"The passed url is not from x or twitter: ...{parsed_url.netloc}...")
    if use_gallery_view:
        fixed_netloc = "g." + fixed_netloc
    return parsed_url.scheme + "://" + fixed_netloc + parsed_url.path


class Confirm(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=8)
        self.value = None
        self.gallery_view = False

    def on_timeout(self) -> Coroutine[Any, Any, None]:
        self.stop()
        return super().on_timeout()

    @discord.ui.button(label="Replace link", style=discord.ButtonStyle.green)
    async def replace_link_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = True
        self.stop()

    @discord.ui.button(label="Media only", style=discord.ButtonStyle.green)
    async def replace_link_gallery_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = True
        self.gallery_view = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = False
        self.stop()


class TwitterEmbeds(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def embed_twitter_link(self, message: discord.Message):
        # Twitter random decides to enable and disable embedding within apps like discord or telegram
        # At time of writing, it's disabled. So we'll halt this for the time being.
        disabled = True
        if disabled:
            return

        # Do nothing if the message doesn't start with a twitter domain
        if not any([message.content.startswith(f"https://{domain}") for domain in ["twitter", "x"]]):
            return

        confirmation_view = Confirm()
        confirmation_message = await message.reply(
            embed=self.bot.embed(title="Replace this link with a fxTwitter link?").set_footer(
                text="You can just ignore this, it'll clear a few seconds."
            ),
            view=confirmation_view,
        )

        # Wait for response (or timeout)
        await confirmation_view.wait()
        # Clean up confirmation message (it's spammy)
        await confirmation_message.delete()
        # If they chose to replace, delete the original message and send a
        if confirmation_view.value:
            await message.delete()
            await message.channel.send(
                join_lines(
                    [
                        f"**{message.author.mention}** shared",
                        fix_link(message.content, use_gallery_view=confirmation_view.gallery_view),
                    ]
                ),
            )


async def setup(bot):
    await bot.add_cog(TwitterEmbeds(bot))
