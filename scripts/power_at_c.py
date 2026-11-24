"""
power_at_c.py -- EXPLORATORY.  The power of the primary test of docs/PREREG.md, Section 7.8, at the ceiling fixed on
24 November 2026 (C = 1,000,000; the constant C of scripts/analyze_horizon.py), with the one quantity Section 7.8
asks for that logs/stage_e_reading.log does not print: the share of simulated studies in which AUROC_L is at or
above 0.70 and the lower end of the 98.33% interval lies above 0.5.

Method: exactly that of scripts/stage_e_reading.py, Section 4, restricted to L_C at C: stage E's rows (runs/dev-
minigrid-e) give L_C per development unit; study 1's outcomes of N, R and I1 (read-only, through
scripts/stage_e_diagnosis.load); 4,000 simulated studies of N clusters of 5 units (N = the 25 confirmatory games),
a cluster taking 5 units of one development game and the S_M of one confirmatory game (scripts/sdd.py), each drawn
with replacement, seeds and chunks of scripts/stage_e_diagnosis.simulate; summaries by
scripts/stage_e_diagnosis.power_summary.  The same seeds give the same studies, so the power above one half must
equal logs/stage_e_reading.log, Section 4, at this C; the script prints both and stops if they differ.

Development data only; nothing here is evidence for any claim.  Reads only committed files; runs no experiment.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\power_at_c.py --workers 4 > logs\\power_at_c.log
"""
from __future__ import annotations

import argparse
import collections
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import analyze_horizon as A  # noqa: E402 -- the fixed C only
import sdd  # noqa: E402
import stage_e_diagnosis as D  # noqa: E402
import stage_e_reading as SR  # noqa: E402

TAG = "EXPLORATORY"


def logged_power(c):
    """{agent: (98.33%, 95%)} of L_C on same-S_M pairs at c, as logs/stage_e_reading.log, Section 4, prints it."""
    pat = re.compile(r"^\s+C\s+([\d,]+) L_C (\w+): .*same S_M mean [\d.]+ SE [\d.]+ power 98\.33% ([\d.]+) 95% ([\d.]+)")
    out = {}
    with open(os.path.join(REPO, "logs", "stage_e_reading.log"), encoding="utf-8") as f:
        for ln in f:
            m = pat.match(ln)
            if m and int(m.group(1).replace(",", "")) == c:
                out[m.group(2)] = (m.group(3), m.group(4))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-repo", default=r"D:\Research\arc3\repo")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    c = A.C
    print(f"power_at_c -- {TAG}: the power of the primary test at C = {c:,} (docs/PREREG.md, Section 7.8); development "
          f"data, not evidence for any claim")
    rows = SR.read_rows(SR.E_ROWS)
    _, _, data = D.load(a.old_repo)
    smv = [float(v) for v in sdd.confirmatory_mechanics()[0].values()]
    logged = logged_power(c)
    print(f"structure: {sdd.N_CLUSTERS} clusters of {D.LEVELS} units; {D.SIMS} simulated studies in {D.CHUNKS} chunks, "
          f"seed {D.SIM_SEED}; S_M of the {len(smv)} confirmatory games; stage E rows {len(rows)}")
    print("L_C on same-S_M between-game pairs, per evidence agent:")
    print("  agent | units | studies | mean AUROC_L | SE | power 98.33% (log) | power 95% (log) | "
          "point >= 0.70 | point >= 0.70 and lower end of 98.33% > 0.5")
    bad = []
    for ag in D.AGENTS:
        vals = {k: SR.l_c(r, c) for k, r in rows.items()}
        keys = [k for k in data[ag] if k in vals and not math.isnan(vals[k])]
        per = collections.defaultdict(list)
        for k in keys:
            per[k[0]].append((vals[k], data[ag][k]["y"]))
        cl = [(np.array([x for x, _ in v], float), np.array([y for _, y in v], bool)) for _, v in sorted(per.items())]
        _, strat = D.simulate(cl, smv, a.workers)
        r98 = D.power_summary(strat, D.ALPHA)
        r95 = D.power_summary(strat, 0.05)
        p98, p95 = f"{r98['power_above_half']:.4f}", f"{r95['power_above_half']:.4f}"
        lg = logged.get(ag, ("missing", "missing"))
        if (p98, p95) != lg:
            bad.append(f"{ag}: {p98}, {p95} against the log's {lg[0]}, {lg[1]}")
        print(f"  {ag:<5} | {len(keys):>5} | {r98['studies']:>7} | {r98['mean']:.4f} | {r98['se']:.4f} | "
              f"{p98} ({lg[0]}) | {p95} ({lg[1]}) | {r98['share_point_at_least_070']:.4f} | "
              f"{r98['power_above_half_and_point_070']:.4f}")
    if bad:
        print("DIFFERS from logs/stage_e_reading.log: " + "; ".join(bad))
        return 1
    print("the power above one half equals logs/stage_e_reading.log, Section 4, at this C for every agent")
    print("the last column is the share of simulated studies that would give the verdict 'shown' (Section 7.5: the "
          "point at or above 0.70 and the lower end of the 98.33% interval above 0.5, the interval taken as the point "
          "minus z times the SE over the studies, as scripts/stage_e_diagnosis.power_summary does)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
