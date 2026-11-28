"""
test_handcheck.py -- tests of scripts/handcheck_app.py and scripts/handcheck_report.py.  Reads committed files
only; every row and answer it makes is kept in a temporary folder, never under docs/truth/.  It reads neither
docs/truth/handcheck_answers.json nor any answer of the author.

1. The committed rows file, of the old form (with the generator's verdicts; one answer was given on it and discarded
   on 28 November 2026), equals what the old build gives from docs/truth/gvgai.json at the blob it was built from,
   pinned below by its git blob hash; that blob's content has the hash the rows file records; one row per drawn game,
   level and predicate; each deciding line is the line of the file it names.  (Changed 28 November 2026: until then
   it compared the rows file with a build from docs/truth/gvgai.json as it now stands, which a generator fix would
   break although the rows file must stay as answered.  The old build, removed from the app, is kept here for this
   check alone.)
2. The app cannot show a verdict, even with docs/truth/gvgai.json present: it refuses the committed rows file, which
   carries verdicts, before any window opens; it refuses the existing readings file, which explains the generator's
   verdict, and a readings file whose writing script names docs/truth/gvgai.json; built from synthetic readings in
   a temporary folder, the 100 rows and fresh round 1's 50 rows carry no verdict, and neither building them nor
   showing every one of them in the window opens docs/truth/gvgai.json.  (Changed 28 November 2026: until then this
   part checked that the squares the app coloured numbered what the generator counted, a display the blind form
   removes.)
3. The window, driven by its own methods on the synthetic blind rows: answers holds, fails and unsure are kept after
   every click, keys 1 to 3 do nothing while the note has the focus, Back and Skip move without answering, a new
   window resumes at the row the last one left, and Finish marks the answers finished; an answers file of the old
   form is refused.
4. The report refuses the committed rows file (the old form) and the answers so made, 3 of 100 rows, and writes
   nothing (changed 28 November 2026 for the blind form; until then only the 3 of 100 refusal was checked).
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe -W error scripts\\test_handcheck.py > logs\\test_handcheck.log
"""
from __future__ import annotations

import builtins
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import handcheck_app as app  # noqa: E402
import handcheck_report as report  # noqa: E402

ROWS = os.path.join(app.TRUTH, "handcheck_rows.json")
OLD_READINGS = os.path.join(app.TRUTH, "handcheck_readings.json")
GVGAI = os.path.join(app.TRUTH, "gvgai.json")
# docs/truth/gvgai.json as committed in 3d6faa2 (25 October 2026), the version the committed rows were built from
PINNED_BLOB = "d2a71c20bd04feb31ee0854930c1d138ab60e037"


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def build_rows_v1(truth):
    """The old build of scripts/handcheck_app.py (before 28 November 2026), from a given truth table."""
    readings = app.read_json(OLD_READINGS)["readings"]
    questions = app.guide_questions()
    rows = []
    for game, other in app.drawn_games():
        gv = truth["games"][game]
        desc = gv["description"]
        for p in app.PRED:
            r = readings[f"{game}/{p}"]
            for lvl in (0, other):
                e = gv["levels"][str(lvl)][p]
                lvl_file = gv["levels"][str(lvl)]["level_file"]
                clauses = [{"in": "level" if c["file"] == lvl_file else "description", "line": c["line"],
                            "text": (c["text"] or "").strip(), "reads": c["reads"]} for c in e["clauses"]]
                level_clause = next((c for c in clauses if c["in"] == "level"), None)
                if r["deciding"][0] == "level":
                    where, line = "level", level_clause["line"]
                else:
                    where, line = "description", int(r["deciding"][1])
                text = app.file_lines(lvl_file if where == "level" else desc)[line - 1].strip()
                reading = r["reading"]
                if "{n}" in reading:
                    reading = reading.replace("{n}", re.search(r"places (\d+) sprite", level_clause["reads"]).group(1))
                rows.append({"id": f"{game}/{p}/{lvl}", "game": game, "level": lvl, "predicate": p,
                             "name": questions[p][0], "question": questions[p][1], "verdict": e["verdict"],
                             "description": desc, "level_file": lvl_file,
                             "deciding": {"in": where, "line": line, "text": text},
                             "reading": reading, "wrong_if": r["wrong_if"], "clauses": clauses})
    return rows


