from pulsefire.clients import CDragonSchema


def get_champion_id_by_name(
    champion_name: str, champion_pool: list[CDragonSchema.LolV1ChampionInfo]
) -> int | None:
    champ_name_to_id = {champion["name"]: champion["id"] for champion in champion_pool}
    for champ in champ_name_to_id.keys():
        if champion_name.lower() in champ.lower():
            return champ_name_to_id[champ]
    return None
