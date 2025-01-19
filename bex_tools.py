"""Collection of utility objects"""

import random
from itertools import batched
from typing import Any, Sequence


class CycleRandom:
    """
    Functionally similar to itertools.Cycle(), but shuffles the order each time it starts over.
    Oh, and without the memory benefits.

    > "Why does this exist?"
    Goonbot serves a lot of randomly picked content. If we used random.choice() to select this content,
    there's a high likelihood of being served repeat content, or back-to-back results.
    CycleRandom resolves this be randomly serving content, and keeping track of what it's already presented.
    No repeats are served until all content has been.

    > "Why is it a class and not a generator of some kind?"
    Some commands (namely /rat, /cat, & /real) allow for new data to be loaded while the bot is running.
    The related command for adding new images also add them into the "live mix", this way new images
    don't require a restart to be served.

    Example
    ```
    >>> next(CycleRandom([1, 2, 3, 4])) # 3 1 4 2 2 3 4 1 ...
    ```
    """

    def __init__(self, items: list[Any]) -> None:
        self.items = items
        self.used_items = []

    def __next__(self):
        if len(self.items) == len(self.used_items):
            self.used_items = []

        next_item = random.choice([i for i in self.items if i not in self.used_items])
        self.used_items.append(next_item)
        return next_item


def frontloaded_batched(items: Sequence, n: int) -> list[tuple[Any]]:
    """
    Functionally similar to itertools.batched, but instead of grouping front-to-back with remaining
    items being grouped at the end, make the odd-numbered group appear at the front.

    Example
    ```py
    items = list(range(1, 11))
    custom_batched(items, 4) -> [(1, 2), (3, 4, 5, 6), (7, 8, 9, 10)]
    ```
    """
    remaining_count = len(items) % n
    if not remaining_count:
        return list(batched(items, n))

    remaining_items = [tuple(items[:remaining_count])]
    items_without_remaining = items[remaining_count:]
    batch = list(batched(items_without_remaining, n))
    return remaining_items + batch
