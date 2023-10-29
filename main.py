import os

from goonbot import goonbot
from log_handling import handler

DISCORD_TOKEN = "GOONBOT_TOKEN"


def main():
    if token := os.environ.get(DISCORD_TOKEN):
        print("starting bot..")
        goonbot.run(token, log_handler=handler, root_logger=True)
        return
    print(f"no discord bot token for set in the environment variable: {DISCORD_TOKEN}")


if __name__ == "__main__":
    main()
