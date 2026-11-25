"""
agent_cap_evidence.py -- what the committed files say about the agent unit cap of docs/PREREG.md, gate G3, before
the pilot agents of gate G1 have run.  EXPLORATORY: nothing here is a GVGAI pilot time, and G3 reads the cap from
the pilot's own times after the tag ("twice the longest pilot time for 20,000 actions, rounded up to a whole
minute", at most 1,800 s).

Reads only committed files and runs nothing:
    1. study 1's rows (read-only, D:\\Research\\arc3\\repo\\runs\\suites\\<suite>\\<condition>\\<mode>\\*.json): for
       each suite, condition and agent (nav = N, hash_state = R, i1 = I1), the wall-clock seconds of a run of
       20,000 actions, measured by study 1's runner on the author's laptop: count, median, 95th percentile, largest,
       runs cut by the wall-clock cap, the caps used; and the G3 rule applied to the largest, for scale only.
    2. logs/test_agents_gvgai.log and logs/test_gvgaiagent.log of this repository: the laptop's seconds for N, R, I1
       and Rand on GVGAI levels in the synthetic tests (2,000 actions on bait level 0, a pilot level; synthetic
       levels), as the tests printed them.
    3. logs/design_budget.log, Section 3: the confirmatory agent campaign's chunks at each candidate cap.
    4. the same count for caps above G3's ceiling of 1,800 s and for one cap per agent, for scale: 25 games x 5
       levels x 10 seeds per agent, the runner's packing rule.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\agent_cap_evidence.py > logs\\agent_cap_evidence.log
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OLD = r"D:\Research\arc3\repo"
MODES = {"nav": "N", "hash_state": "R", "i1": "I1"}
CANDIDATES = (300, 600, 1200, 1800)


def pct(xs, q):
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def g3(longest):
    return int(math.ceil(2 * longest / 60.0) * 60)


def main():
    print("== 1. study 1's runs of 20,000 actions: wall-clock seconds on the author's laptop (EXPLORATORY; study 1's rows, read-only)")
    base = os.path.join(OLD, "runs", "suites")
    for suite in sorted(os.listdir(base)):
        for cond in sorted(os.listdir(os.path.join(base, suite))):
            for mode, name in MODES.items():
                files = sorted(glob.glob(os.path.join(base, suite, cond, mode, "*.json")))
                if not files:
                    continue
                secs, cut_time, caps, budgets, acts = [], 0, set(), set(), []
                for p in files:
                    with open(p, encoding="utf-8") as f:
                        r = json.load(f)[0]
                    if "error" in r or r.get("seconds") is None:
                        continue
                    secs.append(float(r["seconds"]))
                    acts.append(int(r.get("actions") or 0))
                    budgets.add(r.get("budget"))
                    caps.add(r.get("seconds_cap"))
                    if r.get("time_truncated") or (r.get("cut_by_cap") and float(r["seconds"]) >= float(r.get("seconds_cap") or 1e18) - 1):
                        cut_time += 1
                if not secs:
                    continue
                print(f"  {suite}/{cond} {name}: {len(secs)} runs, budget {sorted(budgets)}, cap {sorted(caps)} s; seconds "
                      f"median {pct(secs, 0.5):.1f}, 95th percentile {pct(secs, 0.95):.1f}, largest {max(secs):.1f}; "
                      f"runs stopped by the wall-clock cap {cut_time}; runs short of the budget {sum(a < 20000 for a in acts)}; "
                      f"the G3 rule on the largest would give {g3(max(secs))} s")
    print()
    print("== 2. this repository's agent tests on GVGAI levels, laptop seconds as printed by the tests (EXPLORATORY)")
    for log in ("test_agents_gvgai.log", "test_gvgaiagent.log"):
        p = os.path.join(REPO, "logs", log)
        if not os.path.exists(p):
            print(f"  logs/{log}: not present")
            continue
        for line in open(p, encoding="utf-8"):
            if re.search(r"actions \d+.* s$", line.rstrip()):
                print(f"  logs/{log}: {line.strip()}")
    print()
    print("== 3. the confirmatory agent campaign at each candidate cap (logs/design_budget.log, Section 3)")
    for line in open(os.path.join(REPO, "logs", "design_budget.log"), encoding="utf-8"):
        if line.startswith("confirmatory agents, cap"):
            print("  " + line.strip())
    print()
    print("== 4. chunks (one Kaggle session each) of the confirmatory agent campaign by cap, the packing rule of the runner")
    print("     (a unit starts only if its cap fits before the work deadline: 4 workers x floor(28,800 / cap) units per chunk)")
    units_per_agent = 25 * 5 * 10
    for cap in (300, 600, 900, 1200, 1800, 2400, 3600):
        per = 4 * (28800 // cap)
        print(f"  cap {cap:5d} s: {per:4d} units per chunk; one agent ({units_per_agent} units) {math.ceil(units_per_agent / per):4d} "
              f"chunks; four agents ({4 * units_per_agent} units) {math.ceil(4 * units_per_agent / per):4d} chunks")
    print("  one cap per agent, for scale: N, R and Rand at 600 s and I1 at 3,600 s: "
          f"{math.ceil(3 * units_per_agent / (4 * (28800 // 600)))} + {math.ceil(units_per_agent / (4 * (28800 // 3600)))} chunks "
          "(a chunk holds one kind, and the runner already reads the cap per unit)")
    print()
    print("Every number above is EXPLORATORY. None is a GVGAI pilot time; G3 reads the cap from the pilot agents of G1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
