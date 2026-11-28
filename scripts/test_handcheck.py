"""
test_handcheck.py -- tests of scripts/handcheck_app.py and scripts/handcheck_report.py.  Reads committed files
only; every row and answer it makes is kept in a temporary folder, never under docs/truth/.  It reads no answer of
the author.

1. The rows files.  The blind rows, docs/truth/handcheck_rows.json and docs/truth/handcheck_fresh_rows_1.json, equal
   what the app builds now from their committed sources (the draws, the guide's questions, the source readings of
   scripts/handcheck_readings_source.py), carry no verdict, one row per drawn game, level and predicate, and are
   pinned to docs/truth/gvgai.json at the blob pinned below, the blob at HEAD when they were built.  The rows file
   of the old form (with the generator's verdicts; one answer was given on it and discarded on 28 November 2026),
   as last committed in OLD_ROWS_COMMIT, equals the old build from docs/truth/gvgai.json at that same blob, whose
   content has the hash the old file records.  (Changed 28 November 2026, twice: until the first change this part
   compared the old rows file with a build from docs/truth/gvgai.json as it now stands, which a generator fix
   would break although the rows file must stay as answered; until the second, the old file was at the rows
   file's path and no blind rows existed.)
2. The app cannot show a verdict, even with docs/truth/gvgai.json present: it refuses a rows file of the old form,
   before any window opens; it refuses the readings that explain the generator's verdict, and readings whose
   writing script names docs/truth/gvgai.json; and showing every one of the 150 committed blind rows in the window
   (the rows loaded first, which hashes their sources, the guide among them, without showing them) opens neither docs/truth/gvgai.json nor any file listed as not to be opened in docs/truth/handcheck_seen.json,
   and the right pane holds none of the words verdict, holds and fails beyond the fixed line naming the keys.
3. The window, driven by its own methods on the committed blind rows: answers holds, fails and unsure are kept after
   every click, keys 1 to 3 do nothing while the note has the focus, Back and Skip move without answering, a new
   window resumes at the row the last one left, and Finish marks the answers finished; an answers file of the old
   form is refused.
4. The report refuses the old rows file and the answers so made, 3 of 100 rows, and writes nothing.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe -W error scripts\\test_handcheck.py > logs\\test_handcheck.log
"""
from __future__ import annotations

import builtins
import hashlib
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
FRESH_ROWS = os.path.join(app.TRUTH, "handcheck_fresh_rows_1.json")
OLD_READINGS = os.path.join(app.TRUTH, "handcheck_readings.json")
GVGAI = os.path.join(app.TRUTH, "gvgai.json")
SEEN = os.path.join(app.TRUTH, "handcheck_seen.json")
# docs/truth/gvgai.json as committed in 3d6faa2 (25 October 2026): the blob the old rows were built from, and the blob
# at HEAD when the blind rows were built on 28 November 2026
PINNED_BLOB = "d2a71c20bd04feb31ee0854930c1d138ab60e037"
OLD_ROWS_COMMIT = "8d53df0"


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def git_show(spec):
    return subprocess.run(["git", "show", spec], cwd=app.REPO, capture_output=True, check=True).stdout


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


def test_rows():
    blob = git_show(PINNED_BLOB)
    for rnd, path, n in ((0, ROWS, 100), (1, FRESH_ROWS, 50)):
        data, changed = app.load_rows(path, rnd)
        check(not changed, f"round {rnd}: sources changed since the rows were written: {changed}")
        check(app.build_rows(rnd)["rows"] == data["rows"], f"round {rnd}: the rows differ from a build now")
        check(len(data["rows"]) == n and len({r["id"] for r in data["rows"]}) == n, f"round {rnd}: {n} unique rows")
        check(app.blind_refusal(data, "x") is None, f"round {rnd}: blind form, no verdict")
        check(data["truth_blob"] == PINNED_BLOB, f"round {rnd}: pinned to blob {PINNED_BLOB}")
    old = json.loads(git_show(f"{OLD_ROWS_COMMIT}:docs/truth/handcheck_rows.json").decode("utf-8"))
    check(old["schema"] == "horizon.handcheck_rows.v1", "the old rows file is of the old form")
    check(hashlib.sha256(blob.replace(b"\r\n", b"\n")).hexdigest() == old["sources"]["docs/truth/gvgai.json"],
          "the pinned blob is the docs/truth/gvgai.json the old rows file records")
    check(build_rows_v1(json.loads(blob.decode("utf-8"))) == old["rows"],
          "the old rows file differs from the old build at the pinned blob")
    print(f"rows: the 100 blind rows and fresh round 1's 50 equal a build now from their sources, carry no verdict and "
          f"are pinned to docs/truth/gvgai.json at blob {PINNED_BLOB}; the old rows file of {OLD_ROWS_COMMIT} (as "
          "answered once and discarded) equals the old build at that blob")


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


def synthetic_readings(tmp, writer_text, name):
    writer = os.path.join(tmp, name + ".py")
    with open(writer, "w", encoding="utf-8") as f:
        f.write(writer_text)
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema": app.READINGS_SCHEMA, "written_by": writer, "readings": {}}, f)
    return path


