import logging
import os

from goonbot import goonbot

DISCORD_TOKEN = "GOONBOT_TOKEN"


def main():
    handler = logging.FileHandler(filename="bot.log", encoding="utf-8", mode="a")
    if token := os.environ.get(DISCORD_TOKEN):
        print("starting bot..")
        goonbot.run(token, log_handler=handler, root_logger=True)
        return
    print(f"no discord bot token for set in the environment variable: {DISCORD_TOKEN}")


if __name__ == "__main__":
    main()
