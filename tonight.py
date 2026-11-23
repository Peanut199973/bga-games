import csv
import urllib.request

DATA_URL = "https://githubusercontent.com"

print("Downloading BGG dataset with player counts and playtimes...")
req = urllib.request.urlopen(DATA_URL)
lines = [line.decode("utf-8", errors="replace") for line in req.readlines()]
reader = csv.DictReader(lines, delimiter=";")

bgg_db = {}
for row in reader:
    name = row.get("Name", "").strip().lower()
    if name and name not in bgg_db:
        bgg_db[name] = row

with open("games.txt", "r", encoding="utf-8") as f:
    my_games = [line.strip() for line in f if line.strip()]

with open("game_night_tonight.csv", "w", newline="", encoding="utf-8") as out:
    writer = csv.writer(out)
    writer.writerow(["Game", "Min Players", "Max Players", "Playtime (Min)", "Complexity (1-5)", "BGG Rating"])
    for game in my_games:
        match = bgg_db.get(game.lower())
        if match:
            writer.writerow([
                game,
                match.get("Min Players", ""),
                match.get("Max Players", ""),
                match.get("Play Time", ""),
                match.get("Complexity Average", ""),
                match.get("Rating Average", "")
            ])
        else:
            writer.writerow([game, "Not found", "", "", "", ""])

print("Done! Saved game_night_tonight.csv")
