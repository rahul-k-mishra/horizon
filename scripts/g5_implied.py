"""
g5_implied.py -- what text written before 28 November 2026 already implies about gate G5 (docs/PREREG.md,
Section 8).  This is NOT G5's reading and does not open docs/truth/gvgai.json.  G5 is read by scripts/g5_reading.py,
after the hand check of Section 5 and any generator fix.

It reads three committed texts:
    docs/PREREG.md, Section 4   "The mechanics score S_M of the 25 games is 2 on 3 games, 3 on 12, 4 on 7 and 5 on 3"
    logs/fit_rule.log, Section 5   the same counts, "after the rule (25 games)", the source Section 4 cites
    logs/truth_vgdl.log         "games whose vector differs between levels: 0" for the deterministic games, so
                                S_M is constant within a game (PREREG Section 4 cites it)
It checks that Section 4 and logs/fit_rule.log give the same counts, then takes each game's S_M for all 5 of its
levels and prints the units and shares per value of S_M, with G5's threshold of 10% applied in integers, as
scripts/g5_reading.py applies it.  The figures hold for the truth table as it stood when those texts were written;
a generator fix from the hand check could change them, and G5's registered reading is the one made after it.

Run: D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\g5_implied.py > logs\\g5_implied.log
Reads only committed files.  Plays no game.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LEVELS = 5
MIN_PERCENT = 10


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return f.read()


def main():
    print("What text written before 28 November 2026 implies about G5; not G5's reading; docs/truth/gvgai.json "
          "not opened")
    m = re.search(r"The mechanics score S_M of the 25 games is 2 on (\d+) games, 3 on (\d+), 4 on (\d+) and 5 on (\d+)",
                  read("docs/PREREG.md"))
    if not m:
        print("stopped: the sentence of PREREG Section 4 was not found")
        return 2
    prereg = {2: int(m[1]), 3: int(m[2]), 4: int(m[3]), 5: int(m[4])}
    line = next((ln for ln in read("logs/fit_rule.log").splitlines() if ln.startswith("after the rule (25 games):")),
                None)
    if line is None:
        print("stopped: the line of logs/fit_rule.log, Section 5, was not found")
        return 2
    log = {int(v): int(n) for v, n in re.findall(r"S_M=(\d): (\d+) games", line)}
    print(f"PREREG Section 4: {prereg}")
    print(f"logs/fit_rule.log: {log}")
    if log != prereg:
        print("stopped: the two differ")
        return 2
    tv = read("logs/truth_vgdl.log")
    block = tv.split("== deterministic games:", 1)[1].split("==", 1)[0]
    if "games whose vector differs between levels: 0" not in block:
        print("stopped: logs/truth_vgdl.log does not record S_M constant within every deterministic game")
        return 2
    print("logs/truth_vgdl.log: deterministic games whose vector differs between levels: 0")
    games = sum(prereg.values())
    units = games * LEVELS
    need = -(-MIN_PERCENT * units // 100)
    print(f"games {games}; units {units} (5 levels each); a value needs at least {need} units ({MIN_PERCENT}%)")
    common = []
    for v in sorted(prereg):
        u = prereg[v] * LEVELS
        held = u * 100 >= MIN_PERCENT * units
        common += [v] if held else []
        print(f"  S_M = {v}: {prereg[v]:2d} games, {u:3d} units, {100 * u / units:4.1f}%{'  at least 10%' if held else ''}")
    print(f"implied: {len(common)} values of S_M held by at least {MIN_PERCENT}% of the units "
          f"({', '.join(map(str, common))}); G5 needs 2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
