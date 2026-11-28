"""
test_handcheck_report.py -- tests of scripts/handcheck_report.py on synthetic files only: synthetic truth tables,
rows, answers, resolutions and fresh rounds, all in a temporary folder.  No file under docs/truth/ is read or written,
and the author's answers are never read.

The synthetic hand check: 10 games g00 .. g09, levels 0 and 1, 5 predicates, 100 rows, every verdict "holds" unless a
case changes it; the confirmatory units of the diff are g00 .. g09 and c00 .. c04; fresh rounds draw from f00 .. f09.

Checks:
    1. refusals (exit 3, nothing written): a row without an answer; answers not marked finished; a fresh row without
       an answer; rows of the old form, with the generator's verdict in them; answers of the old form (agree,
       disagree, unsure, schema v1);
    2. a clean hand check: every row agreed, no fix, fresh round 1 agreed: G4: PASS, 0 of 100 errors, no diff;
    3. a disagreement resolved from the source and fixed: G4: PASS, 1 of 100 errors (1.0%), the fix and its commit
       listed, the rerun's diff names the unit;
    4. an unsure row: resolved with the generator right, it is not an error and stays in the denominator (0 of 100);
       resolved with the generator wrong, it is an error (1 of 100) and is reported apart from the disagreements;
       left without a resolution, no verdict;
    5. incomplete resolutions give no verdict (exit 2): no source line; an error without the commit of its fix; a
       source verdict the generator does not give after the fix (the fix was not made);
    6. a fix that flips a row the author marked agree: without a resolution, no verdict; resolved with the new verdict,
       G4 passes and the row is listed and counted as an error; resolved with the old verdict (a wrong fix), no verdict;
    7. failure form (i): a disagreement the source does not resolve gives G4: FAIL, condition (i), VOID at once, even
       before any fresh round; the same in a fresh round;
    8. failure form (ii): an error in fresh round 1 gives the first failure, naming round 2 and seed 20261129; an
       error in round 2 too gives the second failure, VOID; round 2 clean gives PASS after the first failure; a fresh
       row marked disagree that the source resolves in the generator's favour is not a disagreement; round 2 without a
       failure of round 1, no verdict;
    9. consistency: fresh round 1 missing, fresh rows that are not the drawn games, answers kept against another rows
       file, rows that name no truth_blob, a fresh round with no pinned truth table: no verdict.

Changed 28 November 2026 to the blind form of the hand check (PREREG Section 5): the synthetic rows carry no verdict
and name the truth table they are compared with by blob ("before", read from the case's folder by --blob-dir); the
synthetic author answers holds, fails or unsure.  The cases are still written in terms of agree and disagree, which
the test turns into the answer that agrees or disagrees with the generator's verdict.  Until then the rows carried
the verdict and the answers were agree, disagree or unsure.
Run: D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\test_handcheck_report.py > logs\\test_handcheck_report.log
"""
import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import handcheck_report as R  # noqa: E402

FAILS = []
TMP = tempfile.mkdtemp(prefix="handcheck-report-test-")
HAND = [f"g{i:02d}" for i in range(10)]
CONF = HAND + [f"c{i:02d}" for i in range(5)]
FRESH1 = [f"f{i:02d}" for i in range(5)]
FRESH2 = [f"f{i:02d}" for i in range(5, 10)]
ALL = HAND + CONF[10:] + FRESH1 + FRESH2
PRED = R.PRED
N = [0]


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        FAILS.append(what)


def truth(over=None):
    over = over or {}
    return {"games": {g: {"deterministic": True, "levels": {str(lv): {p: {"verdict": over.get((g, lv, p), "holds"),
                                                                           "clauses": []} for p in PRED}
                                                              for lv in range(5)}} for g in ALL}}


def rows_for(games, blob="before"):
    out = []
    for g in games:
        for p in PRED:
            for lv in (0, 1):
                out.append({"id": f"{g}/{p}/{lv}", "game": g, "level": lv, "predicate": p, "name": p,
                            "description": f"{g}.txt", "level_file": f"{g}_lvl{lv}.txt", "reading": "",
                            "highlight": {"description": [], "level": []}})
    return {"schema": R.ROWS_SCHEMA, "truth_blob": blob, "rows": out}


def answers_for(rows, t, marks=None, finished=True, sha=None):
    """The author's answers: agree gives the generator's verdict in t, disagree the other one, unsure stays."""
    marks = marks or {}

    def given(r):
        m = marks.get(r["id"], "agree")
        v = t["games"][r["game"]]["levels"][str(r["level"])][r["predicate"]]["verdict"]
        return {"agree": v, "disagree": "fails" if v == "holds" else "holds"}.get(m, m)
    return {"schema": R.ANSWERS_SCHEMA, "rows_sha256": sha, "started_at": "s", "updated_at": "u",
            "finished_at": "f" if finished else None,
            "answers": {r["id"]: {"answer": given(r), "note": ""} for r in rows["rows"]}}


def dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def case(before=None, after=None, marks=None, res=None, fresh=None, unanswered=(), finished=True, bad_sha=False,
         old_rows=False, old_answers=False, no_blob=False):
    """fresh: {round: dict(games=[...], truth=t, marks={...}, extra_row=False, pin=False)}: truth is the truth table
    the round is compared with, kept as blob "fresh<round>" and named in the resolutions file unless pin is False.  Returns
    (code, console, result)."""
    N[0] += 1
    d = os.path.join(TMP, f"c{N[0]:02d}")
    os.makedirs(d)
    tb = truth(before)
    ta = truth(after if after is not None else before)
    rows = rows_for(HAND)
    if old_rows:
        rows = {"schema": "horizon.handcheck_rows.v1", "rows": [dict(r, verdict="holds") for r in rows["rows"]]}
    if no_blob:
        del rows["truth_blob"]
    dump(os.path.join(d, "rows.json"), rows)
    ans = answers_for(rows, tb, marks, finished, None if bad_sha else R.sha256(os.path.join(d, "rows.json")))
    for rid in unanswered:
        ans["answers"][rid]["answer"] = None
    if old_answers:
        ans["schema"] = "horizon.handcheck_answers.v1"
        for e in ans["answers"].values():
            e["answer"] = "agree"
    dump(os.path.join(d, "answers.json"), ans)
    pins = {str(rnd): f"fresh{rnd}" for rnd, f in (fresh or {}).items() if f.get("pin", True)}
    dump(os.path.join(d, "res.json"), {"fresh_truth_blob": pins, "resolutions": res or {}})
    dump(os.path.join(d, "before.json"), tb)
    dump(os.path.join(d, "after.json"), ta)
    for rnd, f in (fresh or {}).items():
        dump(os.path.join(d, f"handcheck_fresh_{rnd}.json"),
             {"round": rnd, "seed": {1: 20261128, 2: 20261129}[rnd],
              "games": [{"game": g, "levels": [0, 1]} for g in f["games"]]})
        ft = truth(f.get("truth"))
        dump(os.path.join(d, f"fresh{rnd}.json"), ft)
        fr = rows_for(f["games"], blob=None)
        fa = answers_for(fr, ft, f.get("marks"))
        if f.get("extra_row"):
            fr["rows"].append(dict(fr["rows"][0], id="zz/A1/0", game="zz"))
            fa["answers"]["zz/A1/0"] = {"answer": "holds", "note": ""}
        dump(os.path.join(d, f"handcheck_fresh_rows_{rnd}.json"), fr)
        for rid in f.get("unanswered", ()):
            fa["answers"][rid]["answer"] = None
        dump(os.path.join(d, f"handcheck_fresh_answers_{rnd}.json"), fa)
    out = os.path.join(d, "RESULT.md")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = R.main(["--out", out, "--rows", os.path.join(d, "rows.json"), "--answers", os.path.join(d, "answers.json"),
                       "--resolutions", os.path.join(d, "res.json"), "--blob-dir", d,
                       "--truth-after", os.path.join(d, "after.json"), "--fresh-dir", d, "--games", ",".join(CONF)])
    text = None
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            text = f.read()
    return code, buf.getvalue(), text


OK1 = {1: dict(games=FRESH1)}
SRC = [{"file": "third_party/gvgai/src/ontology/avatar/MovingAvatar.java", "line": 42}]


def fixed(va, commit="c0ffee", note=""):
    return {"resolved": True, "source": SRC, "generator_commit": commit, "verdict_after": va, "note": note}


def part1():
    print("== 1. refusals")
    code, out, text = case(fresh=OK1, unanswered=("g03/A4/1",))
    check(code == 3 and "99 of 100 rows answered" in out and text is None, f"a row without an answer: exit {code}, nothing written")
    code, out, text = case(fresh=OK1, finished=False)
    check(code == 3 and text is None, f"answers not marked finished: exit {code}, nothing written")
    code, out, text = case(fresh={1: dict(games=FRESH1, unanswered=("f02/A1/0",))})
    check(code == 3 and "fresh round 1" in out and text is None, f"a fresh row without an answer: exit {code}")
    code, out, text = case(fresh=OK1, old_rows=True)
    check(code == 3 and "not horizon.handcheck_rows.v2" in out and "discarded on 28 November 2026" in out
          and text is None, f"rows of the old form, with the generator's verdict: exit {code}, nothing written")
    code, out, text = case(fresh=OK1, old_answers=True)
    check(code == 3 and "given with the verdict visible" in out and text is None,
          f"answers of the old form (agree, disagree, unsure): exit {code}, nothing written")


