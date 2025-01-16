from typing import Literal, Sequence

import requests

from keys import Keys

tags = Literal[
    "+1",
    "partying_face",
    "tada",
    "heavy_check_mark",
    "loudspeaker",
    "-1",
    "warning",
    "rotating_light",
    "triangular_flag_on_post",
    "skull",
    "facepalm",
    "no_entry",
    "no_entry_sign",
    "cd",
    "computer",
    "white_check_mark",
]


def send_ntfy(
    *,
    title: str,
    message: str,
    tags: Sequence[tags] | None = None,
    priority: int = 0,
) -> requests.Response:
    """
    Simple function to send push notifications through ntfy.sh. The topic is private, & hopefully
    never compromised. That would be annoying.

    Docs: https://docs.ntfy.sh/publish/#message-title
    """

    headers = {
        "Title": title,
    }

    if priority:
        headers["Priority"] = str(priority)

    if tags:
        headers["Tags"] = ",".join(tags)

    return requests.post(
        f"https://ntfy.sh/{Keys.NTFY_TOPIC}",
        data=message,
        headers=headers,
    )


response = send_ntfy(
    title="Database limit met",
    message="The database has exceeded 90% capacity",
    tags=["warning", "white_check_mark"],
    priority=5,
)
