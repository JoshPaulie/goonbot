import asyncio
import logging
import os
from enum import Enum, auto

from goonbot import goonbot

# Change the event loop policy if running the bot on Windows (one of two dev environments)
# Without this, the pytwitchapi library throws weird exceptions
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class EnvironmentType(Enum):
    production = auto()
    development = auto()


def main():
    log_handler = logging.FileHandler(filename="bot.log", encoding="utf-8", mode="a")
    # Check environment
    if os.environ.get("GOONBOT_ENV") == "PROD":
        token = goonbot.keys.PROD_DISCORD_API_TOKEN
        goonbot.environment = EnvironmentType.production
    else:
        token = goonbot.keys.DEV_DISCORD_API_TOKEN
        goonbot.environment = EnvironmentType.development
    # Start bot
    print("starting goonbot..")
    goonbot.run(token, log_handler=log_handler, root_logger=True)


if __name__ == "__main__":
    main()
