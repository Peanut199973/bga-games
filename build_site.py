import json, os, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

TOKEN = os.environ.get("BGG_TOKEN", "").strip()
HDR = {"Authorization": f"Bearer {TOKEN}", "User-Agent": "BGA-Hub/1.0"}

def fetch(url):
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=15) as r:
        return ET.fromstring(r.read())

def lookup(name):
    q = urllib.parse.quote(name)
    items = fetch(f"https://boardgamegeek.com{q}&type=boardgame").findall("item")
    if not items: return None
    bid = next((i.attrib["id"] for i in items if i.find("name").attrib.get("value","").lower() == name.lower()), items[0].attrib["id"])
    time.sleep(1.5)
    it = fetch(f"https://boardgamegeek.com{bid}&stats=1").find("item")
    if it is None: return None
    mn, mx = int(it.find("minplayers").attrib.get("value",1) or 1), int(it.find("maxplayers").attrib.get("value",4) or 4)
    tm = int(it.find("playingtime").attrib.get("value",30) or 30)
    wt = round(float(it.find(".//averageweight").attrib.get("value",1.5) or 1.5), 2)
    rt = round(float(it.find(".//average").attrib.get("value",0) or 0), 1)
    th = (it.find("thumbnail").text or "").strip() if it.find("thumbnail") is not None else ""
    tags = ", ".join([l.attrib["value"] for l in it.findall("link[@type='boardgamecategory']")[:2] + it.findall("link[@type='boardgamemechanic']")[:2]])
    return {"name": name, "bgg_id": bid, "min": mn, "max": mx, "best": f"{mn}-{mx}", "time": tm, "weight": wt, "rating": rt, "thumb": th, "tags": tags}

cache = {g["name"].lower(): g for g in json.load(open("games_data.json"))} if os.path.exists("games_data.json") else {}
games = []
for n in [l.strip() for l in open("games.txt") if l.strip()]:
    if n.lower() in cache and cache[n.lower()].get("bgg_id"):
        games.append(cache[n.lower()])
    else:
        try: games.append(lookup(n) or {"name": n, "min": 2, "max": 4, "best": "2-4", "time": 30, "weight": 1.5, "tags": "Unmatched"})
        except Exception: games.append({"name": n, "min": 2, "max": 4, "best": "2-4", "time": 30, "weight": 1.5, "tags": "Pending"})
        time.sleep(1.5)

json.dump(games, open("games_data.json", "w"), indent=2)
open("index.html", "w").write(open("template.html").read().replace("__GAMES_JSON__", json.dumps(games)))
