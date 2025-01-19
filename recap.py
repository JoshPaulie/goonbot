import datetime as dt
import sqlite3
from abc import ABC
from typing import Any, Sequence

# Goon server year in a review!

db_path = "gbdb.sqlite"

"""
The recap will consist of 2 parts: a server wide and one for each user

They'll share a lot of the same structure, but the user one will be filtered by user ID

Server recap:
- Top channel, reactions, chatters
- Day with most messages sent (and how many)
- Most popular command
- Most popular time of day for a message to be sent (windows of time)

User recap:
- Commands
    - Total commands used
    - Fav command, amount of times used
- Messages
    - Total messages sent
    - Which channel most popular
- Reactions
    - Total reactions sent
    - Favorite reactions
"""


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
    return messages_this_year / (days_this_year or 1)


def count_reactions(reactions: Sequence[ReactionRow]) -> dict[str, int]:
    reaction_counts = {}
    for reaction in reactions:
        if reaction.reactionStr not in reaction_counts:
            reaction_counts[reaction.reactionStr] = 0
        reaction_counts[reaction.reactionStr] += 1
    # Sort in decreasing order
    reaction_counts = dict(sorted(reaction_counts.items(), key=lambda item: item[1], reverse=True))
    return reaction_counts


def count_chatters(messages: Sequence[MessageRow]) -> dict[int, int]:
    chatters = {}
    for message in messages:
        if message.userID not in chatters:
            chatters[message.userID] = 0
        chatters[message.userID] += 1
    # Sort in decreasing order
    chatters = dict(sorted(chatters.items(), key=lambda item: item[1], reverse=True))
    return chatters


def count_commands(commands: Sequence[CommandRow]) -> dict[str, int]:
    command_counts = {}
    for command in commands:
        if command.commandName not in command_counts:
            command_counts[command.commandName] = 0
        command_counts[command.commandName] += 1
    # Sort in decreasing order
    command_counts = dict(sorted(command_counts.items(), key=lambda item: item[1], reverse=True))
    return command_counts


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

    # Top 5 reactions
    reaction_counts = count_reactions(reactions)
    print("Top 5 reactions:")
    for reaction, count in list(reaction_counts.items())[:5]:
        print(f"{reaction}: {count}")

    # Top 5 chatters
    chatters = count_chatters(messages)
    print("Top 5 chatters:")
    for chatter_id, count in list(chatters.items())[:5]:
        print(f"{chatter_id}: {count}")

    # Top 5 commands
    command_counts = count_commands(commands)
    print("Top 5 commands:")
    for command, count in list(command_counts.items())[:5]:
        print(f"{command}: {count}")


if __name__ == "__main__":
    print_recap()
