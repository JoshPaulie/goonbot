from typing import Optional

from text_processing import make_plural


def timestamp_from_seconds(duration_seconds: int) -> str:
    """Takes seconds and responds with a timestamp of the following format: 00:00

    Examples
        - 62 -> 01:02
    """
    minutes, remaining_seconds = divmod(duration_seconds, 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"


def fstat(
    name: str,
    value: str | int | float,
    make_name_plural: bool = False,
    extra_stat: Optional[str | int | float] = None,
) -> str:
    if make_name_plural:
        name = make_plural(name)

    if isinstance(value, int):
        value = f"{value:,d}"

    output = f"{name} **{value}**"
    if extra_stat:
        output += f" ({extra_stat})"

    return output


def format_big_number(num: int) -> str:
    if num >= 1_000_000:
        return str(round(num / 1_000_000, 1)) + "m"
    elif num >= 1_000:
        return str(round(num / 1_000, 1)) + "k"
    else:
        return str(round(num, 1))
