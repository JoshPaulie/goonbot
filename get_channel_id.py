"""
Simple tool that takes a url to a youtube channel and returns the channel ID.
Youtube is kind of a mess right now, with a few different channel url schemas. The channel id for a channel
isn't always obvious, especially with the new username system. Regardless of the url, this tool
can pluck the channel id

Example inputs:
    - https://youtube.com/c/nasa
    - https://www.youtube.com/@DrGrande
    - https://www.youtube.com/channel/UCkRfArvrzheW2E7b6SVT7vQ
"""

import re
import sys

import requests


class ChannelIDNotFound(Exception):
    pass


def get_channel_id(youtube_channel_url: str) -> str | None:
    # Requests lib requires a protocol be specified
    if not youtube_channel_url.startswith("http"):
        raise ValueError("URL must start with 'https://' or 'http://'")

    # Older (or "legacy") channels who have not migrated to one of the two channel naming convetions have the ID
    # already present, which we can return it without making an http request. (IDs are always 24 char long)
    if "/channel/" in youtube_channel_url:
        return youtube_channel_url[-24:]

    # For "modern" channel urls, we need to make an http request for the source,
    # then pick through it for the external ID. We do this with the help of regex
    pattern = r'"externalId":"(.*?)"'
    source = requests.get(youtube_channel_url)
    match = re.search(pattern, source.content.decode())
    if match:
        return match.group(1)
    raise ChannelIDNotFound(
        "Uh oh. Either the URL provided is incorrect, or YouTube changed the source for channel pages."
    )


def main():
    args = sys.argv
    if len(args) != 1:
        url = sys.argv[1]
    else:
        url = input("Channel url: ")

    try:
        id = get_channel_id(url)
    except ValueError as e:
        return print(e)
    except ChannelIDNotFound as e:
        return print(e)
    print(id)


if __name__ == "__main__":
    main()