def test_rows_pinned():
    blob = subprocess.run(["git", "cat-file", "-p", PINNED_BLOB], cwd=app.REPO, capture_output=True, check=True).stdout
    data = app.read_json(ROWS)
    check(data["schema"] == "horizon.handcheck_rows.v1", "the committed rows file is of the old form")
    import hashlib
    check(hashlib.sha256(blob.replace(b"\r\n", b"\n")).hexdigest() == data["sources"]["docs/truth/gvgai.json"],
          "the pinned blob is the docs/truth/gvgai.json the rows file records")
    for p, h in data["sources"].items():
        if p != "docs/truth/gvgai.json":
            check(app.sha256(os.path.join(app.REPO, p)) == h, f"{p} unchanged since the rows were written")
    rows = data["rows"]
    check(build_rows_v1(json.loads(blob.decode("utf-8"))) == rows,
          "the rows file differs from the old build at the pinned blob")
    drawn = app.drawn_games()
    check(len(rows) == len(drawn) * len(app.PRED) * 2, "one row per drawn game, level and predicate")
    check(len({r["id"] for r in rows}) == len(rows), "row ids are unique")
    for r in rows:
        d = r["deciding"]
        path = r["description"] if d["in"] == "description" else r["level_file"]
        check(app.file_lines(path)[d["line"] - 1].strip() == d["text"], f"{r['id']}: deciding line text")
    print(f"rows (old form, as answered once and discarded): {len(rows)} rows on {len(drawn)} games; equal to the old "
          f"build from docs/truth/gvgai.json at blob {PINNED_BLOB}; every deciding line matches its file")


@contextmanager
def opens_traced():
    """Records the path of every file opened through open() while active."""
    seen, real = [], builtins.open

    def traced(file, *a, **k):
        seen.append(os.path.abspath(str(file)))
        return real(file, *a, **k)
    builtins.open = traced
    try:
        yield seen
    finally:
        builtins.open = real


def refused(fn):
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            fn()
        except SystemExit as e:
            return e.code == 3, buf.getvalue()
    return False, buf.getvalue()


def synthetic_readings(tmp, writer_text="# synthetic: reads third_party/gvgai only\n", name="readings.json"):
    writer = os.path.join(tmp, name + ".py")
    with open(writer, "w", encoding="utf-8") as f:
        f.write(writer_text)
    ids = [f"{g}/{p}/{lv}" for g, k in app.drawn_games() for p in app.PRED for lv in (0, k)]
    ids += [f"{d['game']}/{p}/{lv}" for d in app.read_json(os.path.join(app.TRUTH, "handcheck_fresh_1.json"))["games"]
            for p in app.PRED for lv in d["levels"]]
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema": app.READINGS_SCHEMA, "written_by": writer,
                   "readings": {i: {"reading": f"synthetic reading of {i}", "lines": {"description": [1], "level": [1]}}
                                for i in ids}}, f)
    return path


def test_no_verdict(tmp):
    check(os.path.exists(GVGAI), "docs/truth/gvgai.json is present")
    gv = os.path.abspath(GVGAI)
    import tkinter
    real_tk = tkinter.Tk

    def no_window(*a, **k):
        raise AssertionError("a window was opened")
    tkinter.Tk = no_window
    try:
        ok, out = refused(lambda: app.main(["--answers", os.path.join(tmp, "a.json")]))
    finally:
        tkinter.Tk = real_tk
    check(ok and "not horizon.handcheck_rows.v2" in out, "the app refuses the committed rows file before any window")
    ok, out = refused(lambda: app.load_rows(os.path.join(tmp, "r0.json"), 0, OLD_READINGS))
    check(ok and "not horizon.handcheck_readings.v2" in out, "the app refuses the readings that explain the verdict")
    bad = synthetic_readings(tmp, "TRUTH = 'docs/truth/gvgai.json'\n", "bad.json")
    ok, out = refused(lambda: app.load_rows(os.path.join(tmp, "r0.json"), 0, bad))
    check(ok and "names gvgai.json" in out, "the app refuses readings whose writer names docs/truth/gvgai.json")
    ok, out = refused(lambda: app.load_rows(os.path.join(tmp, "r0.json"), 0, os.path.join(tmp, "none.json")))
    check(ok and "the author's decision" in out, "the app refuses when no source readings exist")
    check(not os.path.exists(os.path.join(tmp, "r0.json")), "no rows file is written by a refused build")

    good = synthetic_readings(tmp)
    import tkinter as tk
    built = {}
    with opens_traced() as seen:
        for rnd, n in ((0, 100), (1, 50)):
            rows_path, _ = app.paths_for(rnd, tmp)
            data, changed = app.load_rows(rows_path, rnd, good)
            rows = data["rows"]
            check(len(rows) == n, f"round {rnd}: {n} rows")
            check(not any(k in r for r in rows for k in app.VERDICT_KEYS), f"round {rnd}: no row carries a verdict")
            check(app.blind_refusal(data, "x") is None, f"round {rnd}: the rows are of the blind form")
            built[rnd] = (rows_path, rows)
            root = tk.Tk()
            root.withdraw()
            w = app.App(root, rows, app.Answers(os.path.join(tmp, f"show{rnd}.json"), rows_path,
                                                app.sha256(rows_path)), changed)
            for i in range(len(rows)):
                w.i = i
                w.show()
                shown = w.info.get("1.0", "end")
                check("verdict" not in shown.lower(), f"{rows[i]['id']}: no verdict in the window")
            root.destroy()
    check(gv not in seen, "docs/truth/gvgai.json was opened while building or showing the rows")
    check(app.read_json(built[0][0])["truth_blob"] == PINNED_BLOB,
          "the 100 rows record the blob of docs/truth/gvgai.json at HEAD")
    print("no verdict: the committed rows file refused before any window, with docs/truth/gvgai.json present; the old "
          "readings and a writer naming docs/truth/gvgai.json refused; 100 and 50 synthetic blind rows built and every "
          "one shown without opening docs/truth/gvgai.json; the rows record its blob")
    return built


