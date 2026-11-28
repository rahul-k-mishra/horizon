"""
handcheck_app.py -- a window for the author's hand check of the truth tables (docs/PREREG.md draft v0, Section 5).
Standard library only (Tkinter).  One row at a time: a predicate, on one level of one drawn game.  The hand check is
blind (PREREG Section 5, decided 28 November 2026): the window shows no verdict of the generator, and the author
answers holds, fails or unsure from the game's files and the reading alone.  The left pane shows the game's
description and the row's level file, with the lines the reading names highlighted; the right pane shows the
question, the reading and the files.

Changed 28 November 2026 to the blind form.  Until then the window showed the generator's verdict, its deciding line,
"what it says", "for the verdict to be wrong" and every clause the verdict rested on as the generator read it, and the
author answered agree, disagree or unsure; the rows were built from docs/truth/gvgai.json and
docs/truth/handcheck_readings.json, whose readings explain the generator's verdict.  That form was used for one
answer, which was discarded with the change.  The Guide button, which showed docs/truth/HANDCHECK_GUIDE.md, is
removed: the guide's examples state the generator's verdict on rows of sokoban,
labyrinthdual, painter, wrapsokoban and rivers, games of the hand check.
scripts/test_handcheck.py, part 1, keeps the check that the old rows file equals a build from docs/truth/gvgai.json
at the blob it was built from.

Reads:  logs/draw_handcheck.log (the 10 games and levels drawn by scripts/draw_handcheck.py; names and levels)
        or docs/truth/handcheck_fresh_<r>.json (a fresh round, scripts/draw_handcheck_fresh.py);
        docs/truth/HANDCHECK_GUIDE.md (the question of each predicate);
        docs/truth/handcheck_readings_source.json, schema horizon.handcheck_readings.v2, a reading per row derived
        from the vendored GVGAI source under third_party/gvgai, with the script that wrote it ("written_by");
        and the GVGAI files the rows name.
        It never opens docs/truth/gvgai.json.  It records the git blob of that file at HEAD in the rows file when it
        builds them (git rev-parse, which reads no verdict), for every round: scripts/handcheck_report.py compares
        the 100 answers with the truth table of that blob, and a fresh round's with the blob its resolutions name.
Refuses (exit 3): a readings file that is not of schema v2, or whose writing script names docs/truth/gvgai.json,
        scripts/truth_vgdl.py or docs/truth/handcheck_readings.json; a missing readings file (no reading derived
        from the source has been written yet); a rows file of the old form or with a verdict in it; an answers file
        of the old form.
Writes: the rows file, from the files above, only if it does not exist; and the answers file after every click, so
        that closing the window loses nothing and the next start resumes at the row where the last one stopped.
        Round 0 (the 100 rows): docs/truth/handcheck_rows.json and docs/truth/handcheck_answers.json.  Fresh round r:
        docs/truth/handcheck_fresh_rows_<r>.json and docs/truth/handcheck_fresh_answers_<r>.json.
Keys:   1 holds, 2 fails, 3 unsure (not while typing a note).

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\handcheck_app.py
Options: --round R     0 for the 100 rows (the default), 1 or 2 for a fresh round;
         --rows        write the rows file if it does not exist, print what it holds (no verdict), and stop;
         --answers P, --readings P, --out-dir D   for the tests.
When finished: scripts/handcheck_report.py compares the answers with the generator and writes
docs/truth/HANDCHECK_RESULT.md.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRUTH = os.path.join(REPO, "docs", "truth")
DRAW_LOG = os.path.join(REPO, "logs", "draw_handcheck.log")
GUIDE = os.path.join(TRUTH, "HANDCHECK_GUIDE.md")
READINGS = os.path.join(TRUTH, "handcheck_readings_source.json")
GAMES_DIR = "third_party/gvgai/examples/gridphysics"
TRUTH_REL = "docs/truth/gvgai.json"
ROWS_SCHEMA = "horizon.handcheck_rows.v2"
ANSWERS_SCHEMA = "horizon.handcheck_answers.v2"
READINGS_SCHEMA = "horizon.handcheck_readings.v2"
FORBIDDEN_IN_WRITER = ("gvgai.json", "truth_vgdl", "handcheck_readings.json")
VERDICT_KEYS = ("verdict", "wrong_if", "clauses")
PRED = ("A1", "A2", "A3", "A4", "A5")
CHOICES = ("holds", "fails", "unsure")


def rel(path):
    try:
        return os.path.relpath(path, REPO).replace("\\", "/")
    except ValueError:
        return path


def sha256(path):
    """Of the file with Windows line endings read as Unix ones, so that a checkout with either gives the same."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def refuse(msg):
    print(f"refused: {msg}")
    raise SystemExit(3)


