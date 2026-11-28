"""
test_g5_reading.py -- tests of scripts/g5_reading.py on synthetic truth tables only.  The real table,
docs/truth/gvgai.json, is never read here: every run that would read it is either given a synthetic --truth or
checked to refuse before it opens the file.

Checks:
    1. S_M of a unit is the number of A1 to A5 whose verdict is "holds", worked by hand on mixed patterns;
    2. a table that passes: 125 units, S_M 3 on 65 and 4 on 60 (exit 0, "G5: PASS");
    3. G5 names one condition, at least two values each held by at least 10%, so a table fails it in one way,
       fewer than two such values.  That happens in two shapes, each tested: (a) one value of S_M on every
       unit; (b) three values, but two of them held by 6 of 125 units each, under 10% (exit 1, "G5: FAIL",
       the stop rule and VOID named).  Fewer than one such value cannot happen: S_M has 6 possible values, so
       one of them is held by at least a sixth of the units; checked on 2,000 random tables;
    4. the boundary of 10% on 125 units, where 10% is 12.5: a second value on 13 units passes, on 12 fails;
    5. the boundary of 10% where it is a whole number, 100 units of 20 games: a second value on exactly 10 units
       passes ("at least"), on 9 fails; and the comparison is in integers;
    6. the boundary of two values: exactly two values at 10% or more pass, exactly one fails (3 (b) and 4);
       four pass;
    7. an incomplete table gives no verdict (exit 2): a missing game, a missing level, a missing predicate, a
       verdict other than holds or fails;
    8. without docs/truth/HANDCHECK_RESULT.md the default run refuses (exit 3) and does not open the truth table;
       the author's command, run as a separate process today, refuses;
    9. test options print "not G5".
Run: D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\test_g5_reading.py > logs\\test_g5_reading.log
"""
import builtins
import contextlib
import io
import json
import os
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import g5_reading as G  # noqa: E402

FAILS = []
TMP = tempfile.mkdtemp(prefix="g5-test-")


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        FAILS.append(what)


def entry(holds):
    return {p: {"verdict": "holds" if p in holds else "fails", "clauses": []} for p in G.PRED}


def by_score(k):
    return entry(G.PRED[:k])


