from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot


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


class TwitterEmbeds(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot
        self.fix_tweet_ctx_menu = app_commands.ContextMenu(
            name="Embed Tweet",
            callback=self.embed_tweet,
        )
        self.bot.tree.add_command(self.fix_tweet_ctx_menu)

    async def embed_tweet(self, interaction: discord.Interaction, message: discord.Message) -> None:
        link = message.content

        # Do nothing if the message doesn't start with a twitter domain
        if not any([link.startswith(f"https://{domain}") for domain in ["twitter", "x"]]):
            return await interaction.response.send_message(
                embed=discord.Embed(description="This is not a tweet. 😴", color=discord.Color.greyple()),
                ephemeral=True,
            )

        await interaction.response.send_message(fix_link(link))

    @commands.Cog.listener("on_message")
    async def auto_embed_media_tweets(self, message: discord.Message):
        """
        Automatically reply to tweet with media, with an embedded version mirrored through FixTweet
        You can watch FixTweet videos in discord

        Currently only covers
        - Tweets that aren't replies
        - Tweets that contain a video
        """
        link = message.content
        # Do nothing if the message doesn't start with a twitter domain
        if not any([link.startswith(f"https://{domain}") for domain in ["twitter", "x"]]):
            return

        # Only embed if it's a video link
        if not link.endswith("?s=20"):
            return

        await message.reply(fix_link(link, use_gallery_view=True))


async def setup(bot):
    await bot.add_cog(TwitterEmbeds(bot))
