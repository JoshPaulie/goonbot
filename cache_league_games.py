"""
Used to cache many matches prior to the launch of Goonbot v6.
This is to be ran before launch day in the production environment, as it may take some time.
"""
import asyncio
import time

from pulsefire.caches import DiskCache
from pulsefire.clients import RiotAPIClient
from pulsefire.middlewares import (
    cache_middleware,
    http_error_middleware,
    json_response_middleware,
    rate_limiter_middleware,
)
from pulsefire.ratelimiters import RiotAPIRateLimiter
from pulsefire.schemas import RiotAPISchema
from pulsefire.taskgroups import TaskGroup

from cogs._league.calculators import duration
from cogs._league.lookups import discord_to_summoner_name
from keys import Keys

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

riot_client = RiotAPIClient(
    default_headers={"X-Riot-Token": Keys.RIOT_API},
    middlewares=[
        riot_cache_middleware,
        json_response_middleware(),
        http_error_middleware(),
        rate_limiter_middleware(RiotAPIRateLimiter()),
    ],
)


async def get_match_history(summoner_name: str, count: int):
    print(f"Fetching {summoner_name}'s last {count} matches...")
    start_time = time.perf_counter()
    async with riot_client as client:
        summoner = await client.get_lol_summoner_v4_by_name(region="na1", name=summoner_name)
        match_ids = await client.get_lol_match_v5_match_ids_by_puuid(
            region="americas",
            puuid=summoner["puuid"],
            queries={"start": 0, "count": 1},
        )

    async with TaskGroup(asyncio.Semaphore(100)) as tg:
        for match_id in match_ids:
            await tg.create_task(client.get_lol_match_v5_match(region="americas", id=match_id))
    matches: list[RiotAPISchema.LolMatchV5Match] = tg.results()

    end_time = time.perf_counter()
    elapsed_time = round(end_time - start_time, 2)
    print(f"Finished fetching {summoner_name}'s {len(matches)} matches. ({elapsed_time}s)")


async def main():
    count = 10
    print(f"Fetching last {count} matches for all goons...")
    start_time = time.perf_counter()
    summoner_names = list(discord_to_summoner_name.values())
    for summoner_name in summoner_names[:2]:
        await get_match_history(summoner_name, count)
    end_time = time.perf_counter()
    elapsed_time = round(end_time - start_time, 2)
    print(f"Finished fetching all goon matches. ({elapsed_time}s)")


if __name__ == "__main__":
    asyncio.run(main())
