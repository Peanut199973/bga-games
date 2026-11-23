import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BGG_TOKEN = os.environ.get("BGG_TOKEN", "").strip()

HEADERS = {
    "Authorization": f"Bearer {BGG_TOKEN}",
    "User-Agent": "BGA-Game-Night-Builder/1.0"
}

def search_bgg_id(game_name):
    query = urllib.parse.quote(game_name)
    url = f"https://boardgamegeek.com{query}&type=boardgame"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        root = ET.fromstring(resp.read())
    items = root.findall("item")
    if not items:
        return None
    for item in items:
        name_el = item.find("name")
        if name_el is not None and name_el.attrib.get("value", "").lower() == game_name.lower():
            return item.attrib["id"]
    return items[0].attrib["id"]

def fetch_bgg_details(bgg_id):
    url = f"https://boardgamegeek.com{bgg_id}&stats=1"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        root = ET.fromstring(resp.read())
    item = root.find("item")
    if item is None:
        return None

    min_p = int(item.find("minplayers").attrib.get("value", 1) or 1)
    max_p = int(item.find("maxplayers").attrib.get("value", 4) or 4)
    playtime = int(item.find("playingtime").attrib.get("value", 30) or 30)
    weight_el = item.find(".//averageweight")
    weight = round(float(weight_el.attrib.get("value", 1.5) or 1.5), 2)
    rating_el = item.find(".//average")
    rating = round(float(rating_el.attrib.get("value", 0) or 0), 1)
    thumb_el = item.find("thumbnail")
    thumb = thumb_el.text.strip() if thumb_el is not None and thumb_el.text else ""

    # Determine community best player count
    best_players = f"{min_p}-{max_p}" if min_p != max_p else str(min_p)
    best_votes = 0
    for res in item.findall(".//poll[@name='suggested_numplayers']/results"):
        num = res.attrib.get("numplayers", "")
        best_el = res.find("result[@value='Best']")
        votes = int(best_el.attrib.get("numvotes", 0)) if best_el is not None else 0
        if votes > best_votes:
            best_votes = votes
            best_players = num

    mechanics = [
        link.attrib.get("value", "")
        for link in item.findall("link[@type='boardgamemechanic']")
    ][:3]
    categories = [
        link.attrib.get("value", "")
        for link in item.findall("link[@type='boardgamecategory']")
    ][:2]
    tags = ", ".join(categories + mechanics) or "Board Game"

    return {
        "bgg_id": bgg_id,
        "min": min_p,
        "max": max_p,
        "best": best_players,
        "time": playtime,
        "weight": weight,
        "rating": rating,
        "thumb": thumb,
        "tags": tags
    }

def main():
    if not BGG_TOKEN:
        raise RuntimeError("Missing BGG_TOKEN environment variable.")

    # Load existing cache so we don't re-fetch games we already have
    cache = {}
    if os.path.exists("games_data.json"):
        with open("games_data.json", "r", encoding="utf-8") as f:
            for entry in json.load(f):
                cache[entry["name"].lower()] = entry

    with open("games.txt", "r", encoding="utf-8") as f:
        game_names = [line.strip() for line in f if line.strip()]

    updated_games = []
    for idx, name in enumerate(game_names, 1):
        key = name.lower()
        if key in cache and cache[key].get("bgg_id"):
            updated_games.append(cache[key])
            continue

        print(f"[{idx}/{len(game_names)}] Fetching BGG data for: {name}")
        try:
            bgg_id = search_bgg_id(name)
            time.sleep(1.5)
            details = fetch_bgg_details(bgg_id) if bgg_id else None
            if details:
                updated_games.append({"name": name, **details})
            else:
                updated_games.append({
                    "name": name, "bgg_id": "", "min": 2, "max": 4,
                    "best": "2-4", "time": 30, "weight": 1.5,
                    "rating": 0, "thumb": "", "tags": "Unmatched on BGG"
                })
        except Exception as e:
            print(f"  Error on {name}: {e}")
            updated_games.append({
                "name": name, "bgg_id": "", "min": 2, "max": 4,
                "best": "2-4", "time": 30, "weight": 1.5,
                "rating": 0, "thumb": "", "tags": "Lookup pending"
            })
        time.sleep(1.5)

    with open("games_data.json", "w", encoding="utf-8") as f:
        json.dump(updated_games, f, indent=2, ensure_ascii=False)

    build_html(updated_games)
    print(f"Successfully built index.html with {len(updated_games)} games!")

