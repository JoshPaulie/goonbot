from typing import Optional

from text_processing import make_plural


def timestamp_from_seconds(duration_seconds: int) -> str:
    """Takes seconds and responds with a timestamp of the following format: 00:00

    Examples
        - 62 -> 01:02
    """
    minutes, remaining_seconds = divmod(duration_seconds, 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"


def humanize_seconds(seconds: int) -> str:
    """
    Takes amount of seconds and returns a string in the following format

    - humanize_seconds(3600) -> "1 hour"
    - humanize_seconds(4530) -> "1 hour, 15 minutes"
    """
    hours, remainder = divmod(seconds, 60 * 60)
    minutes, _ = divmod(remainder, 60)

    time_units = [(hours, "hour"), (minutes, "minute")]
    output = [f"{value} {unit}" if value == 1 else f"{value} {unit}s" for value, unit in time_units if value]

    return ", ".join(output)


def fstat(
    name: str,
    value: str | int | float,
    *,
    pluralize_name_auto: bool = False,
    extra_stat: Optional[str | int | float] = None,
) -> str:
    """
    Format a stat name, value, and extra details with markdown, which helps increase readability.

    Examples:
        fstat("Kills", 10, "15%") -> "Kills **10** (15%)"
    """
    if pluralize_name_auto:
        if isinstance(value, (int, float)):
            if value > 1:
                name = make_plural(name)

    if isinstance(value, int):
        value = f"{value:,d}"

    output = f"{name} **{value}**"
    if extra_stat:
        output += f" ({extra_stat})"

    return output


def format_big_number(num: int) -> str:
    """Abbreviates large numbers with suffixes (ie. k & m)

    Examples
        format_big_number(1_456_925) -> "1.5m"
        format_big_number(8_324) -> "8.3k"
    """
    if num >= 1_000_000:
        return f"{num / 1_000_000:,.1f}m"
    elif num >= 1_000:
        return f"{num / 1_000:,.1f}k"
    else:
        return str(round(num, 1))
