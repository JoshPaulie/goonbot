def calc_winrate(wins: int, losses: int) -> str:
    total_games = wins + losses
    return f"{round((wins / total_games) * 100)}%"
