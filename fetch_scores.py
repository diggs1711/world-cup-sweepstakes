#!/usr/bin/env python3
"""Fetch World Cup 2026 matches from football-data.org and output sweepstakes scores.

Usage: FETCH_FOOTBALL_API_KEY=<key> python3 fetch_scores.py > scores.json
       Or set the env var in your .bashrc
"""

import json
import os
import urllib.request
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta

API_KEY = os.environ.get("FETCH_FOOTBALL_API_KEY", "")
API_URL = "https://api.football-data.org/v4/competitions/2000/matches"

# Map API team names to sweepstakes team names
TEAM_MAP = {
    "Cape Verde Islands": "Cape Verde",
    "Bosnia-Herzegovina": "Bosnia",
    "Congo DR": "Congo",
    "United States": "USA",
    "Curaçao": "Curacao",
    "Czech Republic": "Czechia",
}

# Pot assignments
POT_A = ["Uruguay","Mexico","Belgium","Argentina","Portugal","France","Morocco","England","Senegal","Colombia","Croatia","Germany","USA","Spain","Brazil","Netherlands"]
POT_B = ["Ecuador","Panama","Norway","Iran","Japan","Algeria","Paraguay","Turkey","Sweden","Austria","South Korea","Canada","Switzerland","Ivory Coast","Australia","Egypt"]
POT_C = ["Jordan","Cape Verde","Czechia","Haiti","Saudi Arabia","Tunisia","Congo","Uzbekistan","Qatar","Bosnia","Curacao","New Zealand","South Africa","Ghana","Iraq","Scotland"]

def get_pot(team):
    if team in POT_A: return 'A'
    if team in POT_B: return 'B'
    return 'C'

def get_bonus(team, opponent, result):
    """result: 'win', 'draw', 'loss' from team's perspective"""
    tp, op = get_pot(team), get_pot(opponent)
    if result == 'win' and tp == 'C' and op == 'A': return 2
    if result == 'draw' and tp == 'C' and op == 'A': return 1
    if result == 'win' and tp == 'B' and op == 'A': return 1
    return 0

def map_team(name):
    return TEAM_MAP.get(name, name)

