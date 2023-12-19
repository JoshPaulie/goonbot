def calc_winrate(wins: int, losses: int) -> str:
    total_games = wins + losses
    return f"{round((wins / total_games) * 100)}%"


def duration(*, months=0, weeks=0, days=0, hours=0, minutes=0, seconds=0):
    SECONDS_IN_MINUTE = 60
    SECONDS_IN_HOUR = SECONDS_IN_MINUTE * 60
    SECONDS_IN_DAY = 24 * SECONDS_IN_HOUR
    SECONDS_IN_WEEK = 7 * SECONDS_IN_DAY
    SECONDS_IN_MONTH = 30 * SECONDS_IN_DAY

    total_seconds = 0

    total_seconds += seconds
    total_seconds += minutes * SECONDS_IN_MINUTE
    total_seconds += hours * SECONDS_IN_HOUR
    total_seconds += days * SECONDS_IN_DAY
    total_seconds += weeks * SECONDS_IN_WEEK
    total_seconds += months * SECONDS_IN_MONTH

    return total_seconds
