import json

import aiohttp

from ..annotations import GameMode


async def get_all_queue_ids() -> list[GameMode]:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://static.developer.riotgames.com/docs/lol/queues.json") as response:
            response_text = await response.text()
            response_json: list[GameMode] = json.loads(response_text)
    return response_json
