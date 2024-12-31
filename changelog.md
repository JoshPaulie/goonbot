# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> [!Note]
> Check out the changes between **goonbot5** and **goonbot 6.0** [here](#600)

## [Unreleased]
Changes made, but not associated with a particular version yet

## [6.1.0]
First minor release, including important command tree changes. Big thanks to @Sobheab from the discord.py gang.

### Fixed
- `.sync` and other meta command-related changes

#### League
League commands are back!
- Updated pulsefire (underlying league package)
- Refactored commands to use "new" Riot ID convention

### Removed
- **Grammar geek** (you're*) cog removed

## [6.0.5]
Biggest change: `/creator` is now `/watch`

### Added
- **Twitter Embed** message command
  - Used to run a twitter link through FixTweet
- **How long ago** message command
  - Tells you how long ago a message was sent
  - "I'll be on in 10"
- `/watch`
  - New personalities
    - Dantes

### Changed
- `/creator` was renamed to `/watch`
- **Twitter Embedding**
  - Tweets that have media (polls, videos) are automatically replied with links served through FixTweet. Read more [here](docs/twitter-embed.md)


## [6.0.4]
😌 evening patches 1/24/24

### Add
- `/recent`
  - New feature that allows you to specify 0 as the `match_count`, which gathers games played today rather than a specific amount
  - Example usage: `/recent gamemode:Draft Pick summoner_name:bexli match_count:0`
  - Recent also now has a doc page, which was somehow missed

### Changed
- `/diceroll`
  - No longer shows advantage/disadvantage when user only rolls one die
- `/champion`
  - Response is now ephemeral, meaning only you can see the response and auto deletes after awhile

## [6.0.3b]
Second batch of suggestions

### Added
- **Grammar geek** cog to make goonbot the most annoying bot ever (inspired by RoninAlex suggestion)
  - No extra note. Wouldn't want to spoil the fun, would we?
- `/creator`
  - New personalities
    - NeverKnowsBest (suggested by Poydok)
    - Patritian (suggested by Poydok)
    - Nemesis (a favorite of Ectoplax)
    - Mega64 (a favorite of RoninAlex)

### Fixed
- `/peepotalk` is no longer `/peepotlak`

### Disabled
- FixTweet
  - FixTweet is disabled until space man decides to disable twitter embeds again

## [6.0.3a]
The first small batch of community suggestions

**6.0.3** will be made up of two parts. I wanted to get the command tracking going ASAP, to minimize how far back I need to manually enter command usage stats

> [!Note]
> This update technically (🤓☝️) involves user tracking. Read more about the privacy policy [here](docs/privacy-policy.md)

### Added
- Command usage tracker (suggested by boxrog)
  - Goonbot will tally how many times each user has used a command
  - This data will be fun for later use, like a Goonbot unwrapped

### Changed
- **Chatting Watch** (suggested by Ectoplax)
  - Now uses a random reaction
  - New reactions
    - 💀
    - :clueless:


## [6.0.2]
First hot fix! And `/teams` changes

### Hot Fixed
- **Delete a bot message**
  - Goonbot got a bit over zealous with the last patch, and was stopping anyone from deleting any of his messages. He's been nerfed
- **Send Love**
  - Mentions the user, so you're no longer sending love the ether

### Changed
- `/teams`
  - Formatting changes!
    - "Mention" users
    - Numbered teams, which discord nicely spaces out because it's technically markdown

## [6.0.1]
First patch!

### Changed
- **Delete a bot message** feature has been limited to whoever invoked the bot message
  - The community (predictably to anyone not named 'josh') abused this feature mere moments after discovering it
- `/lastgame`
  - The "match ended X minutes ago" now uses the end time of the game, and not the start. It looked weird if you checked the command immediately after the game ended, and it said you played it 35 minutes ago.

### Fixed
- `/addpic`
  - Typo in description 🚗 (thanks for report alex)
- `/summoner`
  - Champions (like Akshan) sometimes have line breaks in their kit, apparently. They were the \<br> tags. They now render correctly in Discord

## [6.0.0]
> [!Note]
> The "goonbot" project no longer has a separate codebases to distinguish between major version changes. This is the true "final" goonbot. The reason for separating projects is explained a bit more [here](README.md#why-another-rewrite).

Goonbot 6.0 is considerably more thought out than previous versions. Most commands were rewritten with the following in mind
- Maintainable code that I'm not scared of extending in the future
- Minimize/eliminate the chance of the end user seeing an "interaction failed" message
- Only include features I wanted to maintain, while making those features as future proof as possible.
- No more "worry about it when it breaks" implementations

The code is, dare I say, much more Pythonic and is no longer littered with `type: ignore`

### Didn't make it for launch
Notable mentions that didn't make it for launch

- Poydok's random YouTube video command
- Alex's secret feature
- Suggestion command

### League commands are BACK!
Yes! Reliably working league intergration that doesn't hate the name RoninAlex is back, and with a few new goodies. Read more [here](docs/league.md)

### Added
- `/about <docs page>` explore goonbot features in detail, without having to leave Discord
- `/cat` similar to rat but cat, you get it (suggested by **Ectoplax**)
- `/addpic` anyone can add images/gifs to cat, rat, and real
- **Auto\* twitter embedding** Goonbot listens for twitter links and when they are posted, will offer to "replace" the normal link with a fxtwitter link. Fxtwitter creates a rich embed that twitter no longer provides. Read more [here](docs/twitter-embed.md)
- `/diceroll` emulates dice rolling and accepts "dnd notation" (ie. 4d6, 2d20)
- `/summoner` summoner stats including ranked stats and mastery points
- `/lastgame` analysis of your last game
  - With special parser for Arena games
- `/aram` analysis of your last 50 (or all) ARAM games
- `/champion` summary of a champion's kits
- `/recent` summary of your recent league games, of a specified queue (quickplay, draft, both ranks). In addition to the gamemode, you can also specify how many matches to go back. (Max 50)


### Fixed
- `/wie`
  - now follows the social convetion of considering early morning hours to be part of the previous day's "nighttime". Night owls, rejoice!
- `/today` & `/calendar`
  - previous interations of these commands required the bot to be restarted each new year. commands now continue working, despite the change of year
  - covered every edgecase imaginable, as previous iterations of this command were prone to breakage
  - fixed 4th of July date which, and I'm not kidding, had the wrong date set
  - added halloween

### Changed
- all commands that utilize randomness (rats, wow no invite responses)
  - won't repeat content until all available options have been served
- The **:chatting:** listener
  - Ectoplax is no longer totally exempt from getting *chatted*! He is now only exempt when in a voice channel
- `/today` & `/calendar`
  - refactored to handle many events on the same day, or the day after
- `/rat`, `/real`, all other commands that serve images or gifs
  - images are now served by just posting the image link. Discord embeds and tenor gifs didn't always play nice, and nowadays discord hides the url of media content
- `/real`
  - adds to reactions to the image, allowing the community to "vote"
- `/wni`
  - new responses
- `/creator <name>`
  - the new way to quickly link our favorite personalities, like NL or Baus
  - although it's not as convenient calling the personality name directly, this is a cleaner implementation. 
  - New personalities
    - Library of Letourneau
    - Dr. Todd Grande
    - Nexpo
    - ReportOfTheWeek/Review Brah
- `/teams`
  - easy way to divide users in a voice channel into teams
- `/pickforme` (previously chooseforme)
  - has been reworked to use a modal, allowing users to provide choices in a textbox

### Removed
- Hobo's `/username`
  - seldom used
  - this is a project i'd list on a portfolio, and i can't be bothered to pick out any potentially problematic user names
- Gambling games
  - little interest from dev
  - annoying to maintain and balance related games

### Dependency changes
#### Discord
Switch back to **discord.py**, and no longer using **pycord**
#### Youtube
Swapped from the (questionably typed) **youtube-python** for the official **Google API Client**
#### Twitch
Swapped the synchronous **python-twitch** with the asynchronous **pytwitchapi**
#### Riot games
Previous generations of goonbot relied on **cassiopeia**, a synchronous library, lovely library with beautiful caching. It was wonderful, other than it sucked. We're now using **pulsefire**, which is ✨ asynchronous ✨ and provides beautiful caching
