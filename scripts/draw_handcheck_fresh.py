"""
draw_handcheck_fresh.py -- draws the fresh games of the hand check (docs/PREREG.md, Section 5, decided 28 November
2026): the 5 games checked after the generator fix and rerun, and, only if that check fails, 5 new ones.

The pool is the pool of the original draw (scripts/draw_handcheck.py): the deterministic games of
docs/truth/gvgai.json in name order, which must equal scripts/suite.py, deterministic() (30 games).  Excluded:
    round 1   the 10 games of the original draw (seed 20261025, recomputed here and checked against
              docs/truth/HANDCHECK.md); seed 20261128; 5 games from the 20 left.
    round 2   those 10 and the 5 of round 1; seed 20261129; 5 games from the 15 left.  Drawn only if round 1 shows a
              disagreement (Section 5, failure form (ii)).
The draw is made as the original one is: rng = numpy.random.default_rng(seed); rng.choice(len(pool), 5,
replace=False), the drawn games sorted by name; then, for each drawn game in name order, one level from 1 to 4
(rng.integers(1, 5)).  Each game is checked on level 0 and that level, every predicate: 50 rows per round.
Only the names of the games are read from docs/truth/gvgai.json, never a verdict, so no generator fix can change
what is drawn.  Writes docs/truth/handcheck_fresh_<round>.json (the games and levels; no verdict, no row).

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\draw_handcheck_fresh.py --round 1 > logs\\draw_handcheck_fresh_1.log
Round 2 refuses unless docs/truth/handcheck_fresh_1.json exists.  A round whose file exists is not drawn again.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import draw_handcheck  # noqa: E402 -- the original draw's seed and count, not a copy of them

TRUTH = os.path.join(REPO, "docs", "truth")
SEEDS = {1: 20261128, 2: 20261129}
N = 5
SCHEMA = "horizon.handcheck_fresh.v1"


def fresh_path(rnd, folder=TRUTH):
    return os.path.join(folder, f"handcheck_fresh_{rnd}.json")


def pool():
    import suite  # noqa: PLC0415
    with open(os.path.join(TRUTH, "gvgai.json"), encoding="utf-8") as f:
        games = sorted(g for g, v in json.load(f)["games"].items() if v["deterministic"])
    if games != suite.deterministic():
        raise SystemExit("the deterministic games of docs/truth/gvgai.json differ from scripts/suite.py")
    return games


def original(games):
    rng = np.random.default_rng(draw_handcheck.SEED)
    drawn = sorted(games[i] for i in rng.choice(len(games), draw_handcheck.N, replace=False))
    with open(os.path.join(TRUTH, "HANDCHECK.md"), encoding="utf-8") as f:
        sheet = re.findall(r"^## (\S+)\n", f.read(), re.M)
    if drawn != sheet:
        raise SystemExit(f"the original draw recomputed ({drawn}) differs from docs/truth/HANDCHECK.md ({sheet})")
    return drawn


def draw(games, excluded, seed):
    left = [g for g in games if g not in set(excluded)]
    rng = np.random.default_rng(seed)
    drawn = sorted(left[i] for i in rng.choice(len(left), N, replace=False))
    return left, [(g, int(rng.integers(1, 5))) for g in drawn]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, choices=(1, 2), required=True)
    a = ap.parse_args(argv)
    out = fresh_path(a.round)
    if os.path.exists(out):
        print(f"{os.path.relpath(out, REPO)} exists: round {a.round} was drawn already, and is not drawn again")
        return 3
    games = pool()
    excluded = original(games)
    if a.round == 2:
        if not os.path.exists(fresh_path(1)):
            print("round 2 refused: round 1 has not been drawn")
            return 3
        with open(fresh_path(1), encoding="utf-8") as f:
            excluded = excluded + [g["game"] for g in json.load(f)["games"]]
    left, drawn = draw(games, excluded, SEEDS[a.round])
    print(f"numpy {np.__version__}; pool: {len(games)} deterministic games in name order (scripts/suite.py)")
    print(f"excluded ({len(excluded)}): {', '.join(excluded)}")
    print(f"round {a.round}: seed {SEEDS[a.round]}; {N} games from the {len(left)} left")
    print("drawn: " + ", ".join(f"{g} (levels 0 and {k})" for g, k in drawn))
    data = {"schema": SCHEMA, "round": a.round, "seed": SEEDS[a.round], "written_by": "scripts/draw_handcheck_fresh.py",
            "pool": len(games), "excluded": excluded,
            "games": [{"game": g, "levels": [0, k]} for g, k in drawn],
            "rows": len(drawn) * len(draw_handcheck.PRED) * 2}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1)
        f.write("\n")
    print(f"written {os.path.relpath(out, REPO).replace(os.sep, '/')}: {len(drawn)} games, {data['rows']} rows to mark "
          "once the generator is fixed and rerun")
    return 0


if __name__ == "__main__":
    sys.exit(main())
