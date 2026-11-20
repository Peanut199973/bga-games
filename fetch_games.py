import csv
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BGG_TOKEN = "PASTE_YOUR_TOKEN_HERE"

HEADERS = {
    "Authorization": f"Bearer {BGG_TOKEN}",
    "User-Agent": "BGA-Game-Night-Personal-Script/1.0"
}

def search_bgg_id(game_name):
    query = urllib.parse.quote(game_name)
    url = f"https://boardgamegeek.com{query}&type=boardgame"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as response:
        xml_data = response.read()
    root = ET.fromstring(xml_data)
    items = root.findall("item")
    if not items:
        return None
    for item in items:
        name_el = item.find("name")
        if name_el is not None and name_el.attrib.get("value", "").lower() == game_name.lower():
            return item.attrib["id"]
    return items[0].attrib["id"]

def get_game_details(bgg_id):
    url = f"https://boardgamegeek.com{bgg_id}&stats=1"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as response:
        xml_data = response.read()
    root = ET.fromstring(xml_data)
    item = root.find("item")
    if item is None:
        return {}
    min_p = item.find("minplayers").attrib.get("value", "")
    max_p = item.find("maxplayers").attrib.get("value", "")
    min_t = item.find("minplaytime").attrib.get("value", "")
    max_t = item.find("maxplaytime").attrib.get("value", "")
    weight_el = item.find(".//averageweight")
    weight = round(float(weight_el.attrib.get("value", 0)), 2) if weight_el is not None else ""
    return {
        "min_players": min_p,
        "max_players": max_p,
        "min_minutes": min_t,
        "max_minutes": max_t,
        "complexity_1_to_5": weight
    }

def main():
    if BGG_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        print("Waiting for BGG token! Paste your token into fetch_games.py first.")
        return
    with open("games.txt", "r", encoding="utf-8") as f:
        games = [line.strip() for line in f if line.strip()]
    print(f"Found {len(games)} games in games.txt. Starting lookup...")
    with open("game_night_list.csv", "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["game", "min_players", "max_players", "min_minutes", "max_minutes", "complexity_1_to_5", "bgg_id"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for index, game in enumerate(games, start=1):
            print(f"[{index}/{len(games)}] Looking up: {game}...")
            try:
                bgg_id = search_bgg_id(game)
                if bgg_id:
                    time.sleep(1.5)
                    details = get_game_details(bgg_id)
                    writer.writerow({"game": game, "bgg_id": bgg_id, **details})
                else:
                    writer.writerow({"game": game, "bgg_id": "Not found"})
            except Exception as e:
                print(f"  Error on {game}: {e}")
                writer.writerow({"game": game, "bgg_id": f"Error: {e}"})
            time.sleep(1.5)
    print("Done! Open game_night_list.csv to see your results.")

if __name__ == "__main__":
    main()
