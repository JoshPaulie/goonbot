from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot


def fix_link(url: str) -> str:
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc  # ie. website.tld
    if "x" in netloc:
        fixed_netloc = "fixupx.com"
    elif "twitter" in netloc:
        fixed_netloc = "fxtwitter.com"
    else:
        raise ValueError(f"The passed url is not from x or twitter: ...{parsed_url.netloc}...")
    return parsed_url.scheme + "://" + fixed_netloc + parsed_url.path


class TwitterEmbeds(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def embed_twitter_link(self, message: discord.Message):
        # make sure the message is from twitter
        if not any(
            (
                message.content.startswith(f"https://twitter"),
                message.content.startswith(f"https://x"),
            )
        ):
            return
        await message.reply(fix_link(message.content), silent=True)


async def setup(bot):
    await bot.add_cog(TwitterEmbeds(bot))
