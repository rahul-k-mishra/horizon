"""
power_primary.py -- EXPLORATORY.  The power of the primary test of docs/PREREG.md, Section 7.2, on the confirmatory
structure left by the fit rule of 14 November 2026 (25 games; logs/fit_rule.log), by the method of
scripts/stage_e_diagnosis.py, Section 6, which gave the 26-game values cited in PREREG Sections 1, 7.5 and 7.8.
Development data only; nothing here is evidence for any claim.

What it can and cannot give now.  The primary score is L_C, the fewest actions to a win within C states.  Stage D's
rows give L (the fewest actions to a win found below stage D's caps) but not the number of states seen when the
first win was seen, so L_C at a candidate ceiling cannot be read from them; stage E's rows give it, and
scripts/stage_e_reading.py, Section 4, computes the power of L_C at every candidate ceiling (10,000 to 2,000,000)
on the same structure once stage E is done.  This script gives, on stage D's rows:
    L      the power of the primary test with L uncensored (time-capped units without a win excluded), as
           stage_e_diagnosis.py, Section 6 did for 26 games;
    H_C    the power of the secondary score H_C at each candidate ceiling of stage E (10,000, 100,000, 300,000,
           1,000,000 and 2,000,000 states), which stage D's rows determine exactly.
Each: 4,000 simulated studies of N clusters of 5 units (N = the number of confirmatory games, scripts/sdd.py
N_CLUSTERS), a cluster taking 5 units of one development game and the S_M of one confirmatory game, each drawn
with replacement; seed 20261114 in 8 chunks; power by the normal approximation of scripts/sdd.py, P(lower end of the
interval > 0.5), at 98.33% and 95%, and the share of studies with the point at or above 0.70 and the lower end of
the 98.33% interval above 0.5.

Reads only committed files: stage D's rows, docs/truth/gvgai.json and the game lists (scripts/suite.py), and study
1's macro rows and truth table (read-only) through scripts/stage_e_diagnosis.py.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\power_primary.py --workers 4 > logs\\power_primary.log
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import sdd  # noqa: E402
import stage_e_diagnosis as D  # noqa: E402 -- the loader, the simulation and the power summary, unchanged

TAG = "EXPLORATORY"
CANDIDATES = (10_000, 100_000, 300_000, 1_000_000, 2_000_000)
OUT = os.path.join(REPO, "docs", "design", "power_primary.json")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-repo", default=r"D:\Research\arc3\repo")
    ap.add_argument("--workers", type=int, default=4)
    a_ = ap.parse_args(argv)
    sm, _ = sdd.confirmatory_mechanics()
    smv = [float(v) for v in sm.values()]
    dist = {v: sum(1 for x in sm.values() if x == v) for v in sorted(set(sm.values()))}
    print(f"power_primary -- {TAG}: development data, not evidence for any claim")
    print(f"confirmatory structure: {sdd.N_CLUSTERS} games (scripts/suite.py), S_M " +
          ", ".join(f"{v}: {n} games" for v, n in dist.items()))
    print(f"{D.SIMS} simulated studies of {sdd.N_CLUSTERS} clusters of {D.LEVELS} units each, seed {D.SIM_SEED}, "
          f"{D.CHUNKS} chunks; between-game pairs; normal approximation of scripts/sdd.py")
    search, games, data = D.load(a_.old_repo)
    out = dict(label=TAG, n_clusters=sdd.N_CLUSTERS, sm=sm)
    scores = [("L", "L (stage D, uncensored; time-capped units without a win excluded)")] + \
        [(c, f"H_C, C = {c:,}") for c in CANDIDATES]
    for score, lab in scores:
        print(f"\n== {lab}")
        for ag in D.AGENTS:
            a = D.defined(D.arrays(search, games, data[ag]), score)
            cl = [(a[score][a["game"] == g], a["y"][a["game"] == g]) for g in np.unique(a["game"])]
            plain, strat = D.simulate(cl, smv, a_.workers)
            res = {}
            for plab, v in (("same S_M", strat), ("all", plain)):
                res[plab] = {alab: D.power_summary(v, al) for alab, al in (("98.33%", D.ALPHA), ("95%", 0.05))}
            s98, s95, a98 = res["same S_M"]["98.33%"], res["same S_M"]["95%"], res["all"]["98.33%"]
            print(f"  {ag}: same-S_M pairs: mean AUROC {s98['mean']:.4f}, SE {s98['se']:.4f} ({s98['studies']} studies); "
                  f"power above 0.5 at 98.33% {s98['power_above_half']:.4f}, at 95% {s95['power_above_half']:.4f}; "
                  f"point at or above 0.70 and lower end above 0.5 at 98.33% {s98['power_above_half_and_point_070']:.4f}"
                  f" | all between-game pairs: mean {a98['mean']:.4f}, power at 98.33% {a98['power_above_half']:.4f}")
            out[f"{'L' if score == 'L' else score} {ag}"] = res
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
    print(f"\nwritten {os.path.relpath(OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
