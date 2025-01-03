"""Collection of utility objects"""


import random
from typing import Any


class CycleRandom:
    """
    Functionally similar to itertools.Cycle(), but it shuffles the order each time it starts over.
    Oh, and without the memory benefits.

    > "Why does this exist?"
    This pseudo-generator is serves all of the random content behind many commands and features.
    As of now, all but one of these in use need to ability to add new items into the cycle with disrupting it

    Example
    ```
    CycleRandom([1, 2, 3]) -> 3 1 2 2 3 1 ...
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
