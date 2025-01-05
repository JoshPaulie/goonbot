"""Collection of utility objects"""

import random
from typing import Any


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

    used_items = []

    def __init__(self, items: list[Any]) -> None:
        self.items = items

    def __next__(self):
        if len(self.items) == len(self.used_items):
            self.used_items.clear()

        next_item = random.choice([i for i in self.items if i not in self.used_items])
        self.used_items.append(next_item)
        return next_item
