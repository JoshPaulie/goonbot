import datetime as dt
from operator import itemgetter

# Constants
today = dt.date.today()
current_year = today.year

# Events
BIRTHDAYS = {
    "Hudson": dt.date(current_year, 2, 14),
    "Chris": dt.date(current_year, 4, 21),
    "Alex": dt.date(current_year, 4, 15),
    # 💔
    # "Daniel": dt.date(current_year, 4, 3),
    # "Lex": dt.date(current_year, 5, 20),
    "Justin": dt.date(current_year, 6, 12),
    "Josh": dt.date(current_year, 6, 27),
    "Matt": dt.date(current_year, 9, 24),
    "Hobo": dt.date(current_year, 9, 11),
    "Conrad": dt.date(current_year, 10, 2),
    "Vynle": dt.date(current_year, 5, 9),
}
BIRTHDAYS = {
    f"""{goon}{"'" if goon[-1] == "s" else "'s"} birthday""" + " 🧁": date for goon, date in BIRTHDAYS.items()
}

HOLIDAYS = {
    "Valentine's Day 💕": dt.date(current_year, 2, 14),
    "Freedom Day 🎇": dt.date(current_year, 7, 6),
    "Thanksgiving 🦃": dt.date(current_year, 11, 24),
    "Christmas 🎄": dt.date(current_year, 12, 25),
    "New Year's Eve 🥳": dt.date(current_year, 12, 31),
}

CALENDAR_EVENTS = {**BIRTHDAYS, **HOLIDAYS}
SORTED_CALENDAR_EVENTS = dict(sorted(CALENDAR_EVENTS.items(), key=itemgetter(1)))
