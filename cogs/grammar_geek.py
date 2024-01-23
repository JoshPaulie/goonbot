import datetime as dt
import random

import discord
from discord.ext import commands

from cogs._grammar_geek.youre import wrong_youre
from goonbot import Goonbot

from ._grammar_geek.generic import trim_punctuation
from ._grammar_geek.misspell import flattened_dict


class GrammarGeek(commands.Cog):
    spell_check_limiter = []

    def __init__(self, bot: Goonbot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def grammar_police(self, message: discord.Message):
        if wrong_youre(message.content):
            await message.reply("you're*", mention_author=False)

    @commands.Cog.listener("on_message")
    async def spellchecker(self, message: discord.Message):
        today = dt.datetime.today()

        # Ignore bot messages
        if message.author == self.bot.user:
            return

        # Limits this interaction to once a day
        if today in self.spell_check_limiter:
            return

        ded = "https://i.imgur.com/gXu9UO0.jpg"
        uh_oh = "https://i.imgur.com/lKSH7f7.jpg"
        random_image = random.choice([ded, uh_oh])
        random_emoji = random.choice(["💀", "🤣"])

        for word in map(trim_punctuation, message.content.split()):
            if word in flattened_dict.keys():
                await message.reply(
                    embed=self.bot.embed(title=f">{word} {random_emoji}").set_image(
                        url=random.choice(random_image)
                    )
                )
                return


async def setup(bot):
    await bot.add_cog(GrammarGeek(bot))
