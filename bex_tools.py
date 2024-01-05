"""Collection of utility objects"""


import random
from typing import Any, Sequence


class CycleRandom:
    used_items = []

    def __init__(self, items: Sequence[Any]) -> None:
        self.items = items

    def __next__(self):
        if len(self.items) == len(self.used_items):
            self.used_items.clear()

        next_item = random.choice(self.items)
        self.used_items.append(next_item)
        return random.choice([i for i in self.items if i not in self.used_items])
