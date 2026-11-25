"""
g2_cost.py -- what gate G2 of docs/PREREG.md, Section 8, asks for, counted, and two rough projections of its time
from committed files (docs/registration/REVIEW_2026-11-25.md, item 5).  EXPLORATORY: the projections are
scalings of other runs, not a measurement of G2.

G2 as registered: "on every pilot unit, 1,000 random action sequences of length 200, each replayed twice from the
start, give identical state hashes at every step".  The pilot units are the 20 levels of the 4 pilot games.

1. The work G2 asks for: levels x sequences x 2 replays x 200 actions at most (a sequence stops where the game
   ends, as in HorizonBridge.forwardKeys), each action followed by a state hash.
2. Projection from logs/engine_semantics.log (laptop, 14 November 2026): that run played 50 sequences of 200
   actions per pilot level, each 6 times (check 1: the game loop and the forward model, each with and without the
   tick; check 3: the forward model twice), and also ran check 2, in the wall time it prints.  G2's replays,
   divided by that run's replays, times that wall time.  It overstates, because the wall time includes check 2
   and the game-loop replays; it is the laptop's time on one process.
3. Projection from the pilot agent rows (runs/gvgai-pilot-agents, Kaggle, 25 November 2026): Rand plays 20,000
   uniform random actions per unit, so G2's 400,000 actions on a level are 20 Rand units of that level; the mean
   of Rand's two seeds per level, times 20, summed over the levels.  Rand's time includes the adapter reading the
   grid at every step, which G2 does not need, and leaves out a state hash per step, which G2 needs.
Both are divided among 4 workers and set against one session's work of 28,800 s (docs/PREREG.md, Section 9).

Reads committed files only and plays nothing.  Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\g2_cost.py > logs\\g2_cost.log
"""
import glob
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEQUENCES, LENGTH, REPLAYS = 1000, 200, 2
WORKERS, SESSION_WORK = 4, 28_800
SEMANTICS_REPLAYS_PER_SEQUENCE = 6


def main():
    with open(os.path.join(REPO, "logs", "draw_pilot.log"), encoding="utf-8") as f:
        games = [x.strip() for x in next(ln for ln in f.read().splitlines() if ln.startswith("pilot (")).split(":", 1)[1].split(",")]
    levels = [(g, lv) for g in games for lv in range(5)]
    print("G2 of docs/PREREG.md, Section 8: the work it asks for, and two rough projections (EXPLORATORY)")
    print(f"\n== 1. the work\npilot levels {len(levels)} ({', '.join(games)}; levels 0 to 4)")
    replays = len(levels) * SEQUENCES * REPLAYS
    actions = replays * LENGTH
    print(f"sequences {len(levels) * SEQUENCES:,}; replays {replays:,}; actions at most {actions:,}, each followed by a state hash")

    with open(os.path.join(REPO, "logs", "engine_semantics.log"), encoding="utf-8") as f:
        text = f.read()
    per_level = int(re.search(r"check 1 and 3: (\d+) random sequences of (\d+) actions", text).group(1))
    wall = int(re.search(r"wall time (\d+) s", text).group(1))
    sem_replays = len(levels) * per_level * SEMANTICS_REPLAYS_PER_SEQUENCE
    p2 = wall * replays / sem_replays
    print(f"\n== 2. from logs/engine_semantics.log (laptop, one process)\nthat run: {per_level} sequences per level, "
          f"{SEMANTICS_REPLAYS_PER_SEQUENCE} replays each, {sem_replays:,} replays and check 2 in {wall} s")
    print(f"G2: {replays:,} / {sem_replays:,} x {wall} s = {p2:,.0f} s on one process; {p2 / WORKERS:,.0f} s on {WORKERS} workers")

    rows = []
    for fn in glob.glob(os.path.join(REPO, "runs", "gvgai-pilot-agents", "gvgaiagent", "*.json")):
        with open(fn, encoding="utf-8") as f:
            r = json.load(f)
        if r["agent"] == "Rand":
            rows.append(r)
    by = {}
    for r in rows:
        by.setdefault((r["game"], r["level"]), []).append(r["seconds"])
    total = sum(20 * sum(v) / len(v) for v in by.values())
    longest = max(by, key=lambda k: sum(by[k]) / len(by[k]))
    lmean = sum(by[longest]) / len(by[longest])
    print(f"\n== 3. from Rand's pilot agent rows (Kaggle)\nRand rows {len(rows)} on {len(by)} levels, budget "
          f"{rows[0]['budget']:,} actions each")
    print(f"G2 per level = {actions // len(levels) // rows[0]['budget']} Rand units; summed over the levels: {total:,.0f} s "
          f"on one process; {total / WORKERS:,.0f} s on {WORKERS} workers; longest level {longest[0]} {longest[1]}, "
          f"{20 * lmean:,.0f} s")
    print(f"\none session's work: {SESSION_WORK:,} s on {WORKERS} workers; the larger projection is "
          f"{max(p2, total) / WORKERS / SESSION_WORK:.3f} of it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
