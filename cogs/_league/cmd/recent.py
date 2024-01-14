from collections import Counter, defaultdict
from dataclasses import dataclass

import discord
from pulsefire.clients import RiotAPISchema

from cogs._league.cdragon_builders import get_cdragon_url
from cogs._league.formatting import fstat, humanize_seconds
from text_processing import join_lines

from ..annotations import match_info_participant_stat_keys


@dataclass
class ChampionPerformance:
    champion_id: int
    played: int
    wins: int

    @property
    def win_rate(self) -> float:
        return round((self.wins / self.played) * 100)

    @property
    def win_rate_pretty(self) -> str:
        return f"{self.win_rate}%"


class RecentGamesParser:
    def __init__(
        self,
        target_summoner: RiotAPISchema.LolSummonerV4Summoner,
        matches: list[RiotAPISchema.LolMatchV5Match],
        gamemode_name: str,
    ) -> None:
        """The main function of this"""
        self.summoner = target_summoner
        self.matches = matches
        self.match_count = len(matches)
        self.gamemode_name = gamemode_name

        # Stats
        self.total_kills = self.get_stat_from_matches("kills")
        self.total_deaths = self.get_stat_from_matches("deaths")
        self.total_assists = self.get_stat_from_matches("assists")
        self.total_kda_ratio = (
            round((self.total_kills + self.total_assists) / self.total_deaths, 2)
            if self.total_deaths
            else "Perfect KDA!"
        )

        # Damage and healing
        self.total_champion_damage = self.get_stat_from_matches("totalDamageDealtToChampions")
        self.total_objective_damage = self.get_stat_from_matches("damageDealtToObjectives")
        self.total_damage_taken = self.get_stat_from_matches("totalDamageTaken")
        self.total_teammate_healing = self.get_stat_from_matches("totalHealsOnTeammates")

        # Game length
        self.total_game_duration = self.calc_total_match_durations()
        self.total_time_spent_dead = self.get_stat_from_matches("totalTimeSpentDead")
        self.total_time_dead_percentage = round(self.total_time_spent_dead / self.total_game_duration * 100)

        # Champs played
        self.most_played_champion_ids = Counter(self.get_played_champion_ids()).most_common(5)

        # Win/loss
        self.total_wins = self.get_stat_from_matches("win")
        self.total_losses = self.match_count - self.total_wins
        self.total_win_rate = round((self.total_wins / self.match_count) * 100)

        # Multi kills
        self.total_double_kills = self.get_stat_from_matches("doubleKills")
        self.total_triple_kills = self.get_stat_from_matches("tripleKills")
        self.total_quadra_kills = self.get_stat_from_matches("quadraKills")
        self.total_penta_kills = self.get_stat_from_matches("pentaKills")

    def calc_total_match_durations(self) -> int:
        return sum([match["info"]["gameDuration"] for match in self.matches])

    @property
    def target_summoner_stats(self) -> list[RiotAPISchema.LolMatchV5MatchInfoParticipant]:
        participant_stats = []
        for match in self.matches:
            for participant in match["info"]["participants"]:
                if self.summoner["puuid"] == participant["puuid"]:
                    participant_stats.append(participant)
                    break
        return participant_stats

    def get_stat_from_matches(self, stat_name: match_info_participant_stat_keys) -> int:
        return sum([match_stats[stat_name] for match_stats in self.target_summoner_stats])

    def get_played_champion_ids(self) -> list[int]:
        return [int(match["championId"]) for match in self.target_summoner_stats]

    def get_champion_performance(self) -> list[ChampionPerformance]:
        # schema: {champion_id: {"played": int, "wins": int}}
        champion_performance: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for summoner_match_stats in self.target_summoner_stats:
            champion_id = summoner_match_stats["championId"]
            outcome = summoner_match_stats["win"]
            champion_performance[champion_id]["played"] += 1
            if outcome:
                champion_performance[champion_id]["wins"] += 1

        performance = []
        for champion_name, stats in champion_performance.items():
            played = stats["played"]
            wins = stats.get("wins", 0)
            performance.append(ChampionPerformance(champion_name, played, wins))

        return sorted(performance, key=lambda x: x.played, reverse=True)

    def make_embed(self, champion_id_to_image_path: dict[int, str], champion_id_to_name: dict[int, str]):
        recent_embed = discord.Embed(
            title=f"{self.summoner['name']} {self.gamemode_name} stats",
            description=f"Analysis of your last **{len(self.matches)}** {self.gamemode_name} games!",
        )

        # Thumbnail of most played champ
        # Confusingly enough, this is just the first entry in the counter
        most_played_champ_id = self.most_played_champion_ids[0][0]
        champion_image_path = champion_id_to_image_path[most_played_champ_id]
        champion_image_path_full = get_cdragon_url(champion_image_path)
        recent_embed.set_thumbnail(url=champion_image_path_full)

        recent_embed.add_field(
            name="Champion Performance",
            value=join_lines(
                [
                    f"**{champion_id_to_name[champ_perf.champion_id]}** Games **{champ_perf.played}** // Wins **{champ_perf.wins}** ({champ_perf.win_rate_pretty})"
                    for champ_perf in self.get_champion_performance()
                ]
            ),
            inline=False,
        )

        recent_embed.add_field(
            name="Duration",
            value=join_lines(
                [
                    f"Total match duration **{humanize_seconds(self.total_game_duration)}**",
                    f"Total time dead **{humanize_seconds(self.total_time_spent_dead)}** ({self.total_time_dead_percentage}%)",
                ]
            ),
            inline=False,
        )

        recent_embed.add_field(
            name="Win & Losses",
            value=join_lines(
                [
                    fstat("Wins", self.total_wins),
                    fstat("Losses", self.total_losses),
                    fstat("Win rate", f"{self.total_win_rate}%"),
                ]
            ),
        )

        recent_embed.add_field(
            name="KDA",
            value=join_lines(
                [
                    fstat("Kill", self.total_kills, pluralize_name_auto=True),
                    fstat("Death", self.total_deaths, pluralize_name_auto=True),
                    fstat("Assist", self.total_assists, pluralize_name_auto=True),
                    fstat("Ratio", self.total_kda_ratio),
                ]
            ),
        )

        multi_kills = [
            ("Double Kill", self.total_double_kills),
            ("Triple Kill", self.total_triple_kills),
            ("Quadra Kill", self.total_quadra_kills),
            ("Penta Kill", self.total_penta_kills),
        ]
        recent_embed.add_field(
            name="Multi Kills",
            value=join_lines(
                [
                    fstat(name, kill_amount, pluralize_name_auto=True)
                    for name, kill_amount in multi_kills
                    if kill_amount
                ]
                or "You didn't get a single multi kill 🤣",
            ),
        )

        recent_embed.color = discord.Color.blurple()
        return recent_embed
