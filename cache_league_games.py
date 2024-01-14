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

# Cache, middleware, and client setup the same as it is within the bot
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


async def cache_match_history(summoner_name: str, count: int):
    """Fetches the match history of the given summoner. The depth is determined by the count parameter.
    Pulsefire client is configured to cache api calls"""
    # Output
    print(f"Fetching {summoner_name}'s last {count} matches...")
    # Start execution timer
    start_time = time.perf_counter()

    # Make API calls
    async with riot_client as client:
        # Get summoner details for puuid (player universal unique identity)
        summoner = await client.get_lol_summoner_v4_by_name(region="na1", name=summoner_name)
        # Get the match IDs for each of the matches, this can be done in 1 API call by specifying how many we want
        match_ids = await client.get_lol_match_v5_match_ids_by_puuid(
            region="americas",
            puuid=summoner["puuid"],
            queries={"start": 0, "count": count},
        )

        # Create a task for each match, concurrently ask riot for all of them.
        async with TaskGroup(asyncio.Semaphore(count)) as tg:
            for match_id in match_ids:
                await tg.create_task(client.get_lol_match_v5_match(region="americas", id=match_id))
        # After all of the tasks have compelted, store the results on the task group
        matches: list[RiotAPISchema.LolMatchV5Match] = tg.results()

    # Stats for output
    end_time = time.perf_counter()
    elapsed_time = round(end_time - start_time, 2)

    # Output
    print(f"Finished fetching {summoner_name}'s {len(matches)} matches. ({elapsed_time}s)")


async def main():
    # Get match count
    count = int(input("Enter match history depth: "))
    # Output stats
    print(f"Fetching last {count} matches for all goons...")
    start_time = time.perf_counter()

    # Get match history for each goon
    for summoner_name in discord_to_summoner_name.values():
        await cache_match_history(summoner_name, count)

    # Output stats
    end_time = time.perf_counter()
    elapsed_time = round(end_time - start_time, 2)
    # Output
    print(f"Finished fetching all goon matches. ({elapsed_time}s)")


if __name__ == "__main__":
    asyncio.run(main())