def test_window(rows_path, rows, tmp):
    import tkinter as tk
    path = os.path.join(tmp, "answers.json")
    sha = app.sha256(rows_path)

    def window():
        root = tk.Tk()
        root.withdraw()
        return root, app.App(root, rows, app.Answers(path, rows_path, sha), [])

    root, w = window()
    check(w.i == 0, "a first start begins at row 1")
    w.root.focus_get = lambda: None
    w.key("holds")
    saved = app.read_json(path)
    check(saved["schema"] == app.ANSWERS_SCHEMA, "answers of the blind form")
    check(saved["answers"][rows[0]["id"]]["answer"] == "holds" and saved["position"] == 1, "holds is kept and moves on")
    w.note.set("the push at line 40 moves a second sprite")
    w.mark("fails")
    check(app.read_json(path)["answers"][rows[1]["id"]]["note"] == "the push at line 40 moves a second sprite",
          "the note is kept with the answer")
    w.root.focus_get = lambda: w.note_entry
    w.key("holds")
    check(w.i == 2 and rows[2]["id"] not in app.read_json(path)["answers"], "keys do nothing while typing a note")
    w.root.focus_get = lambda: None
    w.key("unsure")
    w.skip()
    w.note.set("to look at again")
    w.back()
    check(w.i == 3, "skip then back returns to the skipped row")
    w.skip()
    check(app.read_json(path)["answers"][rows[4]["id"]] == {"note": "to look at again", "answer": None},
          "a note without an answer is kept")
    pos = w.i
    w.close()
    root, w = window()
    check(w.i == pos, f"a new window resumes at row {pos + 1}, where the last one left")
    check(w.ans.answered(rows) == 3, "three rows answered after resuming")
    w.finish(ask=False)
    saved = app.read_json(path)
    check(saved["finished_at"] is not None, "finish marks the answers finished")
    old = os.path.join(tmp, "old_answers.json")
    with open(old, "w", encoding="utf-8") as f:
        json.dump({"schema": "horizon.handcheck_answers.v1", "answers": {}}, f)
    ok, out = refused(lambda: app.Answers(old, rows_path, sha))
    check(ok and "discarded on 28 November 2026" in out, "an answers file of the old form is refused")
    print(f"window: holds, fails and unsure kept after each click; keys ignored while typing; back and skip; resumed at "
          f"row {pos + 1}; finish recorded; old answers refused")
    return path


def test_report(rows_path, rows, path, tmp):
    out = os.path.join(tmp, "RESULT.md")
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = report.main(["--rows", ROWS, "--answers", path, "--out", out])
    check(code == 3 and "not horizon.handcheck_rows.v2" in buf.getvalue(), "the report refuses the old rows file")
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = report.main(["--rows", rows_path, "--answers", path, "--out", out])
    check(code == 3, f"the report refuses incomplete answers (exit {code})")
    check(f"3 of {len(rows)} rows answered" in buf.getvalue(), "the refusal gives the count answered")
    check(not os.path.exists(out), "nothing is written")
    print(f"report: refuses the old rows file, and 3 of {len(rows)} answered blind rows, and writes nothing")


if __name__ == "__main__":
    test_rows_pinned()
    with tempfile.TemporaryDirectory() as tmp:
        built = test_no_verdict(tmp)
        rows_path, rows = built[0]
        p = test_window(rows_path, rows, tmp)
        test_report(rows_path, rows, p, tmp)
    print("OK")
