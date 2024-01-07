import json
import re

import aiohttp
import discord
from pulsefire.clients import RiotAPISchema

from text_processing import bullet_points, join_lines, make_possessive

from ..annotations import Augment, GameMode
from ..formatting import fstat, humanize_seconds


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


class ArenaParser:
    def __init__(
        self,
        target_summoner: RiotAPISchema.LolSummonerV4Summoner,
        match: RiotAPISchema.LolMatchV5Match,
    ) -> None:
        self.target_summoner = target_summoner
        self.match = match
        self.target_summoner_stats = self.get_target_summoner_stats()
        self._target_summoner_team_id = self.target_summoner_stats["teamId"]

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


ordinal_numbers = ["1st 👑", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th"]
int_to_ordinal = dict(zip(range(1, len(ordinal_numbers) + 1), ordinal_numbers))


def riot_md_to_md(text: str) -> str:
    """
    Bread And Butter: Your Q gains @QAbilityHaste@ Ability Haste.
    Slap Around: Each time you <status>Immobilize</status> an enemy, gain @AdaptiveForce@ Adaptive Force for the round, stacking infinitely.
    It's Killing Time: After casting your Ultimate, mark all enemy champions for death. The mark stores @DamageStorePercentage*100@% of damage dealt to them, then detonates for the stored damage after @MarkDuration@ seconds. (@Cooldown@ second Cooldown).
    """
    mappings = {
        "<status>": "**",
        "</status>": "**",
    }
    for pre, post in mappings.items():
        text = text.replace(pre, post)

    text = re.sub(r"@[^@]+@", "**N**", text)
    return text


async def arena_last_game_embed(parsed_data: ArenaParser) -> discord.Embed:
    augments = await get_augments()

    embed = discord.Embed(title="Arena Game Analysis", color=discord.Color.blurple())
    embed.description = join_lines(
        [
            fstat("Final placement", int_to_ordinal[parsed_data.final_placement]),
            fstat("Duration", humanize_seconds(parsed_data.match["info"]["gameDuration"])),
        ]
    )

    for participant in [parsed_data.target_summoner_stats, parsed_data.teammate_stats]:
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

        # Add the field
        embed.add_field(
            name=participant["summonerName"],
            value=join_lines([kda, *[fstat(name, amount) for name, amount in combat_stats_filtered]]),
        )

    for participant in [parsed_data.target_summoner_stats, parsed_data.teammate_stats]:
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