def test_no_verdict(tmp):
    check(os.path.exists(GVGAI), "docs/truth/gvgai.json is present")
    old_dir = os.path.join(tmp, "old")
    os.makedirs(old_dir)
    with open(os.path.join(old_dir, "handcheck_rows.json"), "wb") as f:
        f.write(git_show(f"{OLD_ROWS_COMMIT}:docs/truth/handcheck_rows.json"))
    import tkinter
    real_tk = tkinter.Tk

    def no_window(*a, **k):
        raise AssertionError("a window was opened")
    tkinter.Tk = no_window
    try:
        ok, out = refused(lambda: app.main(["--out-dir", old_dir, "--answers", os.path.join(tmp, "a.json")]))
    finally:
        tkinter.Tk = real_tk
    check(ok and "not horizon.handcheck_rows.v2" in out, "the app refuses a rows file of the old form before any window")
    ok, out = refused(lambda: app.load_rows(os.path.join(tmp, "r0.json"), 0, OLD_READINGS))
    check(ok and "not horizon.handcheck_readings.v2" in out, "the app refuses the readings that explain the verdict")
    bad = synthetic_readings(tmp, "TRUTH = 'docs/truth/gvgai.json'\n", "bad.json")
    ok, out = refused(lambda: app.load_rows(os.path.join(tmp, "r0.json"), 0, bad))
    check(ok and "names gvgai.json" in out, "the app refuses readings whose writer names docs/truth/gvgai.json")
    check(not os.path.exists(os.path.join(tmp, "r0.json")), "no rows file is written by a refused build")

    forbidden = [os.path.abspath(GVGAI)] + [os.path.abspath(os.path.join(app.REPO, p))
                                            for p in app.read_json(SEEN)["must_not_open"] if " " not in p]
    import tkinter as tk
    shown_rows = 0
    loaded = [(rnd, path) + app.load_rows(path, rnd) for rnd, path in ((0, ROWS), (1, FRESH_ROWS))]
    with opens_traced() as seen:
        for rnd, path, data, changed in loaded:
            rows = data["rows"]
            root = tk.Tk()
            root.withdraw()
            w = app.App(root, rows, app.Answers(os.path.join(tmp, f"show{rnd}.json"), path, app.sha256(path)), changed)
            for i in range(len(rows)):
                w.i = i
                w.show()
                text = w.info.get("1.0", "end").replace("1 holds, 2 fails, 3 unsure.", "")
                check(not re.search(r"\b(verdict|holds|fails)\b", text, re.I), f"{rows[i]['id']}: no verdict shown")
                shown_rows += 1
            root.destroy()
    opened = sorted({p for p in seen if p in forbidden})
    check(not opened, f"files not to be opened were opened: {opened}")
    print(f"no verdict: a rows file of the old form refused before any window, with docs/truth/gvgai.json present; the "
          f"old readings and a writer naming docs/truth/gvgai.json refused; all {shown_rows} committed blind rows shown "
          f"without opening docs/truth/gvgai.json or any of the {len(forbidden) - 1} files the register lists")


def test_window(tmp):
    import tkinter as tk
    data, _ = app.load_rows(ROWS, 0)
    rows = data["rows"]
    path = os.path.join(tmp, "answers.json")
    sha = app.sha256(ROWS)

    def window():
        root = tk.Tk()
        root.withdraw()
        return root, app.App(root, rows, app.Answers(path, ROWS, sha), [])

    root, w = window()
    check(w.i == 0, "a first start begins at row 1")
    w.root.focus_get = lambda: None
    w.key("holds")
    saved = app.read_json(path)
    check(saved["schema"] == app.ANSWERS_SCHEMA, "answers of the blind form")
    check(saved["answers"][rows[0]["id"]]["answer"] == "holds" and saved["position"] == 1, "holds is kept and moves on")
    w.note.set("a note")
    w.mark("fails")
    check(app.read_json(path)["answers"][rows[1]["id"]]["note"] == "a note", "the note is kept with the answer")
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
    check(app.read_json(path)["finished_at"] is not None, "finish marks the answers finished")
    old = os.path.join(tmp, "old_answers.json")
    with open(old, "w", encoding="utf-8") as f:
        json.dump({"schema": "horizon.handcheck_answers.v1", "answers": {}}, f)
    ok, out = refused(lambda: app.Answers(old, ROWS, sha))
    check(ok and "discarded on 28 November 2026" in out, "an answers file of the old form is refused")
    print(f"window: holds, fails and unsure kept after each click; keys ignored while typing; back and skip; resumed at "
          f"row {pos + 1}; finish recorded; old answers refused")
    return path, rows


def test_report(path, rows, tmp):
    out = os.path.join(tmp, "RESULT.md")
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = report.main(["--rows", os.path.join(tmp, "old", "handcheck_rows.json"), "--answers", path, "--out", out])
    check(code == 3 and "not horizon.handcheck_rows.v2" in buf.getvalue(), "the report refuses the old rows file")
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = report.main(["--rows", ROWS, "--answers", path, "--out", out])
    check(code == 3, f"the report refuses incomplete answers (exit {code})")
    check(f"3 of {len(rows)} rows answered" in buf.getvalue(), "the refusal gives the count answered")
    check(not os.path.exists(out), "nothing is written")
    print(f"report: refuses the old rows file, and 3 of {len(rows)} answered blind rows, and writes nothing")


if __name__ == "__main__":
    test_rows()
    with tempfile.TemporaryDirectory() as tmp:
        test_no_verdict(tmp)
        p, rows = test_window(tmp)
        test_report(p, rows, tmp)
    print("OK")
