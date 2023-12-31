# League of Legends intergeration
Goonbot has a couple of analytic commands for League.
+++
## No name needed
You can use any league-related commands without specifying a summoner name, the bot knows everyone's summoner name and will automatically use it as a default.

This means that if Josh wanted to get his last game, he'd just type `/lastgame` and not `/lastgame bexli`
+++
## League commands are semi-synchronous
Goonbot commands work asynchronously, allowing multiple people to use the same command simultaneously and receive their responses at the same time. However, League commands don't operate in the same way.

As a limitation of using `discord.py` with `pulsefire`, league commands are (effectively) processed in a queue. So if 2 people use a league commands around the same time, the first caller's command must finish before the following is started
+++
## Cached data
A lot of the data that supports League commands is cached, resulting in much faster command execution times.

Because data for a match doesn't change after it's been finished, match data is held indefinitely. This means if the match being queried (ie. your last game played) hasn't yet been cached, you can expect longer loading times.
+++
## 'Summoner' Command
Provides a few details like rank in each queue type (if any), current in-game profile picture, and top champion masteries.
+++
## 'Last Game' Command
Last game is a simple analytic tool that checks your last game.

### Final score
The final score is in the following format: **ally team kills** | **enemy team kills**

### "Stats" section
The **stats** section is made up of lines consisting of a stat name, how much you earned/dealt/received, and how much of yours contributes to the total amount your team outputted.

For example, if your team finished with 20 kills, and you earned 8 kills + 2 assists, your "kill participation" stat would be "**10** (50%)".

### "It got my role/lane wrong!"
Literal [multi-billion](https://levvvel.com/riot-games-statistics/) dollar Riot can't seem to tell which lane you end up in. No one in the API community is sure how they determine this to begin with. Unfortunately it's just the best we got
+++
## 'ARAM' Command
Similar to lastgame but analyzes your last 50 ARAM games, and returns fun stats. Stats are cumulative, so "deaths" represents how many deaths you had in the 50 games in total.

If you have less than 50 ARAM games, all of your games will be analyzed