from collections import Counter
from itertools import batched

import discord
from pulsefire.clients import RiotAPISchema

from cogs._league.cdragon_builders import get_cdragon_url
from cogs._league.formatting import format_big_number, fstat, humanize_seconds
from text_processing import join_lines

from ..annotations import match_info_participant_stat_keys


# todo
# [ ] Focus on Champion Winrate first
class Last20Parser:
    def __init__(
        self,
        target_summoner: RiotAPISchema.LolSummonerV4Summoner,
        aram_match_history: list[RiotAPISchema.LolMatchV5Match],
        gamemode_name: str,
    ) -> None:
        """The main function of this"""
        self.summoner = target_summoner
        self.matches = aram_match_history
        self.match_count = len(aram_match_history)
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

        # Resource gathering
        self.total_gold_earned = self.get_stat_from_matches("goldEarned")
        self.total_minions_killed = self.get_stat_from_matches("totalMinionsKilled")
        self.total_turret_takedowns = self.get_stat_from_matches("turretTakedowns")
        self.total_inhibitor_takedowns = self.get_stat_from_matches("inhibitorTakedowns")

        # Damage and healing
        self.total_champion_damage = self.get_stat_from_matches("totalDamageDealtToChampions")
        self.total_objective_damage = self.get_stat_from_matches("damageDealtToObjectives")
        self.total_damage_taken = self.get_stat_from_matches("totalDamageTaken")
        self.total_teammate_healing = self.get_stat_from_matches("totalHealsOnTeammates")

        # CC
        self.total_cc_dealt = self.get_stat_from_matches("totalTimeCCDealt")

        # Game length
        self.total_game_duration = self.calc_total_match_durations()
        self.total_time_spent_dead = self.get_stat_from_matches("totalTimeSpentDead")
        self.total_time_dead_percentage = round(self.total_time_spent_dead / self.total_game_duration * 100)

        # Champs played
        self.most_played_champion_ids = Counter(self.get_played_champion_ids()).most_common(20)

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

    def get_champion_winrate(self):
        for stat in self.target_summoner_stats:
            pass

    def make_embed(self, champion_id_to_image_path: dict[int, str], champion_id_to_name: dict[int, str]):
        aram_embed = discord.Embed(
            title=f"{self.summoner['name']} {self.gamemode_name} stats",
            description=f"Analysis of your last **{len(self.matches)}** {self.gamemode_name} games!",
        )

        # Thumbnail of most played champ
        # Confusingly enough, this is just the first entry in the counter
        most_played_champ_id = self.most_played_champion_ids[0][0]
        champion_image_path = champion_id_to_image_path[most_played_champ_id]
        champion_image_path_full = get_cdragon_url(champion_image_path)
        aram_embed.set_thumbnail(url=champion_image_path_full)

        aram_embed.add_field(
            name="Most played champions",
            value=" • ".join(
                [
                    f"{champion_id_to_name[champ_id]} **{times_played}**"
                    for champ_id, times_played in self.most_played_champion_ids
                ]
            ),
            inline=False,
        )

        aram_embed.add_field(
            name="Duration",
            value=join_lines(
                [
                    f"Total match duration **{humanize_seconds(self.total_game_duration)}**",
                    f"Total time dead **{humanize_seconds(self.total_time_spent_dead)}**",
                    f"Percentage spent dead **{self.total_time_dead_percentage}%** ",
                    f"CC dealt **{humanize_seconds(self.total_cc_dealt)}**",
                ]
            ),
            inline=False,
        )

        aram_embed.add_field(
            name="Win & Losses",
            value=join_lines(
                [
                    fstat("Wins", self.total_wins),
                    fstat("Losses", self.total_losses),
                    fstat("Win rate", f"{self.total_win_rate}%"),
                ]
            ),
        )

        aram_embed.add_field(
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
        aram_embed.add_field(
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

        aram_embed.color = discord.Color.blurple()
        return aram_embed
