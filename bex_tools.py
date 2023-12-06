"""Collection of utility objects"""


import random
from typing import Any, Sequence


def cycle_random(items: Sequence[Any]):
    """
    Generates an infinite sequence of items from the given sequence, ensuring that each item is yielded before repeating any.
    The order of the items is randomized each time the sequence cycles.

    Functionally similar to itertools.cycle(), but (effectively) shuffles the order each time.
    """
    used_items = []
    while True:
        if len(used_items) == len(items):
            used_items = []
        chosen_item = random.choice([i for i in items if i not in used_items])
        used_items.append(chosen_item)
        yield chosen_item