def fetch_matches():
    req = urllib.request.Request(API_URL, headers={"X-Auth-Token": API_KEY})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def process():
    if not API_KEY:
        return {"error": "FETCH_FOOTBALL_API_KEY environment variable not set"}

    data = fetch_matches()
    matches_raw = data.get('matches', [])

    # Build sweepstakes matches
    matches = []
    for m in matches_raw:
        status = m['status']
        if status not in ('FINISHED', 'IN_PLAY', 'PAUSED'):
            continue

        home = map_team(m['homeTeam']['name'])
        away = map_team(m['awayTeam']['name'])
        sc = m['score']
        hs = sc['fullTime']['home']
        as_ = sc['fullTime']['away']

        if hs is None or as_ is None:
            continue

        result = 'home' if hs > as_ else 'away' if as_ > hs else 'draw'
        date = m['utcDate'][:10]

        matches.append({
            "team1": home,
            "team2": away,
            "result": result,
            "score1": hs,
            "score2": as_,
            "date": date,
            "status": status,
            "group": m.get('group', '') or ''
        })

    # Calculate scores per team
    team_stats = defaultdict(lambda: {"points": 0, "wins": 0, "draws": 0, "losses": 0, "matches": [], "bonuses": []})

    for m in matches:
        t1, t2 = m['team1'], m['team2']
        r = m['result']

        # Team 1 perspective
        r1 = 'win' if r == 'home' else 'loss' if r == 'away' else 'draw'
        pts1 = 3 if r1 == 'win' else 1 if r1 == 'draw' else 0
        bonus1 = get_bonus(t1, t2, r1)
        team_stats[t1]["points"] += pts1 + bonus1
        team_stats[t1]["wins"] += 1 if r1 == 'win' else 0
        team_stats[t1]["draws"] += 1 if r1 == 'draw' else 0
        team_stats[t1]["losses"] += 1 if r1 == 'loss' else 0
        team_stats[t1]["matches"].append({
            "opponent": t2, "result": r1, "goals_for": m['score1'], "goals_against": m['score2'], "date": m['date']
        })
        if bonus1:
            team_stats[t1]["bonuses"].append(f"+{bonus1} underdog vs {t2}")

        # Team 2 perspective
        r2 = 'win' if r == 'away' else 'loss' if r == 'home' else 'draw'
        pts2 = 3 if r2 == 'win' else 1 if r2 == 'draw' else 0
        bonus2 = get_bonus(t2, t1, r2)
        team_stats[t2]["points"] += pts2 + bonus2
        team_stats[t2]["wins"] += 1 if r2 == 'win' else 0
        team_stats[t2]["draws"] += 1 if r2 == 'draw' else 0
        team_stats[t2]["losses"] += 1 if r2 == 'loss' else 0
        team_stats[t2]["matches"].append({
            "opponent": t1, "result": r2, "goals_for": m['score2'], "goals_against": m['score1'], "date": m['date']
        })
        if bonus2:
            team_stats[t2]["bonuses"].append(f"+{bonus2} underdog vs {t1}")

    # Build player scores
    players = [
        {"name": "POTB", "teams": ["Jordan", "Ecuador", "Uruguay"]},
        {"name": "Digs", "teams": ["Cape Verde", "Panama", "Mexico"]},
        {"name": "Sean", "teams": ["Czechia", "Norway", "Belgium"]},
        {"name": "Tadhg", "teams": ["Haiti", "Iran", "Argentina"]},
        {"name": "Losty", "teams": ["Saudi Arabia", "Japan", "Portugal"]},
        {"name": "Cali", "teams": ["Tunisia", "Algeria", "France"]},
        {"name": "Dec W", "teams": ["Congo", "Paraguay", "Morocco"]},
        {"name": "Dec N", "teams": ["Uzbekistan", "Turkey", "England"]},
        {"name": "Smyth", "teams": ["Qatar", "Sweden", "Senegal"]},
        {"name": "Stu", "teams": ["Bosnia", "Austria", "Colombia"]},
        {"name": "Glen", "teams": ["Curacao", "South Korea", "Croatia"]},
        {"name": "Sash", "teams": ["New Zealand", "Canada", "Germany"]},
        {"name": "Deano", "teams": ["South Africa", "Switzerland", "USA"]},
        {"name": "CMD", "teams": ["Ghana", "Ivory Coast", "Spain"]},
        {"name": "Dave W", "teams": ["Iraq", "Australia", "Brazil"]},
        {"name": "Cian", "teams": ["Scotland", "Egypt", "Netherlands"]},
    ]

    output_players = []
    for p in players:
        total = 0
        team_details = []
        for t in p["teams"]:
            ts = team_stats.get(t, {"points": 0, "wins": 0, "draws": 0, "losses": 0, "matches": [], "bonuses": []})
            total += ts["points"]
            team_details.append({
                "name": t,
                "pot": get_pot(t),
                "points": ts["points"],
                "wins": ts["wins"],
                "draws": ts["draws"],
                "losses": ts["losses"],
                "matches": ts["matches"],
                "bonuses": ts["bonuses"]
            })
        output_players.append({
            "name": p["name"],
            "total": total,
            "teams": team_details
        })

    output_players.sort(key=lambda x: x["total"], reverse=True)
    for i, p in enumerate(output_players):
        p["rank"] = i + 1

    # Irish time (IST = UTC+1 in summer)
    ireland_now = datetime.now(timezone.utc) + timedelta(hours=1)
    timestamp = ireland_now.strftime("%d %b %Y, %H:%M")

    return {
        "lastUpdated": timestamp,
        "matchday": data.get('season', {}).get('currentMatchday', ''),
        "players": output_players,
        "matches": matches
    }

if __name__ == "__main__":
    try:
        result = process()
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)
