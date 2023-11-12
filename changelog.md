# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Check out the changes between **goonbot5** and **goonbot 6.0** [here](#600)

## [Unreleased]
Changes made, but not associated with a particular version yet

## [6.0.0]
> The "goonbot" project no longer has a separate codebases to distinguish between major version changes. This is the true "final" goonbot. The reason for separating projects is explained a bit more [here](README.md#why-another-rewrite).

Goonbot 6.0 is considerably more thought out than previous versions. Most commands were rewritten with the following in mind
- Maintainable code that I'm not scared of extending in the future
- Minimize/eliminate the chance of the end user seeing an "interaction failed" message
- Only include features I wanted to maintain, while making those features as future proof as possible.
- No more "worry about it when it breaks" implementations

The code is, dare I say, much more Pythonic and is no longer littered with `type: ignore`

### Added

### Fixed
- `/wie`
  - now follows the social convetion of considering early morning hours to be part of the previous day's "nighttime"
- `/today` & `/calendar`
  - previous interations of these commands required the bot to be restarted each new year. commands now continue working, despite the change of year
  - covered every edgecase imaginable, as previous iterations of this command were prone to breakage
  - fixed 4th of July date which, and I'm not kidding, had the wrong date set
  - added halloween

### Changed
- `/today` & `/calendar`
  - refactored to handle many events on one day
- `/rats`
  - broken rats are now reportable, allowing broken images to be tested, then fixed or removed
  - links are manually "fixed" by reuploading gifs to discord and using the discord URL, which links to their CDN instead of Tenor (for whatever reason Tenor gifs don't work in discord embeds)
- `/wni`
  - new responses
  - responses don't repeat until they've all been used
- **I love you** user command now has permanent and rotating affirmations

### Removed
- Hobo's `/username`
  - seldom used
- Gambling games
  - little interest from dev
  - annoying to maintain and balance related games