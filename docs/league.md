# League of Legends intergeration
Goonbot has a couple of analytic commands for League.
+++
## No name needed
You can use any league-related commands without specifying a summoner name. The bot knows everyone's summoner name and will automatically use it as a default.

This means that if Josh wanted to get his last game, he'd just type `/lastgame` and not `/lastgame bexli`
+++
## League commands are semi-synchronous
Goonbot commands work asynchronously, allowing multiple people to use many commands simultaneously and receive their responses as the finish processing. However, League commands don't operate in the same way.

As a limitation of using `discord.py` with `pulsefire`, league commands are (effectively) processed in a queue. So if 2 people use a league commands around the same time, the first caller's command must finish processing before the following is started
+++
## Cached data
A lot of the data that supports League commands is cached, resulting in much faster command execution times.

- Some data doesn't change after it's been created, like match data, and can be cached indefinitely.
  - This is great for commands that process many matches at a time, because we're not asking Riot for the same match's data twice.
- Some data can be cached for a bit, like a summoner's mastery points. 
- Some data has be fetched every time, like a summoner's match list.

It's worth noting if you're querying a match not yet cached (ie. your last game played), you can expect longer loading times, because that data needs to be fetched from Riot.
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