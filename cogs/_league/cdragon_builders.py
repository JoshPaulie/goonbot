def make_profile_url(profile_id: int) -> str:
    return f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/{profile_id}.jpg"


def get_cdragon_url(path: str) -> str:
    """ "Maps" paths according to the provided link. Some responses from pulsefire are incomplete and need to be
    mapped to its relative page on Community Dragon

    https://github.com/CommunityDragon/Docs/blob/master/assets.md#mapping-paths-from-json-files
    """
    base_cdragon_url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/"
    trimmed_path = path[len("/lol-game-data/assets") :]
    return base_cdragon_url + trimmed_path
