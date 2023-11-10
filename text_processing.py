from typing import Any, Sequence


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


def multiline_string(lst: Sequence[str]) -> str:
    """Helper for writing multiline embed descriptions, field values, etc. easier to hardcode"""
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
