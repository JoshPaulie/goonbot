import datetime as dt
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Sequence

# Goon server year in a review!

db_path = "gbdb.sqlite"


class Row(ABC):

    def __init__(self, id: str, userID: int, timestamp: str):
        self.id = id
        self.userID = userID
        self.timestamp = dt.datetime.fromisoformat(timestamp)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, userID={self.userID}, timestamp={self.timestamp})"


class MessageRow(Row):
    def __init__(self, id: str, userID: int, messageID: int, channelID: int, timestamp: str):
        super().__init__(id, userID, timestamp)
        self.messageID = messageID
        self.channelID = channelID


class ReactionRow(Row):
    def __init__(self, id: str, userID: int, reactionStr: str, messageID: int, timestamp: str):
        super().__init__(id, userID, timestamp)
        self.reactionStr = reactionStr
        self.messageID = messageID


class CommandRow(Row):
    def __init__(self, id: str, userID: int, commandName: str, timestamp: str):
        super().__init__(id, userID, timestamp)
        self.commandName = commandName


def get_all_rows_from_table(table: str) -> list[Any]:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        return cursor.fetchall()


def get_commands() -> list[CommandRow]:
    command_rows = get_all_rows_from_table("command")
    return [CommandRow(*row) for row in command_rows]


def get_messages() -> list[MessageRow]:
    message_rows = get_all_rows_from_table("message")
    return [MessageRow(*row) for row in message_rows]


def get_reactions() -> list[ReactionRow]:
    reaction_rows = get_all_rows_from_table("reaction")
    return [ReactionRow(*row) for row in reaction_rows]


# Filters


def filter_rows_this_year_only(rows: Sequence[Row]):
    return [row for row in rows if row.timestamp.year == dt.datetime.now().year]


def filter_rows_by_user_id(rows: Sequence[Row], user_id: int):
    return [row for row in rows if row.userID == user_id]


# Fun stuff
def get_messages_per_day(messages: Sequence[MessageRow]) -> dict[dt.date, int]:
    messages_per_day = {}
    for message in messages:
        date = message.timestamp.date()
        if date not in messages_per_day:
            messages_per_day[date] = 0
        messages_per_day[date] += 1
    return messages_per_day


def avergage_messages_per_day(messages: Sequence[MessageRow]):
    messages_this_year = len(filter_rows_this_year_only(messages))
    if messages_this_year == 0:
        return 0
    days_this_year = (dt.datetime.now() - dt.datetime(dt.datetime.now().year, 1, 1)).days
    return messages_this_year / days_this_year


def print_recap():
    commands = get_commands()
    messages = get_messages()
    reactions = get_reactions()

    commands_this_year = filter_rows_this_year_only(commands)
    messages_this_year = filter_rows_this_year_only(messages)
    reactions_this_year = filter_rows_this_year_only(reactions)

    print("Commands this year:", len(commands_this_year))
    print("Messages this year:", len(messages_this_year))
    print("Messages per day this year:", round(avergage_messages_per_day(messages), 2))

    # print("Reactions this year:")
    # for reaction in reactions_this_year:
    #     print(reaction)


if __name__ == "__main__":
    print_recap()
