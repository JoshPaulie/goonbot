from collections import Counter

from pulsefire.clients import RiotAPISchema

from ..annotations import match_info_participant_stat_keys
from ..formatting import humanize_seconds


class ARAMPerformanceParser:
    def __init__(
        self,
        target_summoner: RiotAPISchema.LolSummonerV4Summoner,
        aram_match_history: list[RiotAPISchema.LolMatchV5Match],
    ) -> None:
        """The main function of this"""
        self.target_summoner = target_summoner
        self.aram_match_history = aram_match_history
        self.aram_match_count = len(aram_match_history)

        self.target_summoner_stats = self.get_target_summoner_stats()

        # Stats
        self.total_kills = self.get_stat_from_matches("kills")
        self.total_deaths = self.get_stat_from_matches("deaths")
        self.total_assists = self.get_stat_from_matches("assists")
        self.total_kda_ratio = (
            round((self.total_kills + self.total_assists) / self.total_deaths, 2)
            if self.total_deaths
            else "Perfect KDA!"
        )

        # Resource gathering
        self.total_gold = self.get_stat_from_matches("goldEarned")
        self.total_minions = self.get_stat_from_matches("totalMinionsKilled")

        # Damage and healing
        self.total_champion_damage = self.get_stat_from_matches("totalDamageDealtToChampions")
        self.total_objective_damage = self.get_stat_from_matches("damageDealtToObjectives")
        self.total_turret_takedowns = self.get_stat_from_matches("turretTakedowns")
        self.total_damage_taken = self.get_stat_from_matches("totalDamageTaken")
        self.total_teammate_healing = self.get_stat_from_matches("totalHealsOnTeammates")

        # Game length
        self.total_game_duration = self.calc_total_match_durations()
        self.total_time_spent_dead = self.get_stat_from_matches("totalTimeSpentDead")
        self.total_time_dead_percentage = round(self.total_time_spent_dead / self.total_game_duration * 100)

        # Champs played
        self.most_played_champion_ids = Counter(self.get_played_champion_ids()).most_common(4)

        # Win/loss
        self.total_wins = self.get_stat_from_matches("win")
        self.total_losses = self.aram_match_count - self.total_wins
        self.total_win_rate = round((self.total_wins / self.aram_match_count) * 100)

        # Multi kills
        self.total_double_kills = self.get_stat_from_matches("doubleKills")
        self.total_triple_kills = self.get_stat_from_matches("tripleKills")
        self.total_quadra_kills = self.get_stat_from_matches("quadraKills")
        self.total_penta_kills = self.get_stat_from_matches("pentaKills")

    def calc_total_match_durations(self) -> int:
        return sum([match["info"]["gameDuration"] for match in self.aram_match_history])

    def get_target_summoner_stats(self) -> list[RiotAPISchema.LolMatchV5MatchInfoParticipant]:
        participant_stats = []
        for match in self.aram_match_history:
            for participant in match["info"]["participants"]:
                if self.target_summoner["puuid"] == participant["puuid"]:
                    participant_stats.append(participant)
                    break
        return participant_stats

    def get_stat_from_matches(self, stat_name: match_info_participant_stat_keys) -> int:
        return sum([match_stats[stat_name] for match_stats in self.target_summoner_stats])

    def get_played_champion_ids(self) -> list[int]:
        return [int(match["championId"]) for match in self.target_summoner_stats]
