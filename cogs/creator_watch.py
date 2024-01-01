"""
We have wide variety of content creators that we like to share with one another. This family of commands
are simply provide links to either the creator's youtube channel, twitch channel, or both.
"""
import datetime as dt
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from googleapiclient.discovery import build
from twitchAPI.helper import first
from twitchAPI.twitch import Stream, Twitch, TwitchUser

from goonbot import Goonbot
from keys import Keys


class CreatorView(discord.ui.View):
    """
    Crude view that provides buttons to either: the creator's latest YouTube video or the creator's twitch
    channel. The Twitch portion has the extra flair of checking of checking if they are currently live
    streaming now. If so, the title and for how long

    Ideally, if the creator only published one of the two platforms, the relevant embed would just sent.
    This way the user wouldn't have to click the sole available button. It feels redundant.
    """

    @staticmethod
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

    @staticmethod
    def how_long_since(started_at: dt.datetime) -> int:
        """Takes a reference datetime and returns (roughly) how many seconds since"""
        now = dt.datetime.now(tz=dt.timezone.utc)
        return (now - started_at).seconds

    def __init__(
        self,
        *,
        timeout: float | None = 30,
        youtube_channel_id: Optional[str] = None,
        twitch_username: Optional[str] = None,
    ):
        self.youtube_channel_id = youtube_channel_id
        self.twitch_user = twitch_username
        super().__init__(timeout=timeout)

        # Because we don't want both buttons every time, we must declare each button, assign it callback
        # functions, and finally add them to the view.
        twitch_button = discord.ui.Button(label="Twitch", style=discord.ButtonStyle.blurple)
        twitch_button.callback = self.twitch_button_callback
        youtube_button = discord.ui.Button(label="YouTube", style=discord.ButtonStyle.red)
        youtube_button.callback = self.youtube_button_callback

        if youtube_channel_id:
            self.add_item(youtube_button)

        if twitch_username:
            self.add_item(twitch_button)

    async def on_timeout(self) -> None:
        self.clear_items()
        return await super().on_timeout()

    async def youtube_button_callback(self, interaction: discord.Interaction):
        latest_upload_url = self.get_latest_youtube_video(self.youtube_channel_id)
        assert interaction.message
        await interaction.message.edit(content=latest_upload_url, view=None)

    async def twitch_button_callback(self, interaction: discord.Interaction):
        assert self.twitch_user
        streamer, stream = await self.get_streamer(self.twitch_user)
        twitch_embed = discord.Embed()
        if stream:
            twitch_embed.title = f"{streamer.login} is live!"
            twitch_embed.description = stream.title
            twitch_embed.color = discord.Color.green()
            twitch_embed.set_thumbnail(url=streamer.profile_image_url)
            # This makes the title 'clickable'
            twitch_embed.url = "https://www.twitch.tv/" + self.twitch_user
            twitch_embed.add_field(name="Viewer Count", value=stream.viewer_count)
            twitch_embed.add_field(name="Game", value=stream.game_name)
            twitch_embed.add_field(
                name="Started",
                value=self.ftime(self.how_long_since(stream.started_at)) + " ago",
                inline=False,
            )
            twitch_embed.set_footer(text=", ".join(stream.tags))
        else:
            twitch_embed.title = f"{streamer.login} is offline. 😌"
            twitch_embed.set_image(url=streamer.offline_image_url)
            twitch_embed.color = discord.Color.greyple()
        # Send embed
        assert interaction.message
        await interaction.message.edit(embed=twitch_embed, view=None)

    async def get_streamer(self, login: str) -> tuple[TwitchUser, Stream | None]:
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

    def get_latest_youtube_video(self, channel_id):
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
            youtube.playlistItems()
            .list(playlistId=uploads_playlist_id, part="snippet", maxResults=1)
            .execute()
        )
        # Snipe that video ID amidst the chaos that is the JSON response
        video_id = uploads_playlist_response["items"][0]["snippet"]["resourceId"]["videoId"]
        # Finally, assemble the url by appending the video idea to the base youtube video url
        return "https://www.youtube.com/watch?v=" + video_id


class CreatorWatch(commands.Cog):
    """Quickly link to selected creator's youtube or twitch"""

    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="test_creator")
    async def test_creator(self, interaction: discord.Interaction):
        """Template command description"""
        await interaction.response.send_message(
            view=CreatorView(
                youtube_channel_id=None,
                twitch_username="Gnomonkey",
            ),
        )


async def setup(bot):
    await bot.add_cog(CreatorWatch(bot))
