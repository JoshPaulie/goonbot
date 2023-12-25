from dataclasses import dataclass
from functools import total_ordering

from pulsefire.schemas import RiotAPISchema

from .annotations import match_info_participant_stat_keys


# todo turn this into a full class with a __str__ method, that uses the create_participant as a constructor
# that is just the **value** (team%) format
@dataclass
class ParticipantStat:
    participant_value: int
    participant_team_value: int
    total_stat_percent: float


def create_participant_stat(
    participants: list[RiotAPISchema.LolMatchV5MatchInfoParticipant],
    target_participant: RiotAPISchema.LolSummonerV4Summoner,
    stat_names: list[match_info_participant_stat_keys]
    | match_info_participant_stat_keys,  # JOSH STOP MOVING THE LITERALS HERE, YOU NEVER LIKE IT
) -> ParticipantStat:
    """"""
    participant_team_id = None
    participant_stat_value = 0
    team_stat_value = 0

    # if a single stat is passed, just add it to a list
    if not isinstance(stat_names, list):
        stat_names = [stat_names]

    for stat_name in stat_names:
        for participant in participants:
            if participant["puuid"] == target_participant["puuid"]:
                participant_team_id = participant["teamId"]
                participant_stat_value += participant[stat_name]
                break

        participant_teammates = [
            participant for participant in participants if participant["teamId"] == participant_team_id
        ]

        for participant in participant_teammates:
            stat_amount = participant[stat_name]
            team_stat_value += stat_amount

    # Covers: Divide by 0 exception
    if team_stat_value != 0:
        percentage_amount = round((participant_stat_value / team_stat_value) * 100, 1)
    else:
        percentage_amount = 0.0

    return ParticipantStat(participant_stat_value, team_stat_value, percentage_amount)


def calc_kill_participation(
    participants: list[RiotAPISchema.LolMatchV5MatchInfoParticipant],
    target_participant: RiotAPISchema.LolSummonerV4Summoner,
) -> ParticipantStat:
    """Similar to create_participant_stat(), but different enough to require a separate function"""
    participant_team_id = None
    participant_stat_value = 0
    team_stat_value = 0
    stat_names: list[match_info_participant_stat_keys] = ["kills", "assists"]
    for stat_name in stat_names:
        for participant in participants:
            if participant["puuid"] == target_participant["puuid"]:
                participant_team_id = participant["teamId"]
                participant_stat_value += participant[stat_name]
                break

        participant_teammates = [
            participant for participant in participants if participant["teamId"] == participant_team_id
        ]

        # We only want to tally kills for the team, we don't care about assists
        if stat_name == "kills":
            for participant in participant_teammates:
                stat_amount = participant[stat_name]
                team_stat_value += stat_amount

    # Covers: Divide by 0 exception
    if team_stat_value != 0:
        percentage_amount = round((participant_stat_value / team_stat_value) * 100, 1)
    else:
        percentage_amount = 0.0

    return ParticipantStat(participant_stat_value, team_stat_value, percentage_amount)


@total_ordering
class LeagueRank:
    _tiers = ["Iron", "Bronze", "Silver", "Gold", "Platinum", "Emerald", "Diamond"]
    _tier_values = dict(zip(_tiers, list(range(len(_tiers)))))

    _divisions = ["VI", "III", "II", "I"]
    _division_values = dict(zip(_divisions, list(range(len(_divisions)))))

    def __init__(self, tier: str, division: str, lp: int):
        self.tier = tier
        self.division = division
        self.lp = lp

    @property
    def value(self):
        return self._tier_values[self.tier] + self._division_values[self.division] + self.lp

    def __eq__(self, other):
        return self.value == other.value

    def __lt__(self, other):
        return self.value < other.value
