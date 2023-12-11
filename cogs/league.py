import asyncio
import operator
import time
from itertools import batched
from typing import Optional

import discord
from aiohttp.client_exceptions import ClientResponseError
from discord import app_commands
from discord.ext import commands
from pulsefire.clients import CDragonClient, RiotAPIClient, RiotAPISchema
from pulsefire.taskgroups import TaskGroup

from goonbot import Goonbot
from text_processing import make_plural, make_possessive, multiline_string, time_ago

from .league_utils import MultiKill, ParticipantStat, calc_kill_participation, calc_participant_stat


def get_cdragon_url(path: str) -> str:
    """ "Maps" paths according to the provided link. Some responses from pulsefire are incomplete and need to be
    mapped to its relative page on Community Dragon

    https://github.com/CommunityDragon/Docs/blob/master/assets.md#mapping-paths-from-json-files
    """
    base_cdragon_url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/"
    trimmed_path = path[len("/lol-game-data/assets") :]
    return base_cdragon_url + trimmed_path


def timestamp_from_seconds(duration_seconds: int) -> str:
    """Takes seconds and responds with a timestamp of the following format: 00:00

    Examples
        - 62 -> 01:02
    """
    minutes, remaining_seconds = divmod(duration_seconds, 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"


def make_profile_url(profile_id: int) -> str:
    return f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/{profile_id}.jpg"


# Todo add optional extra stat for ()
def fstat(
    name: str,
    value: str | int | float,
    make_name_plural: bool = False,
    extra_stat: Optional[str | int | float] = None,
) -> str:
    if make_name_plural:
        name = make_plural(name)

    if isinstance(value, int):
        value = f"{value:,d}"

    output = f"{name} **{value}**"
    if extra_stat:
        output += f" ({extra_stat})"

    return output


def format_number(num: int) -> str:
    if num >= 1_000_000:
        return str(round(num / 1_000_000, 1)) + "m"
    elif num >= 1_000:
        return str(round(num / 1_000, 1)) + "k"
    else:
        return str(round(num, 1))


def calc_winrate(wins: int, losses: int) -> str:
    total_games = wins + losses
    return f"{round((wins / total_games) * 100)}%"


rank_reaction_strs = {
    "unranked": "<:unranked:1178350707427004527>",
    "iron": "<:iron:1178350718676107324>",
    "bronze": "<:bronze:1178350735881150594>",
    "silver": "<:silver:1178350710564343878>",
    "gold": "<:gold:1178350724615258133>",
    "platinum": "<:platinum:1178350713563263027>",
    "emerald": "<:emerald:1178350726909526036>",
    "diamond": "<:diamond:1178350730126561290>",
    "master": "<:master:1178350716985819208>",
    "grandmaster": "<:grandmaster:1178350721847005224>",
    "challenger": "<:challenger:1178350733855301643>",
}


def create_queue_field(entry: RiotAPISchema.LolLeagueV4LeagueFullEntry):
    wins = entry["wins"]
    losses = entry["losses"]
    return multiline_string(
        [
            fstat("Rank", f"{entry['tier'].title()} {entry['rank']} ({entry['leaguePoints']} lp)"),
            fstat("Win/Loss", f"{wins:,d}/{losses:,d} ({calc_winrate(wins, losses)})"),
        ]
    )


REGION_NA1 = "na1"
REGION_AMERICAS = "americas"


class League(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

    async def build_log_urls(self, puuids: list[str]):
        async with RiotAPIClient(default_headers={"X-Riot-Token": self.bot.keys.RIOT_API}) as client:
            async with TaskGroup(asyncio.Semaphore(100)) as tg:
                for puuid in puuids:
                    await tg.create_task(client.get_account_v1_by_puuid(region="americas", puuid=puuid))

            account_details: list[RiotAPISchema.AccountV1Account] = tg.results()

        base_log_url = "https://www.leagueofgraphs.com/summoner/na/"
        return [
            f"[{acc['gameName']}]({base_log_url}{acc['gameName'].replace(' ', '+')}-{acc['tagLine']})"
            for acc in account_details
        ]

    @app_commands.command(name="summoner", description="Get stats for a summoner")
    async def summoner(self, interaction: discord.Interaction, summoner_name: str):
        await interaction.response.defer()
        # Get summoner data
        async with RiotAPIClient(default_headers={"X-Riot-Token": self.bot.keys.RIOT_API}) as client:
            try:
                summoner = await client.get_lol_summoner_v4_by_name(region=REGION_NA1, name=summoner_name)
            except ClientResponseError:
                return await interaction.response.send_message(
                    embed=self.bot.embed(
                        title=f"Summoner '{summoner_name}' not found",
                        color=discord.Color.brand_red(),
                    )
                )
            league_entries = await client.get_lol_league_v4_entries_by_summoner(
                region=REGION_NA1, summoner_id=summoner["id"]
            )
            mastery_points = await client.get_lol_champion_v4_masteries_by_puuid(
                region=REGION_NA1, puuid=summoner["puuid"]
            )
        # Build embed
        summoner_embed = self.bot.embed(title=summoner["name"])
        summoner_embed.set_thumbnail(url=make_profile_url(summoner["profileIconId"]))
        # Get league ranks
        for league_entry in league_entries:
            match league_entry["queueType"]:
                case "RANKED_SOLO_5x5":
                    summoner_embed.insert_field_at(
                        index=0,
                        name=f"Solo/Duo {rank_reaction_strs[league_entry['tier'].lower()]}",
                        value=create_queue_field(league_entry),
                    )
                case "RANKED_FLEX_SR":
                    summoner_embed.add_field(
                        name=f"Flex {rank_reaction_strs[league_entry['tier'].lower()]}",
                        value=create_queue_field(league_entry),
                    )
        # Set mastries
        async with CDragonClient(default_params={"patch": "latest", "locale": "default"}) as client:
            champions = await client.get_lol_v1_champion_summary()
        champion_id_to_name = {champion["id"]: champion["name"] for champion in champions}
        top_5_mp_champs = [
            f"{champion_id_to_name[champ_mastery_stats['championId']]} {format_number(champ_mastery_stats['championPoints'])}"
            for champ_mastery_stats in mastery_points[:5]
        ]
        summoner_embed.set_footer(text=" · ".join(top_5_mp_champs))
        # Send embed
        await interaction.followup.send(embed=summoner_embed)

    # Todo - make this generic so both commands can use it
    @summoner.autocomplete("summoner_name")
    async def summoner_name_autocomplete(self, interaction: discord.Interaction, current: str):
        GOON_SUMMONER_NAMES = [
            "bexli",
            "mltsimpleton",
            "ectoplax",
            "roninalex",
            "artificialmeat",
            "large frog tamer",
            "boxrog",
            "vynle",
            "poydok",
            "cradmajone",
        ]

        return [
            app_commands.Choice(name=name, value=name)
            for name in sorted(GOON_SUMMONER_NAMES)
            if current.lower() in name.lower()
        ]

    @app_commands.command(name="lastgame", description="An analysis of your lastest league game!")
    async def last_match_analysis(self, interaction: discord.Interaction, summoner_name: str):
        """"""
        # Start timer for response time
        start_time = time.perf_counter()
        # If an interaction takes more than 3 seconds, discord considers it failed.
        # The remedy to this oddity is to "defer" the response, then "follow up" later
        await interaction.response.defer()

        async with RiotAPIClient(default_headers={"X-Riot-Token": self.bot.keys.RIOT_API}) as client:
            # Get summoner data
            try:
                summoner = await client.get_lol_summoner_v4_by_name(region=REGION_NA1, name=summoner_name)
            # If this throws an exception, it's more than likely because the summoner doesn't exist
            except ClientResponseError:
                return await interaction.response.send_message(
                    embed=self.bot.embed(
                        title=f"Summoner '{summoner_name}' not found", color=discord.Color.brand_red()
                    )
                )
            # Get ID of most recent match
            last_match_id = (
                await client.get_lol_match_v5_match_ids_by_puuid(
                    region="americas", puuid=summoner["puuid"], queries={"start": 0, "count": 1}
                )
            )[0]
            # Get match data
            last_match = await client.get_lol_match_v5_match(region="americas", id=last_match_id)

        # Get champion data (for champion image)
        async with CDragonClient(default_params={"patch": "latest", "locale": "default"}) as client:
            champions = await client.get_lol_v1_champion_summary()
        # Dict to get champ image paths
        champion_id_to_image_path = {champion["id"]: champion["squarePortraitPath"] for champion in champions}

        # Pull stats for description
        # Specify the participant
        target_summoner_stats = None
        for participant in last_match["info"]["participants"]:
            if participant["puuid"] == summoner["puuid"]:
                target_summoner_stats = participant
                break
        assert target_summoner_stats

        # Game outcome
        won_game = target_summoner_stats["win"]

        # champion meta
        champion_id = target_summoner_stats["championId"]
        champion_image_path = champion_id_to_image_path[champion_id]
        champion_image_path_full = get_cdragon_url(champion_image_path)

        # team meta
        team_id = target_summoner_stats["teamId"]
        teammates: list[RiotAPISchema.LolMatchV5MatchInfoParticipant] = sorted(
            [
                participant
                for participant in last_match["info"]["participants"]
                if participant["teamId"] == team_id
            ],
            key=operator.itemgetter("summonerName"),
        )

        # Determine role
        lane = target_summoner_stats["lane"]
        role = target_summoner_stats["role"]

        if role == "NONE":
            role = None

        if lane == "NONE":
            lane = "N/A"

        # Final score
        team_100_kills = 0
        team_200_kills = 0
        for participant in last_match["info"]["participants"]:
            if participant["teamId"] == 100:
                team_100_kills += participant["kills"]
            else:
                team_200_kills += participant["kills"]
        if team_id == 100:
            final_score = f"{team_100_kills} | {team_200_kills}"
        else:
            final_score = f"{team_200_kills} | {team_100_kills}"

        # KDA
        kills = target_summoner_stats["kills"]
        deaths = target_summoner_stats["deaths"]
        assists = target_summoner_stats["assists"]
        kda = f"{kills}/{deaths}/{assists}"
        if deaths == 0:
            kda_ratio = "PERF!"
            kda += " 🥵"
        else:
            kda_ratio = str(round((kills + assists) / deaths, 2)) + " ratio"

        # Determine queue type, replace with common name
        match last_match["info"]["queueId"]:
            case 400:
                game_mode = "Draft Pick"
            case 420:
                game_mode = "Ranked Solo"
            case 430:
                game_mode = "Blind Pick"
            case 440:
                game_mode = "Ranked Flex"
            case 450:
                game_mode = "ARAM"
            case _ as unknown_game_mode:
                game_mode = f"Unknown game mode: {unknown_game_mode} (ping jarsh)"

        # Gametime stats
        game_duration_minutes = last_match["info"]["gameDuration"] // 60
        game_duration = timestamp_from_seconds(last_match["info"]["gameDuration"])
        if game_duration_minutes < 20 and won_game:
            game_duration += " 🔥"
        if game_duration_minutes > 40:
            game_duration += " 🐢"
        ended_ago = time_ago(last_match["info"]["gameStartTimestamp"] // 1000)

        # Build embed
        last_match_embed = discord.Embed(title=f"{make_possessive(summoner['name'])} last game analysis")
        last_match_embed.set_thumbnail(url=champion_image_path_full)
        last_match_embed.color = discord.Color.brand_green() if won_game else discord.Color.brand_red()

        # Game meta, final score, kda
        last_match_embed.description = multiline_string(
            [
                fstat("Game mode", game_mode, extra_stat="Victory!" if won_game else "Defeat."),
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
            tm["puuid"] for tm in teammates if tm["puuid"] != target_summoner_stats["puuid"]
        ]
        last_match_embed.add_field(
            name="Teammates",
            value=", ".join([link for link in await self.build_log_urls(teammate_puuids_no_target)]),
            inline=False,
        )

        # Stop the show if it was less than 5 minutes
        if game_duration_minutes < 5:
            last_match_embed.description += "\n\nGame was remade."
            last_match_embed.color = discord.Color.greyple()
            return await interaction.followup.send(embed=last_match_embed, ephemeral=True)

        # Stats field
        # Todo - move from tuples to dataclass
        popular_stats: list[tuple[str, ParticipantStat]] = [
            ("💪 Champ damage", calc_participant_stat(teammates, summoner, "totalDamageDealtToChampions")),
            ("🏰 Obj. damage", calc_participant_stat(teammates, summoner, "damageDealtToObjectives")),
            ("🛡️ Damage Taken", calc_participant_stat(teammates, summoner, "totalDamageTaken")),
            ("❤️‍🩹 Ally Healing", calc_participant_stat(teammates, summoner, "totalHealsOnTeammates")),
            ("🩸 Kill participation", calc_kill_participation(teammates, summoner)),
            ("💀 Feed participation", calc_participant_stat(teammates, summoner, "deaths")),
        ]
        formated_popular_stats = [
            fstat(
                stat[0],
                format_number(stat[1].participant_value),
                extra_stat=f"{stat[1].total_stat_percent}%",
            )
            for stat in popular_stats
        ]
        formated_popular_stats_batched = batched(formated_popular_stats, 2)
        last_match_embed.add_field(
            name="Stats 📊",
            value=multiline_string([" · ".join(pair) for pair in formated_popular_stats_batched]),
            inline=False,
        )

        # Farming and Vision stats field
        creep_score = (
            target_summoner_stats["totalMinionsKilled"] + target_summoner_stats["neutralMinionsKilled"]
        )
        cs_per_min = round(creep_score / game_duration_minutes, 1)
        total_gold = target_summoner_stats["goldEarned"]
        gold_per_min = round(total_gold / game_duration_minutes, 1)
        last_match_embed.add_field(
            name="Farming & Vision 🧑‍🌾",
            value=multiline_string(
                [
                    fstat("CS", f"{creep_score}", extra_stat=f"{cs_per_min} cs/min"),
                    fstat("Gold", f"{total_gold:,d}", extra_stat=f"{gold_per_min:,} gp/min"),
                    fstat("Vision Score", target_summoner["visionScore"]),
                    fstat("Wards destroyed", target_summoner["wardsKilled"]),
                ]
            ),
        )

        # Multi kill field
        if target_summoner_stats["largestMultiKill"] > 1:
            multi_kills = [
                MultiKill("Double Kill", target_summoner_stats["doubleKills"]),
                MultiKill("Triple Kill", target_summoner_stats["tripleKills"]),
                MultiKill("Quadra Kill", target_summoner_stats["quadraKills"]),
                MultiKill("👑 Penta Kill", target_summoner_stats["pentaKills"]),
            ]
            # Format the multikills for output, and only include the stat if they had at least 1
            multi_kills = [
                fstat(mk.name, mk.count, make_name_plural=(mk.count > 0))
                for mk in multi_kills
                if mk.count > 0
            ]
            last_match_embed.add_field(
                name="Multi kills ⚔️",
                value=multiline_string(multi_kills),
            )

        # Send embed
        end_time = time.perf_counter()
        loading_time = round(end_time - start_time, 2)
        last_match_embed.set_footer(text=f"Elapsed loading time: {loading_time}ms")
        await interaction.followup.send(embed=last_match_embed)


async def setup(bot):
    await bot.add_cog(League(bot))
