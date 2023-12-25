import asyncio
import operator
import time
from itertools import batched

import discord
from aiohttp.client_exceptions import ClientResponseError
from discord import app_commands
from discord.ext import commands
from pulsefire.caches import DiskCache
from pulsefire.clients import CDragonClient, RiotAPIClient, RiotAPISchema
from pulsefire.middlewares import (
    cache_middleware,
    http_error_middleware,
    json_response_middleware,
    rate_limiter_middleware,
)
from pulsefire.ratelimiters import RiotAPIRateLimiter
from pulsefire.taskgroups import TaskGroup

from goonbot import Goonbot
from text_processing import html_to_md, make_possessive, multiline_string, time_ago

from ._league.calculators import duration
from ._league.cdragon_builders import get_cdragon_url, make_profile_url
from ._league.cmd.aram import ARAMPerformanceParser
from ._league.cmd.champion import get_champion_id_by_name
from ._league.cmd.last_game import get_all_queue_ids
from ._league.cmd.summoner import league_entry_stats
from ._league.formatting import format_big_number, fstat, humanize_seconds, timestamp_from_seconds
from ._league.lookups import discord_to_summoner_name, rank_reaction_strs
from ._league.objects import ParticipantStat, calc_kill_participation, create_participant_stat

REGION_NA1 = "na1"
REGION_AMERICAS = "americas"


cache = DiskCache("cache")
riot_cache_middleware = cache_middleware(
    cache,
    [
        (lambda inv: inv.invoker.__name__ == "get_lol_summoner_v4_by_name", duration(days=1)),
        (lambda inv: inv.invoker.__name__ == "get_lol_match_v5_match", float("inf")),
        (lambda inv: inv.invoker.__name__ == "get_account_v1_by_puuid", duration(days=1)),
        (lambda inv: inv.invoker.__name__ == "get_lol_champion_v4_masteries_by_puuid", duration(days=1)),
    ],
)

cdragon_cache_middleware = cache_middleware(
    cache,
    [
        # Get champion pool
        (lambda inv: inv.invoker.__name__ == "get_lol_v1_champion_summary", duration(hours=4)),
        # Get specific champion details
        (lambda inv: inv.invoker.__name__ == "get_lol_v1_champion", duration(weeks=1)),
    ],
)


