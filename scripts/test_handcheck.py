"""
test_handcheck.py -- tests of scripts/handcheck_app.py and scripts/handcheck_report.py.  Reads committed files
only; every answer it makes is kept in a temporary folder, never in docs/truth/handcheck_answers.json.

1. The rows file equals what the app builds from its sources now, has one row per drawn game, level and predicate,
   and each deciding line is the line of the file it names.
2. Where a verdict counts a sprite type in a level, the squares the app colours number what the generator counted.
3. The window, driven by its own methods: answers are kept after every click, keys 1 to 3 do nothing while the
   note has the focus, Back and Skip move without answering, a new window resumes at the row the last one left,
   and Finish marks the answers finished.
4. The report counts the answers so made and lists the disagreement and the unsure row with their notes.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe -W error scripts\\test_handcheck.py > logs\\test_handcheck.log
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import handcheck_app as app  # noqa: E402
import handcheck_report as report  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_rows():
    data, changed = app.load_rows()
    check(not changed, f"sources changed since the rows were written: {changed}")
    built = app.build_rows()
    check(built["rows"] == data["rows"], "the rows file differs from what the app builds now")
    drawn = app.drawn_games()
    rows = data["rows"]
    check(len(rows) == len(drawn) * len(app.PRED) * 2, "one row per drawn game, level and predicate")
    check(len({r["id"] for r in rows}) == len(rows), "row ids are unique")
    for r in rows:
        d = r["deciding"]
        path = r["description"] if d["in"] == "description" else r["level_file"]
        check(app.file_lines(path)[d["line"] - 1].strip() == d["text"], f"{r['id']}: deciding line text")
        for c in r["clauses"]:
            path = r["description"] if c["in"] == "description" else r["level_file"]
            check(1 <= c["line"] <= len(app.file_lines(path)), f"{r['id']}: clause line {c['line']} in {path}")
        check("{n}" not in r["reading"], f"{r['id']}: count left unfilled")
    print(f"rows: {len(rows)} rows on {len(drawn)} games; equal to a fresh build; every deciding line matches its file")
    return rows


def test_cells(rows):
    k = 0
    for r in rows:
        found = app.level_cells(r)
        if not found:
            continue
        c = next(c for c in r["clauses"] if c["in"] == "level")
        n = int(re.search(r"places (\d+) sprite", c["reads"]).group(1))
        check(len(found[1]) == n, f"{r['id']}: {len(found[1])} squares coloured, the generator counted {n}")
        k += 1
    print(f"cells: on all {k} rows that count a sprite in the level, the coloured squares equal the generator's count")


def test_window(rows, tmp):
    import tkinter as tk
    path = os.path.join(tmp, "answers.json")
    sha = app.sha256(app.ROWS)

    def window():
        root = tk.Tk()
        root.withdraw()
        return root, app.App(root, rows, app.Answers(path, sha), [])

    root, w = window()
    check(w.i == 0, "a first start begins at row 1")
    w.root.focus_get = lambda: None
    w.key("agree")
    saved = app.read_json(path)
    check(saved["answers"][rows[0]["id"]]["answer"] == "agree" and saved["position"] == 1, "agree is kept and moves on")
    w.note.set("the push at line 40 is a second sprite")
    w.mark("disagree")
    check(app.read_json(path)["answers"][rows[1]["id"]]["note"] == "the push at line 40 is a second sprite",
          "the note is kept with the answer")
    w.root.focus_get = lambda: w.note_entry
    w.key("agree")
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
    print(f"window: answers kept after each click; keys ignored while typing; back and skip; resumed at row {pos + 1}; "
          "finish recorded")
    return path


def test_report(path, tmp):
    out = os.path.join(tmp, "RESULT.md")
    buf = io.StringIO()
    with redirect_stdout(buf):
        check(report.main(["--answers", path, "--out", out]) == 0, "the report runs")
    with open(out, encoding="utf-8") as f:
        text = f.read()
    con = buf.getvalue()
    check(f"all: agree 1, disagree 1, unsure 1, no answer {len(rows) - 3}" in con, "the report's counts")
    check("the push at line 40 is a second sprite" in text, "the disagreement is listed with its note")
    check("## Every row marked unsure" in text and "to look at again" in text, "unsure rows and notes are listed")
    check("| clusters | 0, 3 | 10 | 3 |" in text, "games and levels covered")
    print("report: counts per predicate and game, the disagreement and the unsure row with notes, games and levels")


if __name__ == "__main__":
    rows = test_rows()
    test_cells(rows)
    with tempfile.TemporaryDirectory() as tmp:
        p = test_window(rows, tmp)
        test_report(p, tmp)
    print("OK")
