"""
g5_reading.py -- gate G5 of docs/PREREG.md, Section 8: "from the truth table alone, at least two values of S_M are
each held by at least 10% of the confirmatory units".

NOT RUN ON THE REAL TRUTH TABLE.  Written on 28 November 2026 and tested only on synthetic truth tables
(scripts/test_g5_reading.py, logs/test_g5_reading.log).  docs/truth/gvgai.json is read for G5 only after the hand
check of Section 5 and any generator fix it requires.  Until docs/truth/HANDCHECK_RESULT.md exists the script refuses
to read the real table (exit 3) and reads nothing.  This refusal is a safeguard of the script, not a registered rule.

What it does, as registered:
    units       the confirmatory units of PREREG Section 4: (game, level) for the 25 games of scripts/suite.py,
                confirmatory() (the deterministic games, minus the pilot, minus the games the fit rule removes),
                levels 0 to 4, 125 units.  The deterministic games of the truth table must equal suite.deterministic(),
                as scripts/analyze_horizon.py checks.
    S_M         per unit, the number of A1 to A5 whose verdict in docs/truth/gvgai.json is "holds" (PREREG
                Section 5).  Every unit must have all five predicates with the verdict "holds" or "fails";
                otherwise the script stops with no verdict (exit 2).
    10%         a value of S_M is held by at least 10% of the units when count * 10 >= units, in integers (125
                units: at least 13).
G5 passes if at least two values of S_M are each held by at least 10% of the units.  If it fails, the stop rule of
PREREG Section 8 applies: no confirmatory unit runs and the study stops with the outcome VOID; G5 has no repair.
When: PREREG Section 8 places the gates after the tag of v1 and before any confirmatory unit; G5 is not one of the
three parts named there as running before the tag.

Parallel form: none.  The script reads 125 entries of one file; there is nothing to divide among workers, and no
unit of work long enough for a done-marker.

The single command, once the hand check is done (in cmd, working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\g5_reading.py > logs\\g5_reading.log 2>&1
The console ends with "G5: PASS" or "G5: FAIL" and returns 0 or 1; 2 if the table is incomplete; 3 if refused.
--truth and --games are for the tests (scripts/test_g5_reading.py); with either, the console says "not G5".
Reads only committed files.  Plays no game.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

TRUTH = os.path.join(REPO, "docs", "truth", "gvgai.json")
HANDCHECK_RESULT = os.path.join(REPO, "docs", "truth", "HANDCHECK_RESULT.md")
PRED = ("A1", "A2", "A3", "A4", "A5")
LEVELS = range(5)
VERDICTS = ("holds", "fails")
MIN_PERCENT = 10   # "at least 10% of the confirmatory units"
MIN_VALUES = 2     # "at least two values of S_M"


class Incomplete(Exception):
    pass


def s_m_per_unit(truth_games, games):
    """{(game, level): S_M}; raises Incomplete on a missing unit or predicate, or a verdict other than holds/fails."""
    out = {}
    for g in games:
        if g not in truth_games:
            raise Incomplete(f"{g}: not in the truth table")
        levels = truth_games[g].get("levels", {})
        for lv in LEVELS:
            entry = levels.get(str(lv))
            if entry is None:
                raise Incomplete(f"{g} level {lv}: not in the truth table")
            n = 0
            for p in PRED:
                v = entry.get(p, {}).get("verdict") if isinstance(entry.get(p), dict) else None
                if v not in VERDICTS:
                    raise Incomplete(f"{g} level {lv} {p}: verdict {v!r}, not holds or fails")
                n += v == "holds"
            out[(g, lv)] = n
    return out


def read_g5(sm):
    """(passed, counts {value: units}, common [values held by at least 10%], units)."""
    units = len(sm)
    counts = {v: 0 for v in range(len(PRED) + 1)}
    for v in sm.values():
        counts[v] += 1
    common = [v for v in sorted(counts) if counts[v] > 0 and counts[v] * 100 >= MIN_PERCENT * units]
    return len(common) >= MIN_VALUES, counts, common, units


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth", default=None, help="tests only: a synthetic truth table")
    ap.add_argument("--games", default=None, help="tests only: game,game,... in place of suite.confirmatory()")
    a = ap.parse_args(argv)
    test = a.truth is not None or a.games is not None
    print("G5 of docs/PREREG.md, Section 8: at least two values of S_M each held by at least 10% of the "
          "confirmatory units" + ("  [test options: not G5]" if test else ""))
    path = a.truth or TRUTH
    if a.truth is None and not os.path.exists(HANDCHECK_RESULT):
        print("refused: docs/truth/HANDCHECK_RESULT.md does not exist; G5 is read only after the hand check of "
              "Section 5 and any generator fix.  The truth table was not read.")
        return 3
    with open(path, encoding="utf-8") as f:
        truth_games = json.load(f)["games"]
    if a.games is not None:
        games = [g for g in a.games.split(",") if g]
    else:
        import suite  # noqa: PLC0415 -- the registered game lists
        det = sorted(g for g, v in truth_games.items() if v.get("deterministic"))
        if det != suite.deterministic():
            print("stopped: the deterministic games of the truth table differ from docs/design/vgdl_scan.json")
            return 2
        games = suite.confirmatory()
    print(f"truth table: {os.path.relpath(path, REPO) if a.truth is None else 'synthetic'}; games {len(games)}; "
          f"levels 0 to 4")
    try:
        sm = s_m_per_unit(truth_games, games)
    except Incomplete as e:
        print(f"stopped, no verdict: {e}")
        return 2
    passed, counts, common, units = read_g5(sm)
    need = -(-MIN_PERCENT * units // 100)
    print(f"units {units}; a value needs at least {need} units ({MIN_PERCENT}%)")
    for v in sorted(counts):
        mark = "at least 10%" if v in common else ""
        print(f"  S_M = {v}: {counts[v]:4d} units, {100 * counts[v] / units:5.1f}%  {mark}")
    print(f"values of S_M held by at least {MIN_PERCENT}% of the units: {len(common)} "
          f"({', '.join(map(str, common)) or 'none'}); needed {MIN_VALUES}")
    if passed:
        print("G5: PASS")
        return 0
    print("the stop rule of PREREG Section 8: no confirmatory unit runs; the study stops with the outcome VOID; "
          "G5 has no repair")
    print("G5: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
