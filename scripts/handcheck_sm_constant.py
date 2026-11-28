"""
handcheck_sm_constant.py -- what the hand check's contamination of A1 and A4 costs (docs/PREREG.md, Section 5,
decided 28 November 2026).  Arithmetic only, from committed text; it opens neither the truth table nor any answer.

Reads:
    docs/PREREG.md, Section 4     "The mechanics score S_M of the 25 games is 2 on 3 games, 3 on 12, 4 on 7 and 5 on 3"
    docs/PREREG.md, Section 7.8   "A1 and A4 hold on all 25, A2 on 6, A3 on 19, A5 on 10" (the predicate counts of
                                  the confirmatory games; logs/sdd.log)
    docs/truth/handcheck_seen.json   the contamination register: which rows of the hand check and of fresh round 1
                                  are seen, by predicate (scripts/handcheck_seen.py)
Prints:
    1. the two texts, and the check that they agree: the sum of S_M over the games equals the sum of the predicate
       counts;
    2. that A1 and A4 each hold on every game, so together they add exactly 2 to every game's S_M, and S_M minus 2,
       the part from A2, A3 and A5, has the same groups of games;
    3. that a constant added to every game's S_M changes neither the same-S_M groups the primary test pairs within
       (Section 7.2: pairs of games, and between-game pairs of units, 5 units a game) nor the order of the games by
       S_M, which is all the AUROC of S_M (Section 7.7) uses;
    4. what a non-uniform error would do: A1 or A4 reported as holding on one game where it fails lowers that game's
       S_M by 1; for each value it could leave, the same-S_M pairs of games and of units before and after;
    5. from the register, the seen and blind rows of each predicate in each row set: no blind row tests A1 or A4.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\handcheck_sm_constant.py > logs\\handcheck_sm_constant.log
"""
from __future__ import annotations

import json
import os
import re
import sys
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LEVELS = 5
PRED = ("A1", "A2", "A3", "A4", "A5")
WORDS = {"two": 2, "three": 3, "four": 4, "five": 5}


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return f.read()


def pairs(groups):
    """(same-S_M pairs of games, same-S_M between-game pairs of units) for {S_M: games}."""
    g = sum(comb(k, 2) for k in groups.values())
    u = sum(comb(LEVELS * k, 2) - k * comb(LEVELS, 2) for k in groups.values())
    return g, u


def main():
    prereg = read("docs/PREREG.md")
    sec4 = prereg[prereg.index("## 4. Suite"):prereg.index("## 5. ")]
    m = re.search(r"The mechanics score S_M of the (\d+) games is 2 on (\d+) games, 3 on (\d+), 4 on (\d+) and 5 on (\d+)",
                  sec4)
    n = int(m.group(1))
    spread = {2: int(m.group(2)), 3: int(m.group(3)), 4: int(m.group(4)), 5: int(m.group(5))}
    sec78 = prereg[prereg.index("### 7.8 "):prereg.index("## 8. ")]
    m2 = re.search(r"A1 and A4 hold on all (\d+), A2 on (\d+), A3 on (\d+), A5 on (\d+)", sec78)
    holds = {"A1": int(m2.group(1)), "A4": int(m2.group(1)), "A2": int(m2.group(2)), "A3": int(m2.group(3)),
             "A5": int(m2.group(4))}
    print("1. the texts")
    print(f"   PREREG Section 4: S_M on {n} games: " + ", ".join(f"{v}: {k} games" for v, k in spread.items()))
    print("   PREREG Section 7.8: games where each predicate holds: " + ", ".join(f"{p} {holds[p]}" for p in PRED))
    total_sm = sum(v * k for v, k in spread.items())
    total_p = sum(holds.values())
    ok = sum(spread.values()) == n and total_sm == total_p
    print(f"   games in the spread {sum(spread.values())}; sum of S_M {total_sm}; sum of the predicate counts {total_p}: "
          + ("they agree" if ok else "THEY DISAGREE"))

    print("2. A1 and A4")
    const = holds["A1"] == n and holds["A4"] == n
    rest = {v - 2: k for v, k in spread.items()}
    print(f"   A1 holds on {holds['A1']} of {n} games and A4 on {holds['A4']} of {n}: "
          + ("together exactly 2 on every game" if const else "NOT a constant"))
    print(f"   S_M minus 2, from A2, A3 and A5 alone: " + ", ".join(f"{v}: {k} games" for v, k in rest.items())
          + f"; sum {sum(v * k for v, k in rest.items())} = A2 + A3 + A5 = {holds['A2'] + holds['A3'] + holds['A5']}")

    print("3. a constant added to every game's S_M")
    g0, u0 = pairs(spread)
    g1, u1 = pairs(rest)
    print(f"   same-S_M pairs of games {g0} with S_M, {g1} with S_M minus 2; between-game same-S_M pairs of units {u0} "
          f"and {u1}: " + ("unchanged" if (g0, u0) == (g1, u1) else "CHANGED"))
    order = sorted(spread) == [v + 2 for v in sorted(rest)]
    print("   the order of the values, and so of the games, by S_M and by S_M minus 2: "
          + ("the same" if order else "DIFFERENT") + "; the AUROC of S_M depends on that order alone")

    print("4. a non-uniform error: A1 or A4 reported as holding on one game where it fails")
    for v in sorted(spread):
        if spread[v] == 0 or v - 1 < 0:
            continue
        moved = dict(spread)
        moved[v] -= 1
        moved[v - 1] = moved.get(v - 1, 0) + 1
        g2, u2 = pairs({k: c for k, c in moved.items() if c})
        print(f"   a game with S_M {v} counted as {v - 1}: same-S_M pairs of games {g0} -> {g2}, of units {u0} -> {u2}; "
              f"the game leaves its group of {spread[v]} and joins one of {spread.get(v - 1, 0)}")

    print("5. seen and blind rows by predicate (docs/truth/handcheck_seen.json)")
    reg = json.loads(read("docs/truth/handcheck_seen.json"))
    seen = set(reg["rows"])
    with open(os.path.join(REPO, "logs", "draw_handcheck.log"), encoding="utf-8") as f:
        drawn = re.findall(r"(\w+) \(levels 0 and (\d+)\)", re.search(r"^drawn: (.+)$", f.read(), re.M).group(1))
    fresh = json.loads(read("docs/truth/handcheck_fresh_1.json"))["games"]
    sets = {"hand check": [(g, [0, int(k)]) for g, k in drawn],
            "fresh round 1": [(d["game"], d["levels"]) for d in fresh]}
    blind_a1a4 = 0
    for name, units in sets.items():
        parts = []
        for p in PRED:
            ids = [f"{g}/{p}/{lv}" for g, lvs in units for lv in lvs]
            s = sum(i in seen for i in ids)
            parts.append(f"{p} seen {s}, blind {len(ids) - s}")
            if p in ("A1", "A4"):
                blind_a1a4 += len(ids) - s
        print(f"   {name}: " + "; ".join(parts))
    print(f"   blind rows of A1 and A4 in both sets: {blind_a1a4}")
    print("OK" if ok and const and (g0, u0) == (g1, u1) and order else "FAILED")
    return 0 if ok and const else 1


if __name__ == "__main__":
    sys.exit(main())
