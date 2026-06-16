#!/usr/bin/env python3
"""Fetch World Cup 2026 matches from football-data.org and save to scores.json"""
import json, os, urllib.request
from collections import defaultdict

TEAM_MAP = {"Cape Verde Islands": "Cape Verde", "Bosnia-Herzegovina": "Bosnia", "Congo DR": "Congo", "United States": "USA", "Curaçao": "Curacao", "Czech Republic": "Czechia"}

POT_A = ["Uruguay","Mexico","Belgium","Argentina","Portugal","France","Morocco","England","Senegal","Colombia","Croatia","Germany","USA","Spain","Brazil","Netherlands"]
POT_B = ["Ecuador","Panama","Norway","Iran","Japan","Algeria","Paraguay","Turkey","Sweden","Austria","South Korea","Canada","Switzerland","Ivory Coast","Australia","Egypt"]
POT_C = ["Jordan","Cape Verde","Czechia","Haiti","Saudi Arabia","Tunisia","Congo","Uzbekistan","Qatar","Bosnia","Curacao","New Zealand","South Africa","Ghana","Iraq","Scotland"]

def get_pot(t):
    if t in POT_A: return 'A'
    if t in POT_B: return 'B'
    return 'C'

def calc_bonus(team, opp, result):
    tp, op = get_pot(team), get_pot(opp)
    if result == 'win' and tp == 'C' and op == 'A': return 2
    if result == 'draw' and tp == 'C' and op == 'A': return 1
    if result == 'win' and tp == 'B' and op == 'A': return 1
    return 0

def run():
    key = os.environ.get("FETCH_FOOTBALL_API_KEY", "")
    if not key:
        print("❌ FETCH_FOOTBALL_API_KEY not set")
        return

    req = urllib.request.Request("https://api.football-data.org/v4/competitions/2000/matches", headers={"X-Auth-Token": key})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    matches = []
    for m in data.get('matches', []):
        if m['status'] not in ('FINISHED', 'IN_PLAY', 'PAUSED'): continue
        h = TEAM_MAP.get(m['homeTeam']['name'], m['homeTeam']['name'])
        a = TEAM_MAP.get(m['awayTeam']['name'], m['awayTeam']['name'])
        hs = m['score']['fullTime']['home']
        as_ = m['score']['fullTime']['away']
        if hs is None or as_ is None: continue
        r = 'home' if hs > as_ else 'away' if as_ > hs else 'draw'
        matches.append({"team1": h, "team2": a, "result": r, "score1": hs, "score2": as_, "date": m['utcDate'][:10], "group": m.get('group', '') or ''})

    ts = defaultdict(lambda: {"p": 0, "w": 0, "d": 0, "l": 0, "m": [], "b": []})

    for m in matches:
        for t, o, r, g, ga in [
            (m['team1'], m['team2'], 'win' if m['result'] == 'home' else 'loss' if m['result'] == 'away' else 'draw', m['score1'], m['score2']),
            (m['team2'], m['team1'], 'win' if m['result'] == 'away' else 'loss' if m['result'] == 'home' else 'draw', m['score2'], m['score1'])
        ]:
            pts = (3 if r == 'win' else 1 if r == 'draw' else 0) + calc_bonus(t, o, r)
            ts[t]["p"] += pts
            ts[t]["w"] += 1 if r == 'win' else 0
            ts[t]["d"] += 1 if r == 'draw' else 0
            ts[t]["l"] += 1 if r == 'loss' else 0
            b = calc_bonus(t, o, r)
            if b: ts[t]["b"].append(f"+{b} underdog vs {o}")
            ts[t]["m"].append({"opponent": o, "result": r, "goals_for": g, "goals_against": ga, "date": m['date']})

    players = [
        ("POTB", ["Jordan", "Ecuador", "Uruguay"]), ("Digs", ["Cape Verde", "Panama", "Mexico"]), ("Sean", ["Czechia", "Norway", "Belgium"]),
        ("Tadhg", ["Haiti", "Iran", "Argentina"]), ("Losty", ["Saudi Arabia", "Japan", "Portugal"]), ("Cali", ["Tunisia", "Algeria", "France"]),
        ("Dec W", ["Congo", "Paraguay", "Morocco"]), ("Dec N", ["Uzbekistan", "Turkey", "England"]), ("Smyth", ["Qatar", "Sweden", "Senegal"]),
        ("Stu", ["Bosnia", "Austria", "Colombia"]), ("Glen", ["Curacao", "South Korea", "Croatia"]), ("Sash", ["New Zealand", "Canada", "Germany"]),
        ("Deano", ["South Africa", "Switzerland", "USA"]), ("CMD", ["Ghana", "Ivory Coast", "Spain"]), ("Dave W", ["Iraq", "Australia", "Brazil"]),
        ("Cian", ["Scotland", "Egypt", "Netherlands"]),
    ]

    out = []
    for name, teams in players:
        total = 0
        td = []
        for t in teams:
            s = ts.get(t, {"p": 0, "w": 0, "d": 0, "l": 0, "m": [], "b": []})
            total += s["p"]
            td.append({"name": t, "pot": get_pot(t), "points": s["p"], "wins": s["w"], "draws": s["d"], "losses": s["l"], "matches": s["m"], "bonuses": s["b"]})
        out.append({"name": name, "total": total, "teams": td})

    out.sort(key=lambda x: x["total"], reverse=True)
    for i, p in enumerate(out):
        p["rank"] = i + 1

    from datetime import datetime, timezone, timedelta
    ireland = datetime.now(timezone.utc) + timedelta(hours=1)
    result = {"lastUpdated": ireland.strftime("%d %b %Y, %H:%M"), "players": out, "matches": matches}
    with open("scores.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"✅ Saved {len(matches)} matches, {len(out)} players")

    # Commit and push to GitHub
    import subprocess
    subprocess.run(["git", "add", "scores.json"], cwd=os.path.dirname(os.path.abspath(__file__)), capture_output=True)
    r = subprocess.run(["git", "diff", "--cached", "--quiet", "scores.json"], cwd=os.path.dirname(os.path.abspath(__file__)), capture_output=True)
    if r.returncode != 0:
        subprocess.run(["git", "commit", "-m", f"Auto-update scores ({len(matches)} matches)"], cwd=os.path.dirname(os.path.abspath(__file__)), capture_output=True)
        push = subprocess.run(["git", "push"], cwd=os.path.dirname(os.path.abspath(__file__)), capture_output=True, text=True)
        print(f"📤 Pushed to GitHub: {push.stdout.strip()[:100]}")
    else:
        print("📄 No changes to commit")

if __name__ == "__main__":
    run()
