"""
Many helpers to support the seemingly simple calendar commands
"""
import datetime as dt
from operator import itemgetter


def get_events_dict(today: dt.date) -> dict[str, dt.date]:
    current_year = today.year
    BIRTHDAYS = {
        "Hudson": dt.date(current_year, 2, 14),
        "Chris": dt.date(current_year, 4, 21),
        "Alex": dt.date(current_year, 4, 15),
        "Vynle": dt.date(current_year, 5, 9),
        "Justin": dt.date(current_year, 6, 12),
        "Josh": dt.date(current_year, 6, 27),
        "Matt": dt.date(current_year, 9, 24),
        "Hobo": dt.date(current_year, 9, 11),
        "Conrad": dt.date(current_year, 10, 2),
    }
    BIRTHDAYS = {
        f"""{goon}{"'" if goon[-1] == "s" else "'s"} birthday""" + " 🧁": date
        for goon, date in BIRTHDAYS.items()
    }

    HOLIDAYS = {
        "Valentine's Day 💕": dt.date(current_year, 2, 14),
        "Freedom Day 🎇": dt.date(current_year, 7, 6),
        "Thanksgiving 🦃": dt.date(current_year, 11, 24),
        "Christmas 🎄": dt.date(current_year, 12, 25),
        "New Year's Eve 🥳": dt.date(current_year, 12, 31),
    }

    # Combine
    CALENDAR_EVENTS = {**BIRTHDAYS, **HOLIDAYS}
    # Sort by date
    SORTED_CALENDAR_EVENTS = dict(sorted(CALENDAR_EVENTS.items(), key=itemgetter(1)))
    return SORTED_CALENDAR_EVENTS


class SpecialEvent:
    def __init__(self, today: dt.date, name: str, date: dt.date) -> None:
        self.today = today
        self.name = name
        self.date = date

    @property
    def is_today(self):
        return self.today == self.date

    @property
    def days_until(self):
        return (self.date - self.today).days


def get_events(today: dt.date, remaining_only: bool):
    events = [
        SpecialEvent(today, event_name, event_date)
        for event_name, event_date in get_events_dict(today).items()
    ]
    if remaining_only:
        return [e for e in events if e.days_until > -1]
    return events


# Birthday graveyard 💔
# "Daniel": dt.date(current_year, 4, 3),
# "Lex": dt.date(current_year, 5, 20),
