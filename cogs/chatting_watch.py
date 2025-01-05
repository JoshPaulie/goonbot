import random
from typing import Any, Sequence

import discord
from discord.ext import commands

from goonbot import Goonbot

ECTOPLAX_ID = 104488848309895168


def sequence_same_value(seq: Sequence[Any]):
    """Checks if all values in a sequence are the same.

    Examples:
        - sequence_same_value([1, 1, 1]) == True
        - sequence_same_value([1, 2, 1]) == False
    """
    head, *body = seq
    for item in body:
        if item != head:
            return False
    return True


class ChattingWatch(commands.Cog):
    # Dictionary to track message authors for each channel: {channel_id: [author_ids]}
    channels: dict[int, list[int]] = {}

    def __init__(self, bot: Goonbot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def chatting_listener(self, message: discord.Message):
        # Ignore messages in direct messages (DMs)
        if not message.guild:
            return

        # Get message details
        channel_id = message.channel.id
        author_id = message.author.id

        # Ensure the bot's user is defined and ignore specific guild and self-messages
        assert self.bot.user
        if message.guild == self.bot.BOTTING_TOGETHER or message.author.id == self.bot.user.id:
            return

        # This user is commonly in VC but needs to be muted, and uses text to communicate.
        # We'll exempt him from this "feature" when he's in voice channel
        for channel in message.guild.voice_channels:
            for user in channel.members:
                if user.id == ECTOPLAX_ID:
                    return

        # Initialize the channel's list of past chatters if not already present
        if not self.channels.get(channel_id):
            self.channels[channel_id] = []

        # Add the message's author to the list of past chatters for this channel
        self.channels[channel_id].append(author_id)
        channel_past_chatters_list = self.channels[channel_id]

        # If authors differ, reset the tracking for this channel
        if not sequence_same_value(channel_past_chatters_list):
            self.channels[channel_id] = []
            return

        # If the same author sends 5 consecutive messages, react to the message
        if len(channel_past_chatters_list) == 5:
            await message.add_reaction(
                random.choice(
                    [
                        "<a:chatting:1196923520442191923>",
                        "💀",
                        "<:clueless:934933705611444234>",
                    ]
                )
            )

            # Reset the channel's list after reacting
            self.channels[channel_id] = []


async def setup(bot):
    await bot.add_cog(ChattingWatch(bot))
