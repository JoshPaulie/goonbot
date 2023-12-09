from dataclasses import dataclass
from typing import Literal

from pulsefire.schemas import RiotAPISchema


@dataclass
class MultiKill:
    name: str
    count: int


@dataclass
class ParticipantStat:
    participant_value: int
    participant_team_value: int
    total_stat_percent: float


match_info_participant_stat_keys = Literal[
    "assists",
    "damageDealtToBuildings",
    "damageDealtToObjectives",
    "damageDealtToTurrets",
    "damageSelfMitigated",
    "deaths",
    "detectorWardsPlaced",
    "doubleKills",
    "dragonKills",
    "goldEarned",
    "goldSpent",
    "inhibitorKills",
    "inhibitorTakedowns",
    "kills",
    "magicDamageDealt",
    "magicDamageDealtToChampions",
    "magicDamageTaken",
    "neutralMinionsKilled",
    "pentaKills",
    "physicalDamageDealt",
    "physicalDamageDealtToChampions",
    "physicalDamageTaken",
    "quadraKills",
    "sightWardsBoughtInGame",
    "timeCCingOthers",
    "totalAllyJungleMinionsKilled",
    "totalDamageDealt",
    "totalDamageDealtToChampions",
    "totalDamageShieldedOnTeammates",
    "totalDamageTaken",
    "totalEnemyJungleMinionsKilled",
    "totalHeal",
    "totalHealsOnTeammates",
    "totalMinionsKilled",
    "totalTimeCCDealt",
    "totalTimeSpentDead",
    "totalUnitsHealed",
    "tripleKills",
    "trueDamageDealt",
    "trueDamageDealtToChampions",
    "trueDamageTaken",
    "turretKills",
    "turretTakedowns",
    "turretsLost",
    "unrealKills",
    "visionClearedPings",
    "visionScore",
    "visionWardsBoughtInGame",
    "wardsKilled",
    "wardsPlaced",
]


def calc_participant_stat(
    participants: list[RiotAPISchema.LolMatchV5MatchInfoParticipant],
    target_participant: RiotAPISchema.LolSummonerV4Summoner,
    stat_names: list[match_info_participant_stat_keys]
    | match_info_participant_stat_keys,  # JOSH STOP MOVING THE LITERALS HERE, YOU NEVER LIKE IT
) -> ParticipantStat:
    """"""
    # Todo - refactor this to take a couple of stats, so we can calc kill participation
    # Todo - refactor to take (and return) the stat name, similar to how MultiKills function
    participant_team_id = None
    participant_stat_value = 0
    team_stat_value = 0
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