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


def join_lines(lst: Sequence[str]) -> str:
    """Helper for writing multiline embed descriptions, field values, etc. easier to hardcode

    Functionally the inverse of str.splitlines()"""
    return "\n".join(lst)


def bullet_points(lst: Sequence[Any], numerical: bool = False) -> str:
    """Takes list of items, return bullet point version

    Example
        bullet_points("one two three".split())
        - one
        - two
        - three
    """
    if numerical:
        return join_lines([f"{indx + 1}. {item}" for indx, item in enumerate(lst)])
    return join_lines([f"- {item}" for item in lst])


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


def md_codeblock(text: str, language: str | None = "") -> str:
    """Wrap text in backticks for markdown codeblocks"""
    return f"```{language}\n{text}\n```"


def html_to_md(text: str) -> str:
    """Incredibly crude way of converting HTML tags to MD tags"""

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
    """
    Create an acronym for any given sentence.
    Done by splitting the sentence by white space, keeping only the capitalized first character of each word.

    'This is a dumb bit' -> 'TIADB'
    """
    return "".join([chars[0].upper() for chars in input.split()])
