from pulsefire.clients import RiotAPISchema

from text_processing import multiline_string

from ..calculators import calc_winrate
from ..formatting import fstat


def league_entry_stats(entry: RiotAPISchema.LolLeagueV4LeagueFullEntry):
    wins = entry["wins"]
    losses = entry["losses"]
    return multiline_string(
        [
            fstat("Rank", f"{entry['tier'].title()} {entry['rank']} ({entry['leaguePoints']} lp)"),
            fstat("Win/Loss", f"{wins:,d}/{losses:,d} ({calc_winrate(wins, losses)})"),
        ]
    )