def part2():
    print("== 2. a clean hand check")
    code, out, text = case(fresh=OK1)
    check(code == 0 and "G4: PASS" in out and "0 of 100 rows answered (0.0%)" in text and "No verdict changed." in text,
          f"all agreed, no fix, round 1 agreed: PASS, 0 of 100, no diff (exit {code})")


def part3():
    print("== 3. a disagreement resolved and fixed")
    k = ("g00", 0, "A2")
    code, out, text = case(after={k: "fails"}, marks={"g00/A2/0": "disagree"}, res={"g00/A2/0": fixed("fails", "abc123")},
                           fresh=OK1)
    check(code == 0 and "1 of 100 rows answered (1.0%)" in text and "- abc123: g00/A2/0" in text
          and "- g00, level 0, A2: holds before, fails after" in text
          and "Answers that differ from the generator's verdict: 1" in text,
          f"PASS; error 1 of 100; fix abc123 listed; diff names g00 level 0 A2 (exit {code})")


def part4():
    print("== 4. an unsure row")
    right = {"resolved": True, "source": SRC, "generator_commit": None, "verdict_after": "holds", "note": ""}
    code, out, text = case(marks={"g04/A5/1": "unsure"}, res={"g04/A5/1": right}, fresh=OK1)
    check(code == 0 and "0 of 100 rows answered" in text and "Marked unsure: 1, of which the source found the generator "
          "right on 1" in text and "Answers that differ from the generator's verdict: 0" in text,
          f"resolved, generator right: not an error, denominator 100, apart from disagreements (exit {code})")
    code, out, text = case(after={("g04", 1, "A5"): "fails"}, marks={"g04/A5/1": "unsure"},
                           res={"g04/A5/1": fixed("fails")}, fresh=OK1)
    check(code == 0 and "1 of 100 rows answered (1.0%)" in text and "Marked unsure: 1, of which the source found the "
          "generator right on 0" in text and "Answers that differ from the generator's verdict: 0" in text,
          f"resolved, generator wrong: an error, reported as unsure, not as a disagreement (exit {code})")
    code, out, _ = case(marks={"g04/A5/1": "unsure"}, fresh=OK1)
    check(code == 2 and "g04/A5/1: marked unsure; no resolution" in out, f"unsure without a resolution: no verdict (exit {code})")


def part5():
    print("== 5. incomplete resolutions")
    m, k = {"g00/A2/0": "disagree"}, {("g00", 0, "A2"): "fails"}
    nosrc = dict(fixed("fails"), source=[])
    code, out, _ = case(after=k, marks=m, res={"g00/A2/0": nosrc}, fresh=OK1)
    check(code == 2 and "without a GVGAI source file and line" in out, f"no source line: no verdict (exit {code})")
    code, out, _ = case(after=k, marks=m, res={"g00/A2/0": fixed("fails", commit=None)}, fresh=OK1)
    check(code == 2 and "without the commit of its fix" in out, f"an error without its commit: no verdict (exit {code})")
    code, out, _ = case(marks=m, res={"g00/A2/0": fixed("fails")}, fresh=OK1)
    check(code == 2 and "the source gives fails, the generator now gives holds" in out,
          f"the fix not made (generator unchanged): no verdict (exit {code})")


def part6():
    print("== 6. a fix that flips a row marked agree")
    k = {("g00", 0, "A2"): "fails", ("g01", 1, "A3"): "fails"}
    m = {"g00/A2/0": "disagree"}
    r0 = {"g00/A2/0": fixed("fails")}
    code, out, _ = case(after=k, marks=m, res=r0, fresh=OK1)
    check(code == 2 and "g01/A3/1: marked agree, and a fix flipped it; no resolution" in out,
          f"flipped agreed row without a resolution: no verdict (exit {code})")
    code, out, text = case(after=k, marks=m, res=dict(r0, **{"g01/A3/1": fixed("fails")}), fresh=OK1)
    check(code == 0 and "of them agreeing with the author before the fix: 1 (g01/A3/1" in text and "2 of 100 rows answered" in text,
          f"resolved with the new verdict: PASS, listed, counted as an error (exit {code})")
    code, out, _ = case(after=k, marks=m, res=dict(r0, **{"g01/A3/1": dict(fixed("holds"), generator_commit=None)}),
                        fresh=OK1)
    check(code == 2 and "g01/A3/1: the source gives holds, the generator now gives fails" in out,
          f"resolved with the old verdict, a wrong fix: caught, no verdict (exit {code})")


