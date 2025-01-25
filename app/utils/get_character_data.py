import requests


def get_character_info(name):
    return [
        {"job": 0, "level": 200},
        {"job": 2, "level": 190},
        {"job": 0, "level": 180},
    ]


def get_character_card_data(name):
    response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{name}")
    name = response.json()["name"]
    url = f"https://starlightskins.lunareclipse.studio/render/default/{name}/full?renderScale=3.2"

    return name, url
