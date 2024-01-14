import asyncio
import time

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
from text_processing import html_to_md

from ._league.calculators import duration
from ._league.cdragon_builders import get_cdragon_url, make_profile_url
from ._league.cmd.aram import ARAMPerformanceParser
from ._league.cmd.champion import get_champion_id_by_name
from ._league.cmd.last_game import ArenaMatchParser, StandardMatchParser, get_all_queue_ids
from ._league.cmd.recent import RecentGamesParser
from ._league.cmd.summoner import league_entry_stats
from ._league.formatting import format_big_number
from ._league.lookups import discord_to_summoner_name, rank_reaction_strs

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
        champion_id_to_name = {champion["id"]: champion["name"] for champion in champions}

        # Determine queue type, replace with common name
        # ref: https://static.developer.riotgames.com/docs/lol/queues.json
        parser_type = StandardMatchParser
        match last_match["info"]["queueId"]:
            case 400:
                game_mode = "Draft Pick"
            case 420:
                game_mode = "Ranked Solo"
            case 490:
                game_mode = "Quickplay"
            case 440:
                game_mode = "Ranked Flex"
            case 450:
                game_mode = "ARAM"
            case 1700:
                game_mode = "Arena"
                parser_type = ArenaMatchParser
            case _ as not_set_queue_id:
                # Fallback that fetches the official game mode names
                all_queue_ids = await get_all_queue_ids()
                id_to_game_mode_name = {queue["queueId"]: queue["description"] for queue in all_queue_ids}
                if game_mode_name := id_to_game_mode_name[not_set_queue_id]:
                    game_mode = game_mode_name
                else:
                    game_mode = f"Unknown gamemode ({self.bot.ping_owner()})"

        if parser_type == ArenaMatchParser:
            parser = ArenaMatchParser(
                summoner,
                last_match,
                champion_id_to_image_path,
                champion_id_to_name,
            )
            last_match_embed = await parser.make_embed()
        else:  # if it doesn't use a special parser, we can assume it's the standard
            parser = StandardMatchParser(summoner, last_match, champion_id_to_image_path, game_mode)
            teammate_puuids = [name["puuid"] for name in parser.teammates]
            last_match_embed = parser.make_embed(await self.build_log_urls(teammate_puuids))

        end_time = time.perf_counter()
        loading_time = round(end_time - start_time, 2)
        last_match_embed.set_footer(text=f"Elapsed loading time: {loading_time}s")
        await interaction.followup.send(embed=last_match_embed)

    @app_commands.command(name="aram", description="An analysis of your last 50 ARAM games")
    @app_commands.autocomplete(summoner_name=summoner_name_autocomplete)
    async def aram_analysis(self, interaction: discord.Interaction, summoner_name: str | None):
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

        # Use Riot client to get a ton of matches
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

        # If user hasn't played any, stop the show
        if not aram_matches:
            return await interaction.followup.send(
                embed=self.bot.embed(
                    title="This account doesn't have any ARAM games played",
                    color=discord.Color.greyple(),
                )
            )

        # User CDragon client to champion data (for champion image, champ names)
        async with self.client_lock:
            async with self.cdragon_client as client:
                champions = await client.get_lol_v1_champion_summary()

        # Dict to get champ image paths
        champion_id_to_image_path = {champion["id"]: champion["squarePortraitPath"] for champion in champions}
        champion_id_to_name = {champion["id"]: champion["name"] for champion in champions}

        aram_stats = ARAMPerformanceParser(summoner, aram_matches)
        aram_embed = aram_stats.make_embed(champion_id_to_image_path, champion_id_to_name)

        end_time = time.perf_counter()
        loading_time = round(end_time - start_time, 2)
        aram_embed.set_footer(text=f"Elapsed loading time: {loading_time}s")
        await interaction.followup.send(embed=aram_embed)

    @app_commands.command(
        name="recent", description="An analysis of your recent games in a specific game mode"
    )
    @app_commands.autocomplete(summoner_name=summoner_name_autocomplete)
    @app_commands.choices(
        gamemode=[
            app_commands.Choice(name="Draft Pick", value=400),
            app_commands.Choice(name="Quickplay", value=490),
            app_commands.Choice(name="Ranked Solo/Duo", value=420),
            app_commands.Choice(name="Ranked Flex", value=470),
        ]
    )
    async def recent_games_analysis(
        self,
        interaction: discord.Interaction,
        summoner_name: str | None,
        gamemode: app_commands.Choice[int],
        match_count: app_commands.Range[int, 1, 50] = 20,
    ):
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

        # Use Riot client to get a ton of matches
        async with self.client_lock:
            async with self.riot_client as client:
                match_ids = await client.get_lol_match_v5_match_ids_by_puuid(
                    region="americas",
                    puuid=summoner["puuid"],
                    queries={"queue": gamemode.value, "count": match_count},
                )
                async with TaskGroup(asyncio.Semaphore(100)) as tg:
                    for match_id in match_ids:
                        await tg.create_task(client.get_lol_match_v5_match(region="americas", id=match_id))
                matches: list[RiotAPISchema.LolMatchV5Match] = tg.results()

        # If user hasn't played any, stop the show
        if not matches:
            return await interaction.followup.send(
                embed=self.bot.embed(
                    title=f"{summoner_name} doesn't have any {gamemode.name} games played",
                    color=discord.Color.greyple(),
                )
            )

        # User CDragon client to champion data (for champion image, champ names)
        async with self.client_lock:
            async with self.cdragon_client as client:
                champions = await client.get_lol_v1_champion_summary()

        # Dict to get champ image paths
        champion_id_to_image_path = {champion["id"]: champion["squarePortraitPath"] for champion in champions}
        champion_id_to_name = {champion["id"]: champion["name"] for champion in champions}

        last20_stats = RecentGamesParser(summoner, matches, gamemode.name)
        last20_embed = last20_stats.make_embed(champion_id_to_image_path, champion_id_to_name)

        end_time = time.perf_counter()
        loading_time = round(end_time - start_time, 2)
        last20_embed.set_footer(text=f"Elapsed loading time: {loading_time}s")
        await interaction.followup.send(embed=last20_embed)

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