def build_html(games):
    games_json = json.dumps(games, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BGA Game Night Hub</title>
<style>
  :root {{ --bg: #0f172a; --card: #1e293b; --accent: #38bdf8; --text: #f8fafc; --muted: #94a3b8; --border: #334155; }}
  * {{ box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  body {{ margin: 0; background: var(--bg); color: var(--text); padding: 16px; max-width: 1100px; margin: 0 auto; }}
  header {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 16px; }}
  h1 {{ margin: 0; font-size: 1.5rem; }}
  .btn {{ background: var(--card); color: var(--text); border: 1px solid var(--border); padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.9rem; }}
  .btn-primary {{ background: var(--accent); color: #0f172a; border: none; }}
  .controls {{ background: var(--card); padding: 14px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 16px; display: grid; gap: 12px; }}
  .row {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
  input, select, textarea {{ background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 8px 12px; border-radius: 8px; font-size: 0.95rem; }}
  input[type="text"] {{ flex: 1; min-width: 200px; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .chip {{ background: var(--bg); border: 1px solid var(--border); color: var(--muted); padding: 6px 12px; border-radius: 999px; cursor: pointer; font-size: 0.85rem; }}
  .chip.active {{ background: var(--accent); color: #0f172a; border-color: var(--accent); font-weight: 700; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; cursor: pointer; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.1s; }}
  .card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
  .card-top {{ display: flex; gap: 10px; align-items: flex-start; }}
  .thumb {{ width: 52px; height: 52px; border-radius: 8px; object-fit: cover; background: var(--bg); flex-shrink: 0; }}
  .title {{ font-weight: 700; font-size: 1.05rem; margin: 0 0 4px 0; }}
  .meta {{ color: var(--muted); font-size: 0.85rem; }}
  .tags {{ margin-top: 10px; font-size: 0.78rem; color: var(--accent); }}
  dialog {{ background: var(--card); color: var(--text); border: 1px solid var(--border); border-radius: 14px; padding: 20px; max-width: 480px; width: 92%; }}
  dialog::backdrop {{ background: rgba(0,0,0,0.7); }}
  .elo-row {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); }}
</style>
</head>
<body>
<header>
  <div>
    <h1>🎲 BGA Game Night Hub</h1>
    <div class="meta" id="countLabel">Loading games...</div>
  </div>
  <div class="row">
    <button class="btn" onclick="openAddGame()">+ Add Game</button>
    <button class="btn" onclick="openSyncModal()">🔄 Sync BGA ELOs</button>
    <button class="btn" onclick="openCrewModal()">👥 Crew</button>
    <button class="btn btn-primary" onclick="pickRandom()">🎲 Random Pick</button>
  </div>
</header>

<div class="controls">
  <div class="row">
    <input type="text" id="searchInput" placeholder="Search game name or mechanic..." oninput="render()">
    <select id="playerFilter" onchange="render()">
      <option value="0">Any Players</option>
      <option value="1">1 Player</option>
      <option value="2">2 Players</option>
      <option value="3">3 Players</option>
      <option value="4">4 Players</option>
      <option value="5">5 Players</option>
      <option value="6">6+ Players</option>
    </select>
    <select id="timeFilter" onchange="render()">
      <option value="999">Any Time</option>
      <option value="20">≤ 20 mins</option>
      <option value="30">≤ 30 mins</option>
      <option value="45">≤ 45 mins</option>
      <option value="60">≤ 60 mins</option>
    </select>
    <select id="weightFilter" onchange="render()">
      <option value="5">Any Complexity</option>
      <option value="1.5">Light (≤ 1.5)</option>
      <option value="2.2">Medium-Light (≤ 2.2)</option>
      <option value="3.0">Medium (≤ 3.0)</option>
    </select>
  </div>
  <div class="chips" id="quickChips">
    <span class="chip" onclick="toggleChip(this, '2p')">2 Players</span>
    <span class="chip" onclick="toggleChip(this, '4p')">4 Players</span>
    <span class="chip" onclick="toggleChip(this, 'fast')">⚡ ≤ 20m</span>
    <span class="chip" onclick="toggleChip(this, 'light')">🪶 Light</span>
    <span class="chip" onclick="toggleChip(this, 'coop')">🤝 Cooperative</span>
  </div>
</div>

<div class="grid" id="gameGrid"></div>

<dialog id="gameModal">
  <h2 id="modalTitle" style="margin-top:0"></h2>
  <p class="meta" id="modalMeta"></p>
  <h3>🏆 Crew ELO & Stats</h3>
  <div id="eloList"></div>
