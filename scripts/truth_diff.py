"""
truth_diff.py -- what changed in docs/truth/gvgai.json between a committed revision and the file in the
working tree: per game, any change of the determinism flag, every verdict that changed (level, predicate,
old and new), and the (game, level, predicate) entries whose clauses changed with the verdict the same.
Reads only the two versions of the file (the old one through git show).  Plays nothing.

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\truth_diff.py --old b0091c7 > logs\\truth_diff.log
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PATH = "docs/truth/gvgai.json"
PREDICATES = ("A1", "A2", "A3", "A4", "A5")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True, help="the git revision of the old file")
    a = ap.parse_args(argv)
    old = json.loads(subprocess.run(["git", "show", f"{a.old}:{PATH}"], cwd=REPO, check=True,
                                    capture_output=True).stdout.decode("utf-8"))["games"]
    with open(os.path.join(REPO, PATH), encoding="utf-8") as f:
        new = json.load(f)["games"]
    print(f"truth_diff: {PATH} at {a.old} against the working tree; {len(old)} games then, {len(new)} now")
    print(f"games only in the old file: {sorted(set(old) - set(new)) or 'none'}; only in the new: "
          f"{sorted(set(new) - set(old)) or 'none'}")
    verdicts, clauses = 0, 0
    for g in sorted(set(old) & set(new)):
        tag = "deterministic" if new[g]["deterministic"] else "not deterministic"
        if old[g]["deterministic"] != new[g]["deterministic"]:
            print(f"{g}: determinism flag {old[g]['deterministic']} -> {new[g]['deterministic']}")
        vch, cch = [], []
        for k in sorted(new[g]["levels"]):
            for p in PREDICATES:
                o, n = old[g]["levels"][k][p], new[g]["levels"][k][p]
                if o["verdict"] != n["verdict"]:
                    vch.append(f"L{k} {p} {o['verdict']} -> {n['verdict']}")
                elif o["clauses"] != n["clauses"]:
                    cch.append(f"L{k} {p}")
        if vch:
            print(f"{g} ({tag}): verdicts changed: {', '.join(vch)}")
        if cch:
            print(f"{g} ({tag}): clauses changed, verdict the same: {', '.join(cch)}")
        verdicts += len(vch)
        clauses += len(cch)
    det = [g for g in new if new[g]["deterministic"]]
    det_v = sum(old[g]["levels"][k][p]["verdict"] != new[g]["levels"][k][p]["verdict"]
                for g in det if g in old for k in new[g]["levels"] for p in PREDICATES)
    units = sum(len(new[g]["levels"]) for g in set(old) & set(new))
    print(f"units compared: {units}, {units * len(PREDICATES)} (unit, predicate) verdicts")
    print(f"verdicts changed: {verdicts} in all games, {det_v} in the {len(det)} deterministic games; "
          f"entries with clauses changed and the verdict the same: {clauses}")
    same = sorted(g for g in old if old[g]["deterministic"]) == sorted(det)
    print(f"the set of deterministic games is {'the same' if same else 'different'}: {len(det)} games")
    return 0


if __name__ == "__main__":
    sys.exit(main())
