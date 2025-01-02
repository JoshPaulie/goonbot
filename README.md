#  goonbot
Overly documented discord.py bot for my longtime friend group

# Powered by
| Title                                                                       | Description                                                                           |
| --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| [Discord.py](https://github.com/Rapptz/discord.py)                          | Community implementation of the Discord API                                           |
| [Google API Client](https://github.com/googleapis/google-api-python-client) | Official Google API for Python, used for pulling YouTube videos                       |
| [pyTwitchAPI](https://github.com/Teekeks/pyTwitchAPI)                       | Community implementation of the Twitch Helix API                                      |
| [FxTwitter](https://github.com/FixTweet/FxTwitter)                          | Creates rich Tweets embeds that allows your to view tweet videos from within discord. |

# Why another rewrite?
I started learning the `discord.py` library as a means of learning Python back in 2019. For the first few years I rewrote the bot frequently to better reflect my Python ability. Because I was so new, it was easiest for me to create separate codebasses for each generation rather than extend/refactor my existing code. In addition, I was really misunderstanding the role of git, and didn't know how to commit major code changes.

Not only that, but `discord.py` was unmaintained for a short stint. A forked version of the wrapper was started, but had substantial differences between it and its upstream project. This meant once `discord.py` was officially being maintained by Danny again, I needed to refactor any app commands. This explains this latest (and "final") rewrite
