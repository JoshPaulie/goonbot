from typing import Any, Sequence

import discord
from discord.ext import commands

from goonbot import Goonbot


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
        """This listener is responsible for adding a particular reaction to a message, if the message author has typed consecutive 5 messages"""
        # Get message details
        channel_id = message.channel.id
        author_id = message.author.id

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
            await message.add_reaction("<a:chatting:1196923520442191923>")
            self.channels[channel_id] = []


async def setup(bot):
    await bot.add_cog(ChattingWatch(bot))