def file_lines(path):
    with open(os.path.join(REPO, path), encoding="utf-8") as f:
        return f.read().splitlines()


def paths_for(rnd, out_dir=TRUTH):
    """(rows file, answers file) of a round."""
    if rnd == 0:
        return os.path.join(out_dir, "handcheck_rows.json"), os.path.join(out_dir, "handcheck_answers.json")
    return (os.path.join(out_dir, f"handcheck_fresh_rows_{rnd}.json"),
            os.path.join(out_dir, f"handcheck_fresh_answers_{rnd}.json"))


def drawn_games():
    """The games and second levels of the draw of 25 October 2026, in its order: [(game, level), ...], from the
    draw's console (changed 28 November 2026: until then from docs/truth/HANDCHECK.md, which also shows verdicts)."""
    with open(DRAW_LOG, encoding="utf-8") as f:
        m = re.search(r"^drawn: (.+)$", f.read(), re.M)
    found = re.findall(r"(\w+) \(levels 0 and (\d+)\)", m.group(1)) if m else []
    if not found:
        raise SystemExit(f"no drawn games found in {rel(DRAW_LOG)}")
    return [(g, int(k)) for g, k in found]


def round_units(rnd):
    """[(game, [levels])] of a round, and the file the games come from."""
    if rnd == 0:
        return [(g, [0, k]) for g, k in drawn_games()], DRAW_LOG
    draw = os.path.join(TRUTH, f"handcheck_fresh_{rnd}.json")
    if not os.path.exists(draw):
        refuse(f"fresh round {rnd} has not been drawn ({rel(draw)} does not exist)")
    return [(d["game"], list(d["levels"])) for d in read_json(draw)["games"]], draw


def guide_questions():
    """{predicate: (name, question)} from the guide's sections '## A1. Name' and their '**Question.**' line."""
    with open(GUIDE, encoding="utf-8") as f:
        text = f.read()
    out = {}
    for p, name, body in re.findall(r"^## (A\d)\. ([^\n]+)\n(.*?)(?=^## |\Z)", text, re.M | re.S):
        m = re.search(r"^\*\*Question\.\*\* (.+)$", body, re.M)
        if m:
            out[p] = (name.strip(), m.group(1).strip())
    missing = [p for p in PRED if p not in out]
    if missing:
        raise SystemExit(f"{rel(GUIDE)} has no question for {', '.join(missing)}")
    return out


def source_readings(path):
    """The readings derived from the GVGAI source, and the path of the script that wrote them; refuses any other."""
    if not os.path.exists(path):
        refuse(f"no readings derived from the GVGAI source at {rel(path)}. docs/truth/handcheck_readings.json explains "
               "the generator's verdict and may not be shown in the blind hand check (PREREG Section 5, decided "
               "28 November 2026); how the source readings are written is the author's decision")
    data = read_json(path)
    if data.get("schema") != READINGS_SCHEMA:
        refuse(f"{rel(path)} is {data.get('schema')}, not {READINGS_SCHEMA}")
    writer = data.get("written_by")
    wpath = os.path.join(REPO, writer) if writer else None
    if not wpath or not os.path.exists(wpath):
        refuse(f"{rel(path)} does not name an existing script that wrote it ({writer!r})")
    with open(wpath, encoding="utf-8") as f:
        wtext = f.read()
    bad = [w for w in FORBIDDEN_IN_WRITER if w in wtext]
    if bad:
        refuse(f"{rel(wpath)}, which wrote {rel(path)}, names {', '.join(bad)}; a reading shown in the hand check is "
               "derived from the GVGAI source, not from the generator or its output")
    return data["readings"], wpath


