# League of Legends intergeration
Goonbot has a couple of analytic commands for League.

## Summoner
Provides a few details like rank in each queue type (if any), current in-game profile picture, and top champion masteries.

## Last Game
Last game is a simple analytic tool that checks your last game.

### "Stats" section
The **stats** section is made up of lines consisting of a stat name, how much you earned/dealt/received, and how much of yours contributes to the total amount your team outputted.

For example, if your team finished with 20 kills, and you earned 8 kills + 2 assists, your "kill participation" stat would be "**10** (50%)".

### "It got my role/lane wrong!"
Literal [multi-billion](https://levvvel.com/riot-games-statistics/) dollar Riot can't seem to tell which lane you end up in. No one in the API community is sure how they determine this to begin with. Unfortunately it's just the best we got, and I'd prefer to have some than none