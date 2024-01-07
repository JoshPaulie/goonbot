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
from text_processing import html_to_md, join_lines, make_possessive, time_ago

from ._league.calculators import duration
from ._league.cdragon_builders import get_cdragon_url, make_profile_url
from ._league.cmd.aram import ARAMPerformanceParser
from ._league.cmd.champion import get_champion_id_by_name
from ._league.cmd.last_game import ArenaMatchParser, StandardMatchParser, get_all_queue_ids
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

    async def get_summoner(self, summoner_name: str) -> RiotAPISchema.LolSummonerV4Summoner | None:
        async with self.client_lock:
            async with self.riot_client as client:
                try:
                    return await client.get_lol_summoner_v4_by_name(region=REGION_NA1, name=summoner_name)
                except ClientResponseError:
                    return None

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

        # Incase it takes longer than 3 seconds to respond, we defer the response and followup later
        await interaction.response.defer()

        # Get summoner data
        summoner = await self.get_summoner(summoner_name)
        if not summoner:
            return await interaction.response.send_message(
                embed=self.bot.embed(
                    title=f"Summoner '{summoner_name}' not found",
                    color=discord.Color.brand_red(),
                )
            )

        # Get data relevant to this command
        async with self.client_lock:
            async with self.riot_client as client:
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

        # Incase it takes longer than 3 seconds to respond, we defer the response and followup later
        await interaction.response.defer()

        # Get summoner data
        summoner = await self.get_summoner(summoner_name)
        if not summoner:
            return await interaction.response.send_message(
                embed=self.bot.embed(
                    title=f"Summoner '{summoner_name}' not found",
                    color=discord.Color.brand_red(),
                )
            )

        # Start timer for response time
        start_time = time.perf_counter()

        # Get summoner, their match ids, and their last match
        async with self.client_lock:
            async with self.riot_client as client:
                # Get ID of most recent match
                last_match_id = (
                    await client.get_lol_match_v5_match_ids_by_puuid(
                        region="americas",
                        puuid=summoner["puuid"],
                        queries={"start": 0, "count": 1},
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

        # Determine queue type, replace with common name
        # ref: https://static.developer.riotgames.com/docs/lol/queues.json
        match last_match["info"]["queueId"]:
            case 400:
                game_mode = "Draft Pick"
                parser = StandardMatchParser(summoner, last_match, champion_id_to_image_path, game_mode)
            case 420:
                game_mode = "Ranked Solo"
                parser = StandardMatchParser(summoner, last_match, champion_id_to_image_path, game_mode)
            case 430:
                game_mode = "Blind Pick"
                parser = StandardMatchParser(summoner, last_match, champion_id_to_image_path, game_mode)
            case 440:
                game_mode = "Ranked Flex"
                parser = StandardMatchParser(summoner, last_match, champion_id_to_image_path, game_mode)
            case 450:
                game_mode = "ARAM"
                parser = StandardMatchParser(summoner, last_match, champion_id_to_image_path, game_mode)
            case 1700:
                # Send a completely different embed if game mode is Arena
                parser = ArenaMatchParser(summoner, last_match)
            case _ as not_set_queue_id:
                # Fallback that fetches the official game mode names
                all_queue_ids = await get_all_queue_ids()
                id_to_game_mode_name = {queue["queueId"]: queue["description"] for queue in all_queue_ids}
                if game_mode_name := id_to_game_mode_name[not_set_queue_id]:
                    game_mode = game_mode_name
                else:
                    game_mode = f"Unknown gamemode ({self.bot.ping_owner()})"
                parser = StandardMatchParser(summoner, last_match, champion_id_to_image_path, game_mode)

        end_time = time.perf_counter()
        loading_time = end_time - start_time
        if isinstance(parser, ArenaMatchParser):
            last_match_embed = await parser.make_embed()
        else:  # if it doesn't user a special parser, we can assume it's the standard
            teammate_names = [name["summonerName"] for name in parser.teammates]
            last_match_embed = parser.make_embed(await self.build_log_urls(teammate_names))

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

        # Incase it takes longer than 3 seconds to respond, we defer the response and followup later
        await interaction.response.defer()

        # Get summoner data
        summoner = await self.get_summoner(summoner_name)
        if not summoner:
            return await interaction.response.send_message(
                embed=self.bot.embed(
                    title=f"Summoner '{summoner_name}' not found",
                    color=discord.Color.brand_red(),
                )
            )

        async with self.client_lock:
            async with self.riot_client as client:
                # Get last 50 ARAM games (queue id 450)
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
            value=join_lines(
                [
                    f"Total match duration **{humanize_seconds(aram_stats.total_game_duration)}**",
                    f"Total time dead **{humanize_seconds(aram_stats.total_time_spent_dead)}**",
                    f"Percentage spent dead **{aram_stats.total_time_dead_percentage}%** ",
                    f"CC dealt **{humanize_seconds(aram_stats.total_cc_dealt)}**",
                ]
            ),
            inline=False,
        )

        damage_healing_stats: list[tuple[str, int]] = [
            ("Damage dealt to champions", aram_stats.total_champion_damage),
            ("Damage taken", aram_stats.total_damage_taken),
            ("Damage dealt to objectives", aram_stats.total_objective_damage),
            ("Teammate healing", aram_stats.total_teammate_healing),
        ]
        damage_healing_stats_formatted = [
            fstat(stat_name, format_big_number(stat_value)) for stat_name, stat_value in damage_healing_stats
        ]
        damage_healing_stats_formatted_batched = batched(damage_healing_stats_formatted, 2)
        aram_embed.add_field(
            name="Damage & Healing",
            value=join_lines([" · ".join(pair) for pair in damage_healing_stats_formatted_batched]),
            inline=False,
        )

        resource_gathering_stats: list[tuple[str, int]] = [
            ("Gold earned", aram_stats.total_gold_earned),
            ("Minions Killed", aram_stats.total_minions_killed),
            ("Turret takedowns", aram_stats.total_turret_takedowns),
            ("Inhibitor takedowns", aram_stats.total_inhibitor_takedowns),
        ]
        resource_gathering_stats_formated: list[str] = [
            fstat(stat_name, stat_value) for stat_name, stat_value in resource_gathering_stats
        ]
        resource_gathering_stats_batched = batched(resource_gathering_stats_formated, 2)
        aram_embed.add_field(
            name="Resource Gathering",
            value=join_lines([" · ".join(pair) for pair in resource_gathering_stats_batched]),
            inline=False,
        )

        aram_embed.add_field(
            name="Win & Losses",
            value=join_lines(
                [
                    fstat("Wins", aram_stats.total_wins),
                    fstat("Losses", aram_stats.total_losses),
                    fstat("Win rate", f"{aram_stats.total_win_rate}%"),
                ]
            ),
        )

        aram_embed.add_field(
            name="KDA",
            value=join_lines(
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
            value=join_lines(
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
