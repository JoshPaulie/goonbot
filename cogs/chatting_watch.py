import random
from typing import Any, Sequence

import discord
from discord.ext import commands

from goonbot import Goonbot

ECTOPLAX_ID = 104488848309895168


def sequence_same_value(seq: Sequence[Any]):
    """Makes sure all the values in a sequence in the same.

    Examples
        - sequence_same_value([1, 1, 1]) == True
        - sequence_same_value([1, 2, 1]) == False
    """
    head, *body = seq
    for item in body:
        if item != head:
            return False
    return True


class ChattingWatch(commands.Cog):
    channels: dict[int, list[int]] = {}

    def __init__(self, bot: Goonbot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def chatting_listener(self, message: discord.Message):
        """This listener is responsible for adding a random reaction to a message, if the message author has typed consecutive 5 messages without getting interuptted"""
        # If we're in DM, ignore
        if not message.guild:
            return

        # Get message details
        channel_id = message.channel.id
        author_id = message.author.id

        # Ignore messages sent in the testing guild, or sent by the bot
        assert self.bot.user
        if message.guild == self.bot.BOTTING_TOGETHER or message.author.id == self.bot.user.id:
            return

        # This user is commonly in VC but needs to be muted, and uses text to communicate.
        # We'll except him from this "feature" when he's in voice channel
        for channel in message.guild.voice_channels:
            for user in channel.members:
                if user.id == ECTOPLAX_ID:
                    return

        # Make sure the channel is in the dict
        if not self.channels.get(channel_id):
            self.channels[channel_id] = []

        # Add whoever posted a message to the channel queue
        self.channels[channel_id].append(author_id)
        channel_past_chatters = self.channels[channel_id]

        # If someone else sends a message that wasn't the previous chatter, clear the streak
        if not sequence_same_value(channel_past_chatters):
            self.channels[channel_id] = []
            return

        # If the same chatter has posted 5 times without being interrupted, send the reaction
        if len(channel_past_chatters) == 5:
            await message.add_reaction(
                random.choice(
                    [
                        "<a:chatting:1196923520442191923>",
                        "💀",
                        "<:clueless:934933705611444234>",
                    ]
                )
            )
            self.channels[channel_id] = []


async def setup(bot):
    await bot.add_cog(ChattingWatch(bot))