class League(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot
        self.client_lock = asyncio.Lock()

        self.riot_client = RiotAPIClient(
            default_headers={"X-Riot-Token": self.bot.keys.RIOT_API},
            middlewares=[
                riot_cache_middleware,
                json_response_middleware(),
                http_error_middleware(),
                rate_limiter_middleware(RiotAPIRateLimiter()),
            ],
        )

        self.cdragon_client = CDragonClient(
            default_params={"patch": "latest", "locale": "default"},
            middlewares=[
                cdragon_cache_middleware,
                json_response_middleware(),
                http_error_middleware(),
            ],
        )

    async def build_log_urls(self, puuids: list[str]):
        async with self.client_lock:
            async with self.riot_client as client:
                async with TaskGroup(asyncio.Semaphore(100)) as tg:
                    for puuid in puuids:
                        await tg.create_task(client.get_account_v1_by_puuid(region="americas", puuid=puuid))

                account_details: list[RiotAPISchema.AccountV1Account] = tg.results()

        base_log_url = "https://www.leagueofgraphs.com/summoner/na/"
        return [
            f"[{acc['gameName']}]({base_log_url}{acc['gameName'].replace(' ', '+')}-{acc['tagLine']})"
            for acc in account_details
        ]

    async def summoner_name_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=name, value=name)
            for name in sorted(discord_to_summoner_name.values())
            if current.lower() in name.lower()
        ]

    @app_commands.command(name="summoner", description="Get stats for a summoner")
    @app_commands.autocomplete(summoner_name=summoner_name_autocomplete)
    async def summoner(self, interaction: discord.Interaction, summoner_name: str | None):
        if summoner_name is None:
            summoner_name = discord_to_summoner_name[interaction.user.id]

        await interaction.response.defer()
        # Get summoner data
        async with self.client_lock:
            async with self.riot_client as client:
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
                        value=league_entry_stats(league_entry),
                    )
                case "RANKED_FLEX_SR":
                    summoner_embed.add_field(
                        name=f"Flex {rank_reaction_strs[league_entry['tier'].lower()]}",
                        value=league_entry_stats(league_entry),
                    )

        # Get mastery data
        async with self.client_lock:
            async with self.cdragon_client as client:
                champions = await client.get_lol_v1_champion_summary()
        champion_id_to_name = {champion["id"]: champion["name"] for champion in champions}
        top_5_mp_champs = [
            f"{champion_id_to_name[champ_mastery_stats['championId']]} {format_big_number(champ_mastery_stats['championPoints'])}"
            for champ_mastery_stats in mastery_points[:5]
        ]
        summoner_embed.set_footer(text=" · ".join(top_5_mp_champs))

        # Send embed
        await interaction.followup.send(embed=summoner_embed)

    @app_commands.command(name="lastgame", description="An analysis of your lastest league game!")
    @app_commands.autocomplete(summoner_name=summoner_name_autocomplete)
    async def last_match_analysis(self, interaction: discord.Interaction, summoner_name: str | None):
        """"""
        if summoner_name is None:
            summoner_name = discord_to_summoner_name[interaction.user.id]

        # Start timer for response time
        start_time = time.perf_counter()
        # If an interaction takes more than 3 seconds, discord considers it failed.
        # The remedy to this oddity is to "defer" the response, then "follow up" later
        await interaction.response.defer()

        async with self.client_lock:
            async with self.riot_client as client:
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
        async with self.client_lock:
            async with self.cdragon_client as client:
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

        # Arrange the scores so it's always in the following order
        # target participant team kills | enemy team kills
        if team_id == 100:
            final_score = f"{team_100_kills} | {team_200_kills}"
        else:
            final_score = f"{team_200_kills} | {team_100_kills}"

        # KDA
        kills = target_summoner_stats["kills"]
        deaths = target_summoner_stats["deaths"]
        assists = target_summoner_stats["assists"]
        kda = f"{kills}/{deaths}/{assists}"

        # KDA ratio
        if deaths == 0:
            kda_ratio = "PERF!"
            kda += " 🥵"
        else:
            kda_ratio = str(round((kills + assists) / deaths, 2)) + " ratio"

        # Determine queue type, replace with common name
        # ref: https://static.developer.riotgames.com/docs/lol/queues.json
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
            case 1700:
                game_mode = "Arena"
                return await interaction.followup.send(
                    embed=self.bot.embed(
                        title="Arena matches not yet supported",
                        color=discord.Color.greyple(),
                    )
                )
            case _ as not_set_queue_id:
                # Fallback that fetches the official game mode names
                all_queue_ids = await get_all_queue_ids()
                id_to_game_mode_name = {queue["queueId"]: queue["description"] for queue in all_queue_ids}
                if game_mode_name := id_to_game_mode_name[not_set_queue_id]:
                    game_mode = game_mode_name
                else:
                    game_mode = f"Unknown gamemode ({self.bot.ping_owner()})"

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
            ("💪 Champ damage", create_participant_stat(teammates, summoner, "totalDamageDealtToChampions")),
            ("🏰 Obj. damage", create_participant_stat(teammates, summoner, "damageDealtToObjectives")),
            ("🛡️ Damage Taken", create_participant_stat(teammates, summoner, "totalDamageTaken")),
            ("❤️‍🩹 Ally Healing", create_participant_stat(teammates, summoner, "totalHealsOnTeammates")),
            ("🩸 Kill participation", calc_kill_participation(teammates, summoner)),
            ("💀 Feed participation", create_participant_stat(teammates, summoner, "deaths")),
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
        gold_vision_stats: list[tuple[str, ParticipantStat]] = [
            ("Vision score", create_participant_stat(teammates, summoner, "visionScore")),
            ("Wards Placed", create_participant_stat(teammates, summoner, "wardsPlaced")),
            ("Wards Destroyed", create_participant_stat(teammates, summoner, "wardsKilled")),
        ]
        last_match_embed.add_field(
            name="Farming & Vision 🧑‍🌾",
            value=multiline_string(
                [
                    fstat("CS", creep_score, extra_stat=f"{cs_per_min} cs/min"),
                    fstat("Gold", format_big_number(total_gold), extra_stat=f"{gold_per_min:,} gp/min"),
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
        last_match_embed.set_footer(text=f"Elapsed loading time: {loading_time}s")
        await interaction.followup.send(embed=last_match_embed)

    @app_commands.command(name="aram", description="An analysis of your last 50 ARAM games")
    @app_commands.autocomplete(summoner_name=summoner_name_autocomplete)
    async def aram_analysis(self, interaction: discord.Interaction, summoner_name: str | None):
        # todo get rid of magic number that determines how many matches to look at
        if summoner_name is None:
            summoner_name = discord_to_summoner_name[interaction.user.id]

        # Start timer for response time
        start_time = time.perf_counter()
        await interaction.response.defer()

        async with self.client_lock:
            async with self.riot_client as client:
                # Get summoner data
                try:
                    summoner = await client.get_lol_summoner_v4_by_name(region=REGION_NA1, name=summoner_name)
                # If this throws an exception, it's more than likely because the summoner doesn't exist
                except ClientResponseError:
                    return await interaction.response.send_message(
                        embed=self.bot.embed(
                            title=f"Summoner '{summoner_name}' not found",
                            color=discord.Color.brand_red(),
                        )
                    )

                match_ids = await client.get_lol_match_v5_match_ids_by_puuid(
                    region="americas",
                    puuid=summoner["puuid"],
                    queries={"queue": 450, "count": 50},
                )
                async with TaskGroup(asyncio.Semaphore(100)) as tg:
                    for match_id in match_ids:
                        await tg.create_task(client.get_lol_match_v5_match(region="americas", id=match_id))
                aram_matches: list[RiotAPISchema.LolMatchV5Match] = tg.results()

        if not aram_matches:
            return await interaction.followup.send(
                embed=self.bot.embed(
                    title="This account doesn't have any ARAM games played",
                    color=discord.Color.greyple(),
                )
            )

        # Get champion data (for champion image)
        async with self.client_lock:
            async with self.cdragon_client as client:
                champions = await client.get_lol_v1_champion_summary()

        # Dict to get champ image paths
        champion_id_to_image_path = {champion["id"]: champion["squarePortraitPath"] for champion in champions}
        champion_id_to_name = {champion["id"]: champion["name"] for champion in champions}

        aram_stats = ARAMPerformanceParser(summoner, aram_matches)

        aram_embed = self.bot.embed(
            title=f"{summoner['name']} ARAM stats",
            description=f"Analysis of your last **{len(aram_matches)}** ARAM games!",
        )

        # Thumbnail of most played champ
        # Confusingly enough, this is just the first entry in the counter
        most_played_champ_id = aram_stats.most_played_champion_ids[0][0]
        champion_image_path = champion_id_to_image_path[most_played_champ_id]
        champion_image_path_full = get_cdragon_url(champion_image_path)
        aram_embed.set_thumbnail(url=champion_image_path_full)

        aram_embed.add_field(
            name="Most played champions",
            value=" • ".join(
                [
                    f"{champion_id_to_name[champ_id]} **{times_played}**"
                    for champ_id, times_played in aram_stats.most_played_champion_ids
                ]
            ),
            inline=False,
        )

        aram_embed.add_field(
            name="Duration",
            value=multiline_string(
                [
                    f"Total match duration **{humanize_seconds(aram_stats.total_game_duration)}**",
                    f"Total time dead **{humanize_seconds(aram_stats.total_time_spent_dead)}**",
                    f"Percentage spent dead **{aram_stats.total_time_dead_percentage}%** ",
                ]
            ),
            inline=False,
        )

        damage_healing_stats: list[tuple[str, int]] = [
            ("Damage dealt to champions", aram_stats.total_champion_damage),
            ("Damage taken", aram_stats.total_damage_taken),
            ("Damage dealt to objectives", aram_stats.total_objective_damage),
            ("Teammate healing", aram_stats.total_teammate_healing),
            ("Turret takedowns", aram_stats.total_turret_takedowns),
        ]
        aram_embed.add_field(
            name="Damage & Healing",
            value=multiline_string(
                [
                    f"**{format_big_number(stat_value)}** {stat_name}"
                    for stat_name, stat_value in damage_healing_stats
                ]
            ),
            inline=False,
        )

        aram_embed.add_field(
            name="Win & Losses",
            value=multiline_string(
                [
                    fstat("Wins", aram_stats.total_wins),
                    fstat("Losses", aram_stats.total_losses),
                    fstat("Win rate", f"{aram_stats.total_win_rate}%"),
                ]
            ),
        )

        aram_embed.add_field(
            name="KDA",
            value=multiline_string(
                [
                    fstat("Kill", aram_stats.total_kills, pluralize_name_auto=True),
                    fstat("Death", aram_stats.total_deaths, pluralize_name_auto=True),
                    fstat("Assist", aram_stats.total_assists, pluralize_name_auto=True),
                    fstat("Ratio", aram_stats.total_kda_ratio),
                ]
            ),
        )

        multi_kills = [
            ("Double Kill", aram_stats.total_double_kills),
            ("Triple Kill", aram_stats.total_triple_kills),
            ("Quadra Kill", aram_stats.total_quadra_kills),
            ("Penta Kill", aram_stats.total_penta_kills),
        ]
        aram_embed.add_field(
            name="Multi Kills",
            value=multiline_string(
                [
                    fstat(name, kill_amount, pluralize_name_auto=True)
                    for name, kill_amount in multi_kills
                    if kill_amount
                ]
                or "You didn't get a single multi kill 🤣",
            ),
        )

        end_time = time.perf_counter()
        loading_time = round(end_time - start_time, 2)
        aram_embed.set_footer(text=f"Elapsed loading time: {loading_time}s")
        await interaction.followup.send(embed=aram_embed)

    # todo goon rank leaderboard

    @app_commands.command(name="champion")
    async def champion_spells(self, interaction: discord.Interaction, champion_name: str):
        async with self.client_lock:
            async with self.cdragon_client as client:
                champions = await client.get_lol_v1_champion_summary()
                champion_id = get_champion_id_by_name(champion_name, champions)

            # If champion not found, stop the show
            if champion_id is None:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        title=f"Champion '{champion_name}' was not found",
                        description="Note: Common abbreviations like 'mf' are not yet support",
                        color=discord.Color.greyple(),
                    ),
                    ephemeral=True,
                )

            champion = await client.get_lol_v1_champion(id=champion_id)

        champion_embed = self.bot.embed(
            title=champion["name"],
            description=html_to_md(champion["shortBio"]),
        )

        champion_id_to_image_path = {champion["id"]: champion["squarePortraitPath"] for champion in champions}
        champion_embed.set_thumbnail(url=get_cdragon_url(champion_id_to_image_path[champion["id"]]))

        champion_embed.add_field(
            name=f"(Passive) {champion['passive']['name']}",
            value=html_to_md(champion["passive"]["description"]),
            inline=False,
        )

        for spell in champion["spells"]:
            champion_embed.add_field(
                name=f"({spell['spellKey'].upper()}) {spell['name']}",
                value=html_to_md(spell["description"]),
                inline=False,
            )

        await interaction.response.send_message(embed=champion_embed)


async def setup(bot):
    await bot.add_cog(League(bot))
