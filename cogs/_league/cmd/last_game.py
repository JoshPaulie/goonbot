import json
import operator
import re
from itertools import batched

import aiohttp
import discord
from pulsefire.clients import RiotAPISchema

from cogs._league.cdragon_builders import get_cdragon_url
from cogs._league.objects import ParticipantStat, calc_kill_participation, create_participant_stat
from text_processing import bullet_points, join_lines, make_possessive, time_ago

from ..annotations import Augment, GameMode
from ..formatting import format_big_number, fstat, humanize_seconds, timestamp_from_seconds


# Fetchers
async def get_all_queue_ids() -> list[GameMode]:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://static.developer.riotgames.com/docs/lol/queues.json") as response:
            response_text = await response.text()
            response_json: list[GameMode] = json.loads(response_text)
    return response_json


async def get_augments() -> list[Augment]:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://raw.communitydragon.org/latest/cdragon/arena/en_us.json") as response:
            response_text = await response.text()
            response_json: dict[str, list[Augment]] = json.loads(response_text)
    return response_json["augments"]


def augment_id_to_name(augments: list[Augment], _id: int) -> Augment | None:
    for augment in augments:
        if augment["id"] == _id:
            return augment


# Parsers
class ArenaMatchParser:
    ordinal_numbers = ["1st 👑", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th"]
    int_to_ordinal = dict(zip(range(1, len(ordinal_numbers) + 1), ordinal_numbers))

    def __init__(
        self,
        target_summoner: RiotAPISchema.LolSummonerV4Summoner,
        match: RiotAPISchema.LolMatchV5Match,
        champion_id_to_image_path: dict[int, str],
        champion_id_to_name: dict[int, str],
    ) -> None:
        self.target_summoner = target_summoner
        self.match = match
        self.target_summoner_stats = self.get_target_summoner_stats()
        self._target_summoner_team_id = self.target_summoner_stats["teamId"]
        self.champion_id_to_image_path = champion_id_to_image_path
        self.champion_id_to_name = champion_id_to_name

    @property
    def final_placement(self) -> int:
        return self.target_summoner_stats["subteamPlacement"]

    @property
    def teammate_stats(self) -> RiotAPISchema.LolMatchV5MatchInfoParticipant:
        for participant in self.match["info"]["participants"]:
            if (
                self._target_summoner_team_id == participant["teamId"]
                and participant["puuid"] != self.target_summoner["puuid"]
            ):
                return participant
        raise

    def get_target_summoner_stats(self) -> RiotAPISchema.LolMatchV5MatchInfoParticipant:
        for participant in self.match["info"]["participants"]:
            if self.target_summoner["puuid"] == participant["puuid"]:
                return participant
        raise

    async def make_embed(self) -> discord.Embed:
        augments = await get_augments()

        # champion meta
        champion_id = self.target_summoner_stats["championId"]
        champion_image_path = self.champion_id_to_image_path[champion_id]
        champion_image_path_full = get_cdragon_url(champion_image_path)

        embed = discord.Embed(title="Arena Game Analysis", color=discord.Color.blurple())
        embed.set_thumbnail(url=champion_image_path_full)
        embed.description = join_lines(
            [
                fstat("Final placement", self.int_to_ordinal[self.final_placement]),
                fstat("Duration", humanize_seconds(self.match["info"]["gameDuration"])),
            ]
        )

        for participant in [self.target_summoner_stats, self.teammate_stats]:
            # Name
            name = participant["summonerName"]

            # KDA
            kda = f"{participant['kills']}/{participant['deaths']}/{participant['assists']}"

            # Combat stats
            combat_stats = [
                ("Damage", participant["totalDamageDealtToChampions"]),
                ("Healing", participant["totalHealsOnTeammates"]),
                ("Shielded", participant["totalDamageShieldedOnTeammates"]),
                ("CC dealt", participant["totalTimeCCDealt"]),
            ]
            # Filter out stats that are 0
            combat_stats_filtered = [(name, amount) for name, amount in combat_stats if amount]
            champion_name = self.champion_id_to_name[participant["championId"]]

            # Add the field
            embed.add_field(
                name=f"{name}\n{champion_name}",
                value=join_lines([kda, *[fstat(name, amount) for name, amount in combat_stats_filtered]]),
            )

        for participant in [self.target_summoner_stats, self.teammate_stats]:
            name = participant["summonerName"]
            participant_augment_ids = [
                augment_id_to_name(augments, participant["playerAugment1"]),
                augment_id_to_name(augments, participant["playerAugment2"]),
                augment_id_to_name(augments, participant["playerAugment3"]),
                augment_id_to_name(augments, participant["playerAugment4"]),
            ]
            augments_formated = [
                f"**{aug['name']}**: {riot_md_to_md(aug['desc'])}" for aug in participant_augment_ids if aug
            ]
            embed.add_field(
                name=f"{make_possessive(name)} augments",
                value=bullet_points(augments_formated),
                inline=False,
            )

        return embed


def riot_md_to_md(text: str) -> str:
    """
    Reformats Riot's in-game md to regular markdown. In-game it's super rich, but it looks quite odd outside of the client

    Below is an example
    Bread And Butter: Your Q gains @QAbilityHaste@ Ability Haste.
    Slap Around: Each time you <status>Immobilize</status> an enemy, gain @AdaptiveForce@ Adaptive Force for the round, stacking infinitely.
    It's Killing Time: After casting your Ultimate, mark all enemy champions for death. The mark stores @DamageStorePercentage*100@% of damage dealt to them, then detonates for the stored damage after @MarkDuration@ seconds. (@Cooldown@ second Cooldown).
    """
    riot_keywords = ["keywordMajor", "status", "abilityName", "scaleAD", "scaleAP", "moveSpeed"]
    mappings = {"<br>": " ", "<br><br>": " "}
    for keyword in riot_keywords:
        mappings.update({f"<{keyword}>": "**"})
        mappings.update({f"</{keyword}>": "**"})

    for pre, post in mappings.items():
        text = text.replace(pre, post)

    text = re.sub(r"@[^@]+@", "*some*", text)
    return text


class StandardMatchParser:
    def __init__(
        self,
        summoner: RiotAPISchema.LolSummonerV4Summoner,
        match: RiotAPISchema.LolMatchV5Match,
        champion_id_to_image_path: dict[int, str],
        gamemode: str,
    ) -> None:
        self.target_summoner = summoner
        self.match = match
        self.champion_id_to_image_path = champion_id_to_image_path
        self.game_mode = gamemode
        # team meta

    @property
    def team_id(self):
        return self.target_summoner_stats["teamId"]

    @property
    def teammates(self):
        teammates: list[RiotAPISchema.LolMatchV5MatchInfoParticipant] = sorted(
            [
                participant
                for participant in self.match["info"]["participants"]
                if participant["teamId"] == self.team_id
            ],
            key=operator.itemgetter("summonerName"),
        )
        return teammates

    @property
    def target_summoner_stats(self) -> RiotAPISchema.LolMatchV5MatchInfoParticipant:
        for participant in self.match["info"]["participants"]:
            if self.target_summoner["puuid"] == participant["puuid"]:
                return participant
        raise

    def make_embed(self, teammate_links: list[str]):
        # Game outcome
        won_game = self.target_summoner_stats["win"]

        # champion meta
        champion_id = self.target_summoner_stats["championId"]
        champion_image_path = self.champion_id_to_image_path[champion_id]
        champion_image_path_full = get_cdragon_url(champion_image_path)

        # Determine role
        lane = self.target_summoner_stats["lane"]
        role = self.target_summoner_stats["role"]

        if role == "NONE":
            role = None

        if lane == "NONE":
            lane = "N/A"

        # Final score
        team_100_kills = 0
        team_200_kills = 0
        for participant in self.match["info"]["participants"]:
            if participant["teamId"] == 100:
                team_100_kills += participant["kills"]
            else:
                team_200_kills += participant["kills"]

        # Arrange the scores so it's always in the following order
        # target participant team kills | enemy team kills
        if self.team_id == 100:
            final_score = f"{team_100_kills} | {team_200_kills}"
        else:
            final_score = f"{team_200_kills} | {team_100_kills}"

        # KDA
        kills = self.target_summoner_stats["kills"]
        deaths = self.target_summoner_stats["deaths"]
        assists = self.target_summoner_stats["assists"]
        kda = f"{kills}/{deaths}/{assists}"

        # KDA ratio
        if deaths == 0:
            kda_ratio = "PERF!"
            kda += " 🥵"
        else:
            kda_ratio = str(round((kills + assists) / deaths, 2)) + " ratio"

        # Gametime stats
        game_duration_minutes = self.match["info"]["gameDuration"] // 60
        game_duration = timestamp_from_seconds(self.match["info"]["gameDuration"])
        if game_duration_minutes < 20 and won_game:
            game_duration += " 🔥"
        if game_duration_minutes > 40:
            game_duration += " 🐢"
        ended_ago = time_ago(self.match["info"]["gameStartTimestamp"] // 1000)

        # Build embed
        last_match_embed = discord.Embed(
            title=f"{make_possessive(self.target_summoner['name'])} last game analysis"
        )
        last_match_embed.set_thumbnail(url=champion_image_path_full)
        last_match_embed.color = discord.Color.brand_green() if won_game else discord.Color.brand_red()

        # Game meta, final score, kda
        last_match_embed.description = join_lines(
            [
                fstat("Game mode", self.game_mode, extra_stat="Victory!" if won_game else "Defeat."),
                fstat("Duration", game_duration, extra_stat=ended_ago),
                fstat("Final score", final_score),
                fstat("KDA", kda, extra_stat=kda_ratio),
                fstat("Position", lane.title())
                if not role
                else fstat("Position", lane.title(), extra_stat=role.title()),
            ]
        )

        # Teammates field
        teammate_puuids_no_target = [
            tm["puuid"] for tm in self.teammates if tm["puuid"] != self.target_summoner_stats["puuid"]
        ]
        last_match_embed.add_field(
            name="Teammates",
            value=", ".join(teammate_links),
            inline=False,
        )

        # Stop the show if it was less than 5 minutes
        if game_duration_minutes < 5:
            last_match_embed.description += "\n\nGame was remade."
            last_match_embed.color = discord.Color.greyple()
            return last_match_embed

        # Stats field
        popular_stats: list[tuple[str, ParticipantStat]] = [
            (
                "💪 Champ damage",
                create_participant_stat(self.teammates, self.target_summoner, "totalDamageDealtToChampions"),
            ),
            (
                "🏰 Obj. damage",
                create_participant_stat(self.teammates, self.target_summoner, "damageDealtToObjectives"),
            ),
            (
                "🛡️ Damage Taken",
                create_participant_stat(self.teammates, self.target_summoner, "totalDamageTaken"),
            ),
            (
                "❤️‍🩹 Ally Healing",
                create_participant_stat(self.teammates, self.target_summoner, "totalHealsOnTeammates"),
            ),
            ("🩸 Kill participation", calc_kill_participation(self.teammates, self.target_summoner)),
            ("💀 Feed participation", create_participant_stat(self.teammates, self.target_summoner, "deaths")),
        ]
        formated_popular_stats = [
            fstat(
                stat_name,
                format_big_number(stat_value.participant_value),
                extra_stat=f"{stat_value.total_stat_percent}%",
            )
            for stat_name, stat_value in popular_stats
        ]
        formated_popular_stats_batched = batched(formated_popular_stats, 2)
        last_match_embed.add_field(
            name="Stats 📊",
            value=join_lines([" · ".join(pair) for pair in formated_popular_stats_batched]),
            inline=False,
        )

        # Farming and Vision stats field
        creep_score = (
            self.target_summoner_stats["totalMinionsKilled"]
            + self.target_summoner_stats["neutralMinionsKilled"]
        )
        cs_per_min = round(creep_score / game_duration_minutes, 1)
        total_gold = self.target_summoner_stats["goldEarned"]
        gold_per_min = round(total_gold / game_duration_minutes, 1)
        gold_vision_stats: list[tuple[str, ParticipantStat]] = [
            (
                "Vision score",
                create_participant_stat(self.teammates, self.target_summoner, "visionScore"),
            ),
            (
                "Wards Placed",
                create_participant_stat(self.teammates, self.target_summoner, "wardsPlaced"),
            ),
            (
                "Wards Destroyed",
                create_participant_stat(self.teammates, self.target_summoner, "wardsKilled"),
            ),
        ]
        last_match_embed.add_field(
            name="Farming & Vision 🧑‍🌾",
            value=join_lines(
                [
                    fstat("CS", creep_score, extra_stat=f"{cs_per_min} cs/min"),
                    fstat(
                        "Gold",
                        format_big_number(total_gold),
                        extra_stat=f"{gold_per_min:,} gp/min",
                    ),
                    *[
                        fstat(
                            stat_name,
                            stat_value.participant_value,
                            extra_stat=f"{stat_value.participant_team_value}%",
                        )
                        for stat_name, stat_value in gold_vision_stats
                    ],
                ]
            ),
        )

        # Multi kill field
        if self.target_summoner_stats["largestMultiKill"] > 1:
            multi_kills: list[tuple[str, int]] = [
                ("Double Kill", self.target_summoner_stats["doubleKills"]),
                ("Triple Kill", self.target_summoner_stats["tripleKills"]),
                ("Quadra Kill", self.target_summoner_stats["quadraKills"]),
                ("👑 Penta Kill", self.target_summoner_stats["pentaKills"]),
            ]
            last_match_embed.add_field(
                name="Multi kills ⚔️",
                value=join_lines(
                    [
                        fstat(stat_name, stat_value, pluralize_name_auto=True)
                        for stat_name, stat_value in multi_kills
                        if stat_value
                    ]
                ),
            )

        # Send embed
        return last_match_embed
