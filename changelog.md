# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> [!Note]
> Check out the changes between **goonbot5** and **goonbot 6.0** [here](#600)

## [Unreleased]
Changes made, but not associated with a particular version yet

## [6.0.0]
> [!Tip]
> The "goonbot" project no longer has a separate codebases to distinguish between major version changes. This is the true "final" goonbot. The reason for separating projects is explained a bit more [here](README.md#why-another-rewrite).

Goonbot 6.0 is considerably more thought out than previous versions. Most commands were rewritten with the following in mind
- Maintainable code that I'm not scared of extending in the future
- Minimize/eliminate the chance of the end user seeing an "interaction failed" message
- Only include features I wanted to maintain, while making those features as future proof as possible.
- No more "worry about it when it breaks" implementations

The code is, dare I say, much more Pythonic and is no longer littered with `type: ignore`

### League commands are BACK!
Yes! Reliably working league intergration that doesn't hate the name RoninAlex is back, and with a few new goodies. Read more [here](docs/league.md)

### Added
- `/about <docs page>`
  - Allows you to explore goonbot features in detail, without having to leave Discord
- `/cat`
  - similar to rat but cat, you get it
- `/addpic`
  - Anyone can add images/gifs to cat, rat, and real.
- **Auto* twitter embedding**
  - Goonbot listens for twitter links and when they are posted, will offer to "replace" the normal link with a fxtwitter link. Fxtwitter creates a rich embed that twitter no longer provides. Read more [here](docs/twitter-embed.md)
- `/diceroll` emulates dice rolling and accepts "dnd notation" (ie. 4d6, 2d20)


### Fixed
- `/wie`
  - now follows the social convetion of considering early morning hours to be part of the previous day's "nighttime". Night owls, rejoice!
- `/today` & `/calendar`
  - previous interations of these commands required the bot to be restarted each new year. commands now continue working, despite the change of year
  - covered every edgecase imaginable, as previous iterations of this command were prone to breakage
  - fixed 4th of July date which, and I'm not kidding, had the wrong date set
  - added halloween

### Changed
- all commands that utilize randomness (rats, wow no invite responses) won't repeat content until all available options have been served
- `/today` & `/calendar`
  - refactored to handle many events on the same day
- `/rat`, `/real`, all other commands that serve images or gifs
  - Images are now served by just posting the image link. Discord embeds and tenor gifs didnt always play nice, and nowadays discord hides the url of media content.
- `/real` now adds to reactions to the image, allowing the community to "vote"
- `/wni`
  - new responses
- `/creator <name>` is the new way to quickly link our favorite personalities, like NL or Baus. Although it's not as convenient calling the personality name directly, this is a cleaner implementation. Read more [here](docs/creator-watch.md)
- `/teams` provides an easy way to divide users in a voice channel into teams
- `/pickforme` (previously chooseforme) has been reworked to use a modal, allowing users to provide choices in a textbox

### Removed
- Hobo's `/username`
  - seldom used
- Gambling games
  - little interest from dev
  - annoying to maintain and balance related games

### Dependency changes
#### Discord
As previously mentioned, we are now using **discord.py**, and no longer using **pycord**
#### Youtube
Swapped from the (questionably typed) **youtube-python** for the official **Google API Client**
#### Twitch
Swapped the synchronous **python-twitch** with the asynchronous **pytwitchapi**
#### Riot games
Previous generations of goonbot relied on **cassiopeia**, a synchronous library, lovely library with beautiful caching. It was wonderful, other than it sucked. We're now using **pulsefire**, which is ✨ asynchronous ✨ and provides beautiful caching