def part7():
    print("== 7. failure form (i)")
    un = {"resolved": False, "source": SRC, "generator_commit": None, "verdict_after": None, "note": "not determined"}
    code, out, text = case(marks={"g02/A4/0": "disagree"}, res={"g02/A4/0": un})
    check(code == 1 and "G4: FAIL" in out and "condition (i)" in out and "VOID at once" in out and "row g02/A4/0" in out,
          f"an unresolvable disagreement, no fresh round yet: FAIL (i), VOID at once (exit {code})")
    code, out, _ = case(fresh={1: dict(games=FRESH1, marks={"f01/A1/1": "disagree"})}, res={"fresh1:f01/A1/1": un})
    check(code == 1 and "condition (i)" in out and "fresh round 1 f01/A1/1" in out,
          f"the same in fresh round 1: FAIL (i) (exit {code})")


def part8():
    print("== 8. failure form (ii)")
    kf = ("f01", 0, "A3")
    r1 = {1: dict(games=FRESH1, marks={"f01/A3/0": "disagree"})}
    code, out, _ = case(after={kf: "fails"}, res={"fresh1:f01/A3/0": fixed("fails", "fix2")}, fresh=r1)
    check(code == 1 and "first failure" in out and "fresh round 2 (seed 20261129)" in out and "VOID" not in out,
          f"an error in round 1: first failure, read again on round 2 (exit {code})")
    k2 = ("f06", 1, "A5")
    after = {kf: "fails", k2: "fails"}
    r12 = {1: r1[1], 2: dict(games=FRESH2, truth={kf: "fails"}, marks={"f06/A5/1": "disagree"})}
    code, out, _ = case(after=after, res={"fresh1:f01/A3/0": fixed("fails", "fix2"), "fresh2:f06/A5/1": fixed("fails", "fix3")},
                        fresh=r12)
    check(code == 1 and "second failure" in out and "VOID" in out, f"an error in round 2 too: second failure, VOID (exit {code})")
    r12c = {1: r1[1], 2: dict(games=FRESH2, truth={kf: "fails"})}
    code, out, text = case(after={kf: "fails"}, res={"fresh1:f01/A3/0": fixed("fails", "fix2")}, fresh=r12c)
    check(code == 0 and "G4: PASS" in out and "after the first failure on round 1" in out,
          f"round 2 clean: PASS after the first failure (exit {code})")
    right = {"resolved": True, "source": SRC, "generator_commit": None, "verdict_after": "holds", "note": ""}
    code, out, _ = case(fresh={1: dict(games=FRESH1, marks={"f03/A2/1": "disagree"})}, res={"fresh1:f03/A2/1": right})
    check(code == 0 and "G4: PASS" in out, f"a fresh disagree mark the source resolves for the generator: not a disagreement (exit {code})")
    code, out, _ = case(fresh={1: dict(games=FRESH1), 2: dict(games=FRESH2)})
    check(code == 2 and "round 1 showed no disagreement" in out, f"round 2 without a failure of round 1: no verdict (exit {code})")


def part9():
    print("== 9. consistency")
    code, out, _ = case()
    check(code == 2 and "fresh round 1 has not been checked" in out, f"no fresh round: no verdict (exit {code})")
    code, out, _ = case(fresh={1: dict(games=FRESH1, extra_row=True)})
    check(code == 2 and "not the drawn games" in out, f"fresh rows that are not the drawn games: no verdict (exit {code})")
    code, out, _ = case(fresh=OK1, bad_sha=True)
    check(code == 2 and "another version of the rows file" in out, f"answers kept against another rows file: no verdict (exit {code})")
    code, out, _ = case(fresh=OK1, no_blob=True)
    check(code == 2 and "names no truth_blob" in out, f"rows that name no truth_blob: no verdict (exit {code})")
    kf = ("f01", 0, "A3")
    code, out, _ = case(after={kf: "fails"}, res={"fresh1:f01/A3/0": fixed("fails", "fix2")},
                        fresh={1: dict(games=FRESH1, marks={"f01/A3/0": "disagree"}, pin=False),
                               2: dict(games=FRESH2, truth={kf: "fails"})})
    check(code == 2 and "fresh round 1: no fresh_truth_blob" in out,
          f"a fresh round with no pinned truth table: no verdict (exit {code})")


if __name__ == "__main__":
    for p in (part1, part2, part3, part4, part5, part6, part7, part8, part9):
        p()
    shutil.rmtree(TMP, ignore_errors=True)
    print("OK" if not FAILS else f"FAILED: {len(FAILS)}")
    sys.exit(1 if FAILS else 0)
