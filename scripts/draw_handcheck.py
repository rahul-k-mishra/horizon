"""
draw_handcheck.py -- draws the games of the author's hand check of the truth tables (docs/PREREG.md, Section 5)
and writes the sheet docs/truth/HANDCHECK.md from docs/truth/gvgai.json (written by scripts/truth_vgdl.py).

Reads only docs/truth/gvgai.json.  The deterministic games there are sorted by name;
rng = numpy.random.default_rng(20261025) draws 10 of them (rng.choice, without replacement), then, for
each drawn game in name order, one level from 1 to 4 (rng.integers(1, 5)).  For each game the sheet shows
level 0 and that level, and for each of A1 to A5 the generator's verdict with every clause and line it
rests on, and empty boxes for the author's mark.  It fills in no answer.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\draw_handcheck.py > logs\\draw_handcheck.log
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, N = 20261025, 10
PRED = ("A1", "A2", "A3", "A4", "A5")
NAMES = {"A1": "input coupling", "A2": "one controlled object", "A3": "lattice motion", "A4": "a fixed set of blockers",
         "A5": "a place goal"}


def main():
    with open(os.path.join(REPO, "docs", "truth", "gvgai.json"), encoding="utf-8") as f:
        t = json.load(f)
    games = sorted(g for g, v in t["games"].items() if v["deterministic"])
    rng = np.random.default_rng(SEED)
    drawn = sorted(games[i] for i in rng.choice(len(games), N, replace=False))
    other = {g: int(rng.integers(1, 5)) for g in drawn}
    print(f"numpy {np.__version__}; seed {SEED}; {len(games)} deterministic games in name order")
    print("drawn: " + ", ".join(f"{g} (levels 0 and {other[g]})" for g in drawn))
    out = ["# Hand check of the truth tables", "",
           "For the author. Drawn by scripts/draw_handcheck.py with seed 20261025 (logs/draw_handcheck.log) from the 30 "
           "deterministic games of docs/truth/gvgai.json, written by scripts/truth_vgdl.py (logs/truth_vgdl.log). "
           "The predicates are those of docs/PREREG.md draft v0, Section 5.", "",
           "**How to use this sheet.** For each game, open its description (and level files) at the paths given, read "
           "each clause at its line, and decide whether the predicate's verdict is right for that game and level by the "
           "registered wording. Mark one box per row and add a note where you disagree. A clause line refers to the "
           "description unless the file named is a level file. No answer is filled in.", "",
           "**The rule after the check** (docs/PREREG.md, Section 5): every disagreement is resolved from the GVGAI "
           "source, fixes the generator, and is listed in the registration; the generator is then rerun on all games "
           "and 5 fresh games are checked, which must agree on every predicate.", ""]
    for g in drawn:
        gv = t["games"][g]
        out += [f"## {g}", "", f"Description: `{gv['description']}`. Levels checked: 0 (`{gv['levels']['0']['level_file']}`) "
                f"and {other[g]} (`{gv['levels'][str(other[g])]['level_file']}`).", "",
                "| predicate | level | generator's verdict | the clauses it rests on (file:line, text, what was read) | agree | disagree | note |",
                "|---|---|---|---|---|---|---|"]
        for p in PRED:
            for k in ("0", str(other[g])):
                e = gv["levels"][k][p]
                cl = "<br>".join(f"{c['file'].split('/')[-1]}:{c['line']} `{(c['text'] or '').strip()}` ({c['reads']})"
                                 for c in e["clauses"])
                out.append(f"| {p}, {NAMES[p]} | {k} | **{e['verdict']}** | {cl} | [ ] | [ ] |  |")
        out.append("")
    path = os.path.join(REPO, "docs", "truth", "HANDCHECK.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"written {os.path.relpath(path, REPO)}: {len(drawn)} games, {len(drawn) * len(PRED) * 2} rows to mark")
    return 0


if __name__ == "__main__":
    sys.exit(main())