def table(levels_by_game, name):
    """levels_by_game {game: [entry of level 0 .. 4]}; writes a synthetic truth table, returns its path."""
    t = {"games": {g: {"deterministic": True, "levels": {str(i): e for i, e in enumerate(lv)}}
                   for g, lv in levels_by_game.items()}}
    path = os.path.join(TMP, name + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(t, f)
    return path


def scores_table(scores, name):
    """scores: one S_M per unit, 5 per game, in order; games g00, g01, ..."""
    assert len(scores) % 5 == 0
    games = {f"g{i // 5:02d}": [by_score(s) for s in scores[i:i + 5]] for i in range(0, len(scores), 5)}
    return table(games, name), ",".join(games)


def run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = G.main(list(argv))
    return code, buf.getvalue()


def run_scores(scores, name):
    path, games = scores_table(scores, name)
    return run("--truth", path, "--games", games)


def part1():
    print("== 1. S_M per unit")
    path = table({"m": [entry(()), entry(("A2", "A5")), entry(("A1", "A3", "A4")), entry(G.PRED),
                        entry(("A4",))]}, "mixed")
    with open(path, encoding="utf-8") as f:
        sm = G.s_m_per_unit(json.load(f)["games"], ["m"])
    check([sm[("m", lv)] for lv in range(5)] == [0, 2, 3, 5, 1],
          f"none, A2+A5, A1+A3+A4, all, A4 give 0, 2, 3, 5, 1 (got {[sm[('m', lv)] for lv in range(5)]})")


def part2():
    print("== 2. a table that passes")
    code, out = run_scores([3] * 65 + [4] * 60, "pass")
    check(code == 0 and out.rstrip().endswith("G5: PASS") and "units 125; a value needs at least 13 units" in out,
          f"S_M 3 on 65 and 4 on 60 of 125: PASS (exit {code})")


def part3():
    print("== 3. tables that fail: fewer than two values held by at least 10%")
    code, out = run_scores([4] * 125, "one-value")
    check(code == 1 and out.rstrip().endswith("G5: FAIL") and "VOID" in out and "no repair" in out,
          f"(a) S_M 4 on all 125 units: FAIL, the stop rule and VOID named (exit {code})")
    scores = [3] * 110 + [3, 3, 3, 2, 2] + [2, 2, 2, 2, 5] + [5] * 5
    code, out = run_scores(scores, "one-common")
    check(code == 1 and "S_M = 2:    6 units" in out and "S_M = 5:    6 units" in out and "S_M = 3:  113 units" in out
          and out.rstrip().endswith("G5: FAIL"),
          f"(b) S_M 3 on 113, 2 on 6, 5 on 6 of 125: FAIL (exit {code})")
    rng = random.Random(20261128)
    empty = 0
    for _ in range(2000):
        n = rng.randrange(1, 300)
        sm = {i: rng.choice(range(rng.randrange(1, 7))) if rng.random() < 0.5 else rng.randrange(6) for i in range(n)}
        empty += G.read_g5(sm)[2] == []
    check(empty == 0, f"no value at 10%: possible in 0 of 2,000 random tables (got {empty})")


def part4():
    print("== 4. the boundary of 10% on 125 units (12.5)")
    code, _ = run_scores([3] * 112 + [4] * 13, "b125-13")
    check(code == 0, f"S_M 4 on 13 of 125 (10.4%): PASS (exit {code})")
    code, _ = run_scores([3] * 113 + [4] * 12, "b125-12")
    check(code == 1, f"S_M 4 on 12 of 125 (9.6%): FAIL (exit {code})")


def part5():
    print("== 5. the boundary of 10% where it is whole: 100 units")
    code, out = run_scores([3] * 90 + [4] * 10, "b100-10")
    check(code == 0 and "units 100; a value needs at least 10 units" in out,
          f"S_M 4 on exactly 10 of 100 (10%): PASS, 'at least' (exit {code})")
    code, _ = run_scores([3] * 91 + [4] * 9, "b100-9")
    check(code == 1, f"S_M 4 on 9 of 100: FAIL (exit {code})")
    check(G.read_g5({i: (4 if i < 3 else 3) for i in range(30)})[0], "3 of 30 is 10% exactly in integers: held")
    check(not G.read_g5({i: (4 if i < 7 else 3) for i in range(71)})[0], "7 of 71 (9.86%): not held")


def part6():
    print("== 6. the boundary of two values")
    check(G.read_g5({i: (2 if i < 13 else 3) for i in range(125)})[2] == [2, 3], "exactly two values at 10%: PASS")
    code, _ = run_scores([2] * 15 + [3] * 60 + [4] * 35 + [5] * 15, "three")
    check(code == 0, f"four values each at 10% or more: PASS (exit {code})")


def part7():
    print("== 7. an incomplete table gives no verdict")
    full = {f"g{i}": [by_score(3)] * 5 for i in range(2)}
    path = table(full, "full")
    code, out = run("--truth", path, "--games", "g0,g1,g9")
    check(code == 2 and "g9: not in the truth table" in out, f"a missing game: exit 2 (exit {code})")
    t = {"g0": [by_score(3)] * 4}
    code, out = run("--truth", table(t, "nolevel"), "--games", "g0")
    check(code == 2 and "g0 level 4: not in the truth table" in out, f"a missing level: exit 2 (exit {code})")
    e = by_score(3)
    del e["A5"]
    code, out = run("--truth", table({"g0": [by_score(3)] * 4 + [e]}, "nopred"), "--games", "g0")
    check(code == 2 and "g0 level 4 A5" in out, f"a missing predicate: exit 2 (exit {code})")
    e = by_score(3)
    e["A2"]["verdict"] = "undetermined"
    code, out = run("--truth", table({"g0": [e] + [by_score(3)] * 4}, "badverdict"), "--games", "g0")
    check(code == 2 and "'undetermined'" in out and "G5:" not in out,
          f"a verdict 'undetermined': exit 2, no verdict printed (exit {code})")


def part8():
    print("== 8. no reading of the real table before the hand check")
    real_result, real_truth = G.HANDCHECK_RESULT, G.TRUTH
    G.HANDCHECK_RESULT = os.path.join(TMP, "no-such-HANDCHECK_RESULT.md")
    G.TRUTH = os.path.join(TMP, "no-such-gvgai.json")
    opened = []
    real_open = builtins.open

    def spy(p, *a, **k):
        if os.path.abspath(str(p)) in (os.path.abspath(G.TRUTH), os.path.abspath(real_truth)):
            opened.append(p)
        return real_open(p, *a, **k)
    builtins.open = spy
    try:
        code, out = run()
    finally:
        builtins.open = real_open
        G.HANDCHECK_RESULT, G.TRUTH = real_result, real_truth
    check(code == 3 and "refused" in out and not opened,
          f"default run without the hand-check result: exit 3, truth table not opened (exit {code}, opened {len(opened)})")
    if os.path.exists(real_result):
        check(True, "docs/truth/HANDCHECK_RESULT.md exists: the author's command was not run here")
    else:
        p = subprocess.run([sys.executable, os.path.join(HERE, "g5_reading.py")], capture_output=True, text=True,
                           cwd=REPO)
        check(p.returncode == 3 and "refused" in p.stdout,
              f"the author's command today, as a separate process: refused (exit {p.returncode})")


def part9():
    print("== 9. test options")
    _, out = run_scores([3] * 65 + [4] * 60, "label")
    check("[test options: not G5]" in out.splitlines()[0], "--truth or --games: the console says 'not G5'")


if __name__ == "__main__":
    for part in (part1, part2, part3, part4, part5, part6, part7, part8, part9):
        part()
    print("OK" if not FAILS else f"FAILED: {len(FAILS)}")
    sys.exit(1 if FAILS else 0)
