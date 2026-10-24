"""
draw_pilot.py -- draws the pilot games of docs/PREREG.md (Section 4) from the deterministic GVGAI games.

Reads only docs/design/vgdl_scan.json (written by scripts/vgdl_scan.py).  The games marked deterministic
there are sorted by name, and numpy.random.default_rng(20261024).choice(n, 4, replace=False) picks the
pilot; the rest are the confirmatory games.  Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\draw_pilot.py > logs\\draw_pilot.log
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, N_PILOT = 20261024, 4


def main():
    with open(os.path.join(REPO, "docs", "design", "vgdl_scan.json"), encoding="utf-8") as f:
        scan = json.load(f)
    games = sorted(g["game"] for g in scan["games"] if g["deterministic"])
    idx = np.random.default_rng(SEED).choice(len(games), N_PILOT, replace=False)
    pilot = sorted(games[i] for i in idx)
    conf = [g for g in games if g not in pilot]
    print(f"numpy {np.__version__}; seed {SEED}; {len(games)} deterministic games in name order")
    print(f"pilot ({len(pilot)}): {', '.join(pilot)}")
    print(f"confirmatory ({len(conf)}): {', '.join(conf)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
