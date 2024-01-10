"""
We have wide variety of content creators that we like to share with one another. This family of commands
are simply provide links to either the creator's youtube channel, twitch channel, or both.
"""
import datetime as dt

import discord
from discord import app_commands
from discord.ext import commands
from googleapiclient.discovery import build
from twitchAPI.helper import first
from twitchAPI.twitch import Stream, Twitch, TwitchUser

from goonbot import Goonbot
from keys import Keys


def ftime(seconds: int):
    """Input seconds and return a string of how many minutes, but it's formatted nicely

    Seconds are passed because they're readily available from dt.timedeltas"""
    hours, remainder = divmod(seconds, 60 * 60)
    minutes, _ = divmod(remainder, 60)
    if not hours:
        return f"{minutes} min"
    elif hours and not minutes:
        return f"{hours} hr"
    return f"{hours} hr, {minutes} min"


async def get_streamer(login: str) -> tuple[TwitchUser, Stream | None]:
    """Returns a twitch user and (if they're live) their stream info"""
    twitch = await Twitch(Keys.TWITCH_CLIENT_ID, Keys.TWITCH_CLIENT_SECRET)
    # Gets the streamer data
    # Used for profile pic, offline profile pic, official username
    streamer = await first(twitch.get_users(logins=[login]))
    assert streamer
    # Gets stream data
    stream = await first(twitch.get_streams(user_login=[login]))
    await twitch.close()
    return streamer, stream


def how_long_since(started_at: dt.datetime) -> int:
    """Takes a reference datetime and returns (roughly) how many seconds since"""
    now = dt.datetime.now(tz=dt.timezone.utc)
    return (now - started_at).seconds


def make_twitch_embed(streamer: TwitchUser, stream: Stream | None) -> discord.Embed:
    """Returns a rich embed that changes depending on if they are live"""
    twitch_embed = discord.Embed()

    # case: streamer is not live
    if not stream:
        twitch_embed.title = f"{streamer.login} is offline. 😌"
        twitch_embed.set_image(url=streamer.offline_image_url)
        twitch_embed.color = discord.Color.greyple()
        return twitch_embed

    twitch_embed.title = f"{streamer.login} is live!"
    twitch_embed.description = stream.title
    twitch_embed.color = discord.Color.green()
    twitch_embed.set_thumbnail(url=streamer.profile_image_url)
    # This makes the title 'clickable'
    twitch_embed.url = "https://www.twitch.tv/" + streamer.login
    twitch_embed.add_field(name="Viewer Count", value=stream.viewer_count)
    twitch_embed.add_field(name="Game", value=stream.game_name)
    twitch_embed.add_field(
        name="Started",
        value=ftime(how_long_since(stream.started_at)) + " ago",
        inline=False,
    )
    twitch_embed.set_footer(text=", ".join(stream.tags))
    return twitch_embed


def get_latest_youtube_video(channel_id):
    """Returns url to a give channel's latest video"""
    # This is pretty much lifted straight for the docs
    # Sadly, the google api client a glorified wrapper that returns untyped dicts
    # Build YouTube interface
    youtube = build("youtube", "v3", developerKey=Keys.GOOGLE_API)
    # Get channel info
    channel_info = youtube.channels().list(id=channel_id, part="contentDetails").execute()
    # Blindly hack and slash until we get the ID for their uploads playlist
    # fun fact: all channels have a "hidden" uploads playlist. This is what you see when
    # you visit someone's youtube channel. It's predictably a list of all public videos on the channel
    uploads_playlist_id = channel_info["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    uploads_playlist_response = (
        youtube.playlistItems().list(playlistId=uploads_playlist_id, part="snippet", maxResults=1).execute()
    )
    # Snipe that video ID amidst the chaos that is the JSON response
    video_id = uploads_playlist_response["items"][0]["snippet"]["resourceId"]["videoId"]
    # Finally, assemble the url by appending the video idea to the base youtube video url
    return "https://www.youtube.com/watch?v=" + video_id


class CreatorView(discord.ui.View):
    """
    Simple view that is used if a creator makes content both Twitch and YouTube. Provides a button for either platform.
    """

    def __init__(self, *, youtube_channel_id: str, twitch_username: str):
        self.youtube_channel_id = youtube_channel_id
        self.twitch_user = twitch_username
        super().__init__(timeout=12)

    async def on_timeout(self) -> None:
        self.clear_items()
        return await super().on_timeout()

    @discord.ui.button(label="Twitch", style=discord.ButtonStyle.blurple)
    async def twitch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        streamer, stream = await get_streamer(self.twitch_user)
        twitch_embed = make_twitch_embed(streamer, stream)

        # Send embed, remove view
        assert interaction.message
        await interaction.message.edit(embed=twitch_embed, view=None)

    @discord.ui.button(label="Youtube", style=discord.ButtonStyle.red)
    async def youtube_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        latest_upload_url = get_latest_youtube_video(self.youtube_channel_id)

        # Send embed, remove view
        assert interaction.message
        await interaction.message.edit(content=latest_upload_url, view=None)


class CreatorWatch(commands.Cog):
    """Quickly link to selected creator's youtube or twitch"""

    creators = {
        # "name": (youtube, twitch)
        "Baus": ("UCu7ODDeIZ4x1rJwM1LCVL8w", "thebausffs"),
        "Happy Hob": ("UC0E1n0GRgBW5gR7y7H9TjZQ", "the_happy_hob"),
        "Dr. Campbell": ("UCF9IOB2TExg3QIBupFtBDxg", None),
        "Dan Gheesling": ("UCVHtlynIkgJxxXrisVUZlYQ", "dangheesling"),
        "Northern Lion": ("UC3tNpTOHsTnkmbwztCs30sA", "northernlion"),
        "Nexpo": ("UCpFFItkfZz1qz5PpHpqzYBw", None),
        "Library of Letourneau": ("UC_O58Rr2DOskJvs9bArpLkQ", None),
        "Squeex": ("UCSnd_UHkXW7uBpjHz4qIq5Q", "squeex"),
        "Fascinating Horror": ("UCFXad0mx4WxY1fXdbvtg0CQ", None),
        "Settled": ("UCs-w7E2HZWwXmjt9RTvBB_A", None),
        "Review Brah": ("UCeR0n8d3ShTn_yrMhpwyE1Q", None),
    }

    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="creator")
    @app_commands.choices(
        creator_name=[app_commands.Choice(name=c, value=c) for c in sorted(creators.keys())]
    )
    async def creator(self, interaction: discord.Interaction, creator_name: app_commands.Choice[str]):
        youtube_id, twitch_username = self.creators[creator_name.value]
        if youtube_id and twitch_username:
            return await interaction.response.send_message(
                view=CreatorView(
                    youtube_channel_id=youtube_id,
                    twitch_username=twitch_username,
                ),
            )

        if youtube_id:
            return await interaction.response.send_message(get_latest_youtube_video(youtube_id))

        if twitch_username:
            streamer, stream = await get_streamer(twitch_username)
            twitch_embed = make_twitch_embed(streamer, stream)
            return await interaction.response.send_message(embed=twitch_embed)


async def setup(bot):
    await bot.add_cog(CreatorWatch(bot))
