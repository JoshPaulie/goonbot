import datetime
import math
from typing import Any, Sequence


def make_plural(noun: str) -> str:
    """VERY crude way of making nouns plural. Naive to English rules, simply adds an 's' to the end"""
    return noun + "s"


def make_possessive(noun: str) -> str:
    """
    Makes a noun possessive

    Examples
        - Jake -> Jake's
        - James -> James'
    """
    if noun.endswith("s"):
        return noun + "'"
    return noun + "'s"


def bullet_points(lst: Sequence[Any]) -> str:
    """Takes list of items, return bullet point version

    Example
        bullet_points("one two three".split())
        - one
        - two
        - three
    """
    return "\n".join([f"- {item}" for item in lst])


def join_lines(lst: Sequence[str]) -> str:
    """Helper for writing multiline embed descriptions, field values, etc. easier to hardcode

    Functionally the inverse of str.splitlines()"""
    return "\n".join(lst)


def comma_list(nouns: Sequence[str]) -> str:
    """Functionally similar to str.join(), but adds 'and' to the end to join the last item (oxford comma included 😉)

    Examples
        - comma_list(["One", "Two", "Three"]) -> "One, Two, and Three"
        - comma_list(["One", "Two"])          -> "One and Two"
        - comma_list(["One"])                 -> "One"
    """
    if len(nouns) <= 2:
        return " and ".join(nouns)
    *body, tail = nouns
    return f"{', '.join(body)}, and {tail}"


def time_ago(timestamp: int) -> str:
    dt = datetime.datetime.fromtimestamp(timestamp)
    now = datetime.datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    months, weeks = divmod(weeks, 4)
    years, months = divmod(months, 12)

    if years:
        if years == 1:
            return "over a year ago"
        return f"over {math.floor(years)} years ago"

    if months:
        if months == 1:
            return "about a month ago"
        return f"about {math.floor(months)} months ago"

    if weeks:
        if weeks == 1:
            return "about a week ago"
        return f"about {math.floor(weeks)} weeks ago"

    if days:
        if days == 1:
            return "yesterday"
        return f"about {math.floor(days)} months ago"

    if minutes:
        if minutes == 1:
            return "about a minute ago"
        return f"about {math.floor(minutes)} minutes ago"

    if seconds == 1:
        return "a second ago"
    return f"{math.floor(seconds)} seconds ago"


def html_to_md(text: str) -> str:
    mappings = {
        "<i>": "*",
        "</i>": "*",
        "<b>": "**",
        "</b>": "**",
        "<br>": "\n",
    }
    for html_token, md_token in mappings.items():
        text = text.replace(html_token, md_token)
    return text


def acronymize(input: str) -> str:
    return "".join([chars[0].upper() for chars in input.split()])