def truth_blob():
    """The git blob of docs/truth/gvgai.json at HEAD: a hash, not the file; recorded for the report's comparison."""
    r = subprocess.run(["git", "rev-parse", f"HEAD:{TRUTH_REL}"], cwd=REPO, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def build_rows(rnd=0, readings_path=READINGS):
    readings, writer = source_readings(readings_path)
    units, games_file = round_units(rnd)
    questions = guide_questions()
    rows = []
    for game, levels in units:
        desc = f"{GAMES_DIR}/{game}.txt"
        for p in PRED:
            for lvl in levels:
                rid = f"{game}/{p}/{lvl}"
                r = readings.get(rid)
                if r is None:
                    refuse(f"{rel(readings_path)} has no reading for {rid}")
                lvl_file = f"{GAMES_DIR}/{game}_lvl{lvl}.txt"
                hl = r.get("lines", {})
                highlight = {"description": sorted(int(n) for n in hl.get("description", [])),
                             "level": sorted(int(n) for n in hl.get("level", []))}
                for where, path in (("description", desc), ("level", lvl_file)):
                    size = len(file_lines(path))
                    if any(not 1 <= n <= size for n in highlight[where]):
                        refuse(f"{rid}: a highlighted line is not in {path}")
                rows.append({"id": rid, "game": game, "level": lvl, "predicate": p, "name": questions[p][0],
                             "question": questions[p][1], "description": desc, "level_file": lvl_file,
                             "reading": (r.get("reading") or "").strip(), "highlight": highlight})
    return {"schema": ROWS_SCHEMA, "written_by": "scripts/handcheck_app.py", "round": rnd,
            "truth_blob": truth_blob(),
            "sources": {rel(p): sha256(p) for p in (games_file, GUIDE, readings_path, writer)}, "rows": rows}


def blind_refusal(data, what):
    """Why a rows file may not be shown: not the blind form, or a verdict in it; None if it may."""
    if data.get("schema") != ROWS_SCHEMA:
        return f"{what} is {data.get('schema')}, not {ROWS_SCHEMA}: the old form shows the generator's verdict"
    if any(k in r for r in data.get("rows", []) for k in VERDICT_KEYS):
        return f"{what} carries the generator's verdict or its reading"
    return None


def load_rows(rows_path, rnd=0, readings_path=READINGS):
    """The rows, written first if the file does not exist; and the sources changed since they were written."""
    if not os.path.exists(rows_path):
        write_json(rows_path, build_rows(rnd, readings_path))
    data = read_json(rows_path)
    why = blind_refusal(data, rel(rows_path))
    if why:
        refuse(why)
    changed = [p for p, h in data["sources"].items()
               if not os.path.exists(os.path.join(REPO, p)) or sha256(os.path.join(REPO, p)) != h]
    return data, changed


class Answers:
    """The answers file: one entry per row touched, kept on disk after every change."""

    def __init__(self, path, rows_path, rows_sha):
        self.path = path
        self.rows_sha = rows_sha
        if os.path.exists(path):
            self.data = read_json(path)
            if self.data.get("schema") != ANSWERS_SCHEMA:
                refuse(f"{rel(path)} is {self.data.get('schema')}, not {ANSWERS_SCHEMA}; answers given with the "
                       "verdict visible were discarded on 28 November 2026 (PREREG Section 5) and stay in the git "
                       "history; this file must be removed from this path before the blind pass")
        else:
            self.data = {"schema": ANSWERS_SCHEMA, "rows_file": rel(rows_path), "rows_sha256": rows_sha,
                         "started_at": now(), "updated_at": None, "finished_at": None, "position": 0, "answers": {}}

    @property
    def rows_changed(self):
        return self.data["rows_sha256"] != self.rows_sha

    def get(self, rid):
        return self.data["answers"].get(rid, {})

    def answer(self, rid):
        return self.get(rid).get("answer")

    def set(self, rid, answer=None, note=None):
        e = dict(self.get(rid))
        if answer is not None:
            e["answer"] = answer
            e["answered_at"] = now()
        if note is not None:
            e["note"] = note
        e.setdefault("answer", None)
        e.setdefault("note", "")
        if e["answer"] is None and not e["note"]:
            self.data["answers"].pop(rid, None)
        else:
            self.data["answers"][rid] = e

    def save(self, position, finished=False):
        self.data["position"] = position
        self.data["updated_at"] = now()
        if finished:
            self.data["finished_at"] = self.data["updated_at"]
        write_json(self.path, self.data)

    def answered(self, rows):
        return sum(1 for r in rows if self.answer(r["id"]) in CHOICES)


def start_position(rows, answers):
    """Where the last session stopped; on a first start, the first row without an answer."""
    pos = answers.data.get("position")
    if answers.data.get("updated_at") and isinstance(pos, int) and 0 <= pos < len(rows):
        return pos
    return next((i for i, r in enumerate(rows) if answers.answer(r["id"]) not in CHOICES), 0)


def info_blocks(r):
    """The right pane of a row, as (text, style) pairs.  Built from the row alone; a row carries no verdict."""
    desc_name, level_name = r["description"].split("/")[-1], r["level_file"].split("/")[-1]
    out = [(f"{r['game']}, level {r['level']}\n", "h"), (f"{r['predicate']}. {r['name']}\n", "b"),
           (r["question"] + "\n", None),
           ("Your answer: does the predicate hold on this level, by the files alone?\n", "b"),
           ("1 holds, 2 fails, 3 unsure.\n", None)]
    if r["reading"]:
        out += [("A reading of the source\n", "b"), (r["reading"] + "\n", None)]
    lines = [(desc_name, r["description"], n) for n in r["highlight"]["description"]] + \
            [(level_name, r["level_file"], n) for n in r["highlight"]["level"]]
    if lines:
        out.append(("Lines the reading names (yellow on the left)\n", "b"))
        out += [(f"{name}:{n}  {file_lines(path)[n - 1].strip()}\n", "small") for name, path, n in lines]
    out += [("Files\n", "b"), (f"{r['description']}\n{r['level_file']}\n", "small")]
    return out


class App:
    def __init__(self, root, rows, answers, changed):
        import tkinter as tk
        from tkinter import font as tkfont
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.root, self.rows, self.ans = root, rows, answers
        self.i = start_position(rows, answers)
        root.title("HORIZON hand check of the truth tables (blind)")
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{min(1440, sw - 40)}x{min(880, sh - 80)}+10+10")
        try:
            root.state("zoomed")
        except tk.TclError:
            pass
        root.protocol("WM_DELETE_WINDOW", self.close)
        mono = tkfont.nametofont("TkFixedFont").copy()
        mono.configure(size=11)
        base = tkfont.nametofont("TkDefaultFont").copy()
        base.configure(size=11)
        bold = base.copy()
        bold.configure(weight="bold")
        big = base.copy()
        big.configure(size=14, weight="bold")

        top = ttk.Frame(root, padding=(10, 8))
        top.pack(side="top", fill="x")
        self.counter = ttk.Label(top, font=big)
        self.counter.pack(side="left")
        self.tally = ttk.Label(top, font=base)
        self.tally.pack(side="right")
        self.progress = ttk.Progressbar(root, maximum=len(rows), mode="determinate")
        self.progress.pack(side="top", fill="x", padx=10)
        warn = []
        if changed:
            warn.append("These files changed after the rows were written: " + ", ".join(changed) + ".")
        if answers.rows_changed:
            warn.append("The rows file changed after the first answers were kept.")
        if warn:
            ttk.Label(root, text=" ".join(warn), foreground="#a00000", wraplength=1400,
                      padding=(10, 4)).pack(side="top", fill="x")

        bottom = ttk.Frame(root, padding=(10, 8))
        bottom.pack(side="bottom", fill="x")
        self.buttons = {}
        for k, choice in enumerate(CHOICES, 1):
            b = ttk.Button(bottom, text=f"{choice.capitalize()}  ({k})", command=lambda c=choice: self.mark(c))
            b.pack(side="left", padx=(0, 6))
            self.buttons[choice] = b
        ttk.Label(bottom, text="Note:", font=base).pack(side="left", padx=(16, 4))
        self.note = tk.StringVar()
        self.note_entry = ttk.Entry(bottom, textvariable=self.note, width=60, font=base)
        self.note_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(bottom, text="Finish", command=self.finish).pack(side="right", padx=(6, 0))
        ttk.Button(bottom, text="Skip", command=self.skip).pack(side="right", padx=(6, 0))
        ttk.Button(bottom, text="Back", command=self.back).pack(side="right", padx=(6, 0))
        self.mine = ttk.Label(root, font=bold, padding=(10, 0))
        self.mine.pack(side="bottom", fill="x")

        panes = ttk.PanedWindow(root, orient="horizontal")
        panes.pack(side="top", fill="both", expand=True, padx=10, pady=8)
        self.tabs = ttk.Notebook(panes)
        self.desc_text = self._code_view(self.tabs, mono)
        self.level_text = self._code_view(self.tabs, mono)
        self.tabs.add(self.desc_text.master, text="Description")
        self.tabs.add(self.level_text.master, text="Level file")
        panes.add(self.tabs, weight=3)
        right = ttk.Frame(panes)
        self.info = tk.Text(right, wrap="word", font=base, relief="flat", padx=12, pady=8, cursor="arrow")
        sb = ttk.Scrollbar(right, orient="vertical", command=self.info.yview)
        self.info.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.info.pack(side="left", fill="both", expand=True)
        self.info.tag_configure("h", font=big, spacing3=4)
        self.info.tag_configure("b", font=bold, spacing1=10)
        self.info.tag_configure("small", font=mono, lmargin1=16, lmargin2=40, foreground="#333333")
        panes.add(right, weight=2)

        for k, choice in enumerate(CHOICES, 1):
            root.bind(f"<Key-{k}>", lambda e, c=choice: self.key(c))
            root.bind(f"<KP_{k}>", lambda e, c=choice: self.key(c))
        self.show()

    def _code_view(self, parent, mono):
        tk, ttk = self.tk, self.ttk
        frame = ttk.Frame(parent)
        t = tk.Text(frame, wrap="none", font=mono, padx=6, pady=4)
        ys = ttk.Scrollbar(frame, orient="vertical", command=t.yview)
        xs = ttk.Scrollbar(frame, orient="horizontal", command=t.xview)
        t.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.pack(side="right", fill="y")
        xs.pack(side="bottom", fill="x")
        t.pack(side="left", fill="both", expand=True)
        t.tag_configure("named", background="#ffe066")
        t.tag_configure("num", foreground="#888888")
        return t

    def _fill_code(self, t, path, named):
        lines = file_lines(path)
        t.configure(state="normal")
        t.delete("1.0", "end")
        for n, line in enumerate(lines, 1):
            t.insert("end", f"{n:4d}  ", "num")
            t.insert("end", line + "\n")
        for n in named:
            t.tag_add("named", f"{n}.0", f"{n}.end+1c")
        t.configure(state="disabled")
        t.update_idletasks()
        t.yview(f"{max(1, (min(named) if named else 1) - 8)}.0")

    def show(self):
        r = self.rows[self.i]
        desc_name, level_name = r["description"].split("/")[-1], r["level_file"].split("/")[-1]
        self._fill_code(self.desc_text, r["description"], r["highlight"]["description"])
        self._fill_code(self.level_text, r["level_file"], r["highlight"]["level"])
        self.tabs.tab(0, text=f"Description: {desc_name}")
        self.tabs.tab(1, text=f"Level file: {level_name}")
        self.tabs.select(1 if r["highlight"]["level"] and not r["highlight"]["description"] else 0)
        t = self.info
        t.configure(state="normal")
        t.delete("1.0", "end")
        for text, style in info_blocks(r):
            t.insert("end", text, style or ())
        t.configure(state="disabled")

        n = len(self.rows)
        done = self.ans.answered(self.rows)
        self.counter.configure(text=f"Row {self.i + 1} of {n}:  {r['game']}, level {r['level']}, {r['predicate']}")
        self.tally.configure(text=f"Answered {done}    Remaining {n - done}")
        self.progress.configure(value=done)
        e = self.ans.get(r["id"])
        self.note.set(e.get("note", ""))
        a = e.get("answer")
        self.mine.configure(text=f"Your answer on this row: {a}" if a else "This row has no answer yet.")
        self.root.focus_set()

    def _keep_note(self):
        self.ans.set(self.rows[self.i]["id"], note=self.note.get().strip())

    def key(self, choice):
        if self.root.focus_get() is self.note_entry:
            return
        self.mark(choice)

    def mark(self, choice):
        rid = self.rows[self.i]["id"]
        self.ans.set(rid, answer=choice, note=self.note.get().strip())
        if self.i < len(self.rows) - 1:
            self.i += 1
        else:
            nxt = next((k for k, r in enumerate(self.rows) if self.ans.answer(r["id"]) not in CHOICES), None)
            if nxt is not None:
                self.i = nxt
        self.ans.save(self.i)
        self.show()

    def back(self):
        self._keep_note()
        self.i = max(0, self.i - 1)
        self.ans.save(self.i)
        self.show()

    def skip(self):
        self._keep_note()
        self.i = (self.i + 1) % len(self.rows)
        self.ans.save(self.i)
        self.show()

    def close(self):
        self._keep_note()
        self.ans.save(self.i)
        self.root.destroy()

    def finish(self, ask=True):
        from tkinter import messagebox
        self._keep_note()
        self.ans.save(self.i, finished=True)
        n, done = len(self.rows), self.ans.answered(self.rows)
        if ask:
            messagebox.showinfo("Finished", f"{done} of {n} rows answered, {n - done} without an answer.\n\n"
                                f"The answers are in {rel(self.ans.path)}. Commit them before anything compares "
                                "them with the generator. Starting the tool again resumes at row "
                                f"{self.i + 1}.")
        self.root.destroy()


def main(argv=None):
    ap = argparse.ArgumentParser(description="The blind hand check of the truth tables, one row at a time.")
    ap.add_argument("--round", type=int, default=0, choices=(0, 1, 2), help="0 the 100 rows, 1 or 2 a fresh round")
    ap.add_argument("--rows", action="store_true", help="write the rows file if it does not exist, and stop")
    ap.add_argument("--answers", default=None, help="tests only: the answers file")
    ap.add_argument("--readings", default=READINGS, help="tests only: the readings file")
    ap.add_argument("--out-dir", default=TRUTH, help="tests only: the folder of the rows and answers files")
    a = ap.parse_args(argv)
    rows_path, answers_path = paths_for(a.round, a.out_dir)
    existed = os.path.exists(rows_path)
    data, changed = load_rows(rows_path, a.round, a.readings)
    rows = data["rows"]
    if a.rows:
        print(f"{rel(rows_path)} {'existed' if existed else 'written'}: {len(rows)} rows, "
              f"{len({r['game'] for r in rows})} games, sha256 {sha256(rows_path)}; no verdict in it")
        for g in dict.fromkeys(r["game"] for r in rows):
            lv = sorted({r["level"] for r in rows if r["game"] == g})
            print(f"   {g}: levels {', '.join(map(str, lv))}")
        print(f"sources: {', '.join(data['sources'])}")
        print("sources changed since written: " + (", ".join(changed) if changed else "none"))
        return 0
    answers = Answers(os.path.abspath(a.answers or answers_path), rows_path, sha256(rows_path))
    import tkinter as tk
    root = tk.Tk()
    App(root, rows, answers, changed)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
