"""
handcheck_app.py -- a window for the author's hand check of the truth tables (docs/PREREG.md draft v0, Section 5).
Standard library only (Tkinter).  One row at a time: a predicate, on one level of one drawn game, with the
generator's verdict.  The left pane shows the game's description and the row's level file with the deciding line
highlighted; the right pane shows the question, the verdict, the deciding line and what it says.

Reads:  docs/truth/gvgai.json (scripts/truth_vgdl.py), docs/truth/HANDCHECK.md (the games and levels drawn by
        scripts/draw_handcheck.py), docs/truth/HANDCHECK_GUIDE.md (the question of each predicate) and
        docs/truth/handcheck_readings.json (a plain reading of each verdict), and the GVGAI files they name.
Writes: docs/truth/handcheck_rows.json, from the files above, only if it does not exist; and
        docs/truth/handcheck_answers.json after every click, so that closing the window loses nothing and the next
        start resumes at the row where the last one stopped.
Keys:   1 agree, 2 disagree, 3 unsure (not while typing a note).

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\handcheck_app.py
Options: --rows        write docs/truth/handcheck_rows.json if it does not exist, print what it holds, and stop;
         --answers P   keep the answers in P instead of docs/truth/handcheck_answers.json.
When finished: scripts/handcheck_report.py writes docs/truth/HANDCHECK_RESULT.md from the answers.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRUTH = os.path.join(REPO, "docs", "truth")
GVGAI = os.path.join(TRUTH, "gvgai.json")
SHEET = os.path.join(TRUTH, "HANDCHECK.md")
GUIDE = os.path.join(TRUTH, "HANDCHECK_GUIDE.md")
READINGS = os.path.join(TRUTH, "handcheck_readings.json")
ROWS = os.path.join(TRUTH, "handcheck_rows.json")
ANSWERS = os.path.join(TRUTH, "handcheck_answers.json")
ROWS_SCHEMA = "horizon.handcheck_rows.v1"
ANSWERS_SCHEMA = "horizon.handcheck_answers.v1"
PRED = ("A1", "A2", "A3", "A4", "A5")
CHOICES = ("agree", "disagree", "unsure")


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


def file_lines(path):
    with open(os.path.join(REPO, path), encoding="utf-8") as f:
        return f.read().splitlines()


def level_chars(desc_path, stype):
    """The level-file characters that place a sprite of type stype or of a type under it in the SpriteSet."""
    lines = file_lines(desc_path)
    block, parents, mapping, stack = None, {}, {}, []
    for line in lines:
        s = line.split("#", 1)[0].rstrip()
        if not s.strip():
            continue
        word = s.strip().split()[0]
        if word in ("SpriteSet", "LevelMapping", "InteractionSet", "TerminationSet"):
            block, stack = word, []
            continue
        if ">" not in s:
            continue
        left, right = (x.strip() for x in s.split(">", 1))
        if block == "SpriteSet":
            ind = len(s) - len(s.lstrip())
            while stack and stack[-1][0] >= ind:
                stack.pop()
            parents[left] = stack[-1][1] if stack else None
            stack.append((ind, left))
        elif block == "LevelMapping" and len(left) == 1:
            mapping[left] = right.split()

    def under(name):
        while name is not None:
            if name == stype:
                return True
            name = parents.get(name)
        return False
    return {c for c, names in mapping.items() if any(under(n) for n in names)}


def level_cells(row):
    """For a row whose verdict counts a sprite type in the level: (type, [(line, column), ...]) of the squares
    that place one; otherwise None."""
    m = next((re.search(r"places \d+ sprite\(s\) of (\S+)", c["reads"]) for c in row["clauses"]
              if c["in"] == "level"), None)
    if not m:
        return None
    chars = level_chars(row["description"], m.group(1))
    return m.group(1), [(n, col) for n, line in enumerate(file_lines(row["level_file"]), 1)
                        for col, ch in enumerate(line) if ch in chars]


def drawn_games():
    """The games and second levels of the sheet, in its order: [(game, level), ...]."""
    with open(SHEET, encoding="utf-8") as f:
        text = f.read()
    found = re.findall(r"^## (\S+)\n\nDescription: `[^`]+`\. Levels checked: 0 \(`[^`]+`\) and (\d+) ", text, re.M)
    if not found:
        raise SystemExit(f"no drawn games found in {rel(SHEET)}")
    return [(g, int(k)) for g, k in found]


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


def build_rows():
    truth = read_json(GVGAI)
    readings = read_json(READINGS)["readings"]
    questions = guide_questions()
    rows = []
    for game, other in drawn_games():
        gv = truth["games"][game]
        desc = gv["description"]
        for p in PRED:
            r = readings.get(f"{game}/{p}")
            if r is None:
                raise SystemExit(f"{rel(READINGS)} has no reading for {game}/{p}")
            for lvl in (0, other):
                e = gv["levels"][str(lvl)][p]
                lvl_file = gv["levels"][str(lvl)]["level_file"]
                clauses = [{"in": "level" if c["file"] == lvl_file else "description", "line": c["line"],
                            "text": (c["text"] or "").strip(), "reads": c["reads"]} for c in e["clauses"]]
                level_clause = next((c for c in clauses if c["in"] == "level"), None)
                if r["deciding"][0] == "level":
                    if level_clause is None:
                        raise SystemExit(f"{game}/{p}/{lvl}: the reading points at the level file, the verdict does not")
                    where, line = "level", level_clause["line"]
                else:
                    where, line = "description", int(r["deciding"][1])
                text = file_lines(lvl_file if where == "level" else desc)[line - 1].strip()
                reading = r["reading"]
                if "{n}" in reading:
                    m = level_clause and re.search(r"places (\d+) sprite", level_clause["reads"])
                    if not m:
                        raise SystemExit(f"{game}/{p}/{lvl}: the reading needs a count the verdict does not give")
                    reading = reading.replace("{n}", m.group(1))
                rows.append({"id": f"{game}/{p}/{lvl}", "game": game, "level": lvl, "predicate": p,
                             "name": questions[p][0], "question": questions[p][1], "verdict": e["verdict"],
                             "description": desc, "level_file": lvl_file,
                             "deciding": {"in": where, "line": line, "text": text},
                             "reading": reading, "wrong_if": r["wrong_if"], "clauses": clauses})
    return {"schema": ROWS_SCHEMA, "written_by": "scripts/handcheck_app.py",
            "sources": {rel(p): sha256(p) for p in (GVGAI, SHEET, GUIDE, READINGS)}, "rows": rows}


def load_rows():
    """The rows, written first if the file does not exist; and the sources changed since they were written."""
    if not os.path.exists(ROWS):
        write_json(ROWS, build_rows())
    data = read_json(ROWS)
    if data.get("schema") != ROWS_SCHEMA:
        raise SystemExit(f"{rel(ROWS)} is not {ROWS_SCHEMA}")
    changed = [p for p, h in data["sources"].items()
               if not os.path.exists(os.path.join(REPO, p)) or sha256(os.path.join(REPO, p)) != h]
    return data, changed


class Answers:
    """The answers file: one entry per row touched, kept on disk after every change."""

    def __init__(self, path, rows_sha):
        self.path = path
        self.rows_sha = rows_sha
        if os.path.exists(path):
            self.data = read_json(path)
            if self.data.get("schema") != ANSWERS_SCHEMA:
                raise SystemExit(f"{path} is not {ANSWERS_SCHEMA}")
        else:
            self.data = {"schema": ANSWERS_SCHEMA, "rows_file": rel(ROWS), "rows_sha256": rows_sha,
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


class App:
    def __init__(self, root, rows, answers, changed):
        import tkinter as tk
        from tkinter import font as tkfont
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.root, self.rows, self.ans = root, rows, answers
        self.i = start_position(rows, answers)
        root.title("HORIZON hand check of the truth tables")
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
            warn.append(f"{rel(ROWS)} changed after the first answers were kept.")
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
        ttk.Button(bottom, text="Guide", command=self.show_guide).pack(side="right", padx=(6, 0))
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
        self.info.tag_configure("code", font=mono, background="#fff2a8", lmargin1=16, lmargin2=16)
        self.info.tag_configure("small", font=mono, lmargin1=16, lmargin2=40, foreground="#333333")
        self.info.tag_configure("holds", font=big, foreground="#006400")
        self.info.tag_configure("fails", font=big, foreground="#a00000")
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
        t.tag_configure("clause", background="#dcebfa")
        t.tag_configure("deciding", background="#ffe066")
        t.tag_configure("num", foreground="#888888")
        t.tag_configure("cell", background="#f4a259", foreground="#000000")
        t.tag_raise("cell")
        return t

    def _fill_code(self, t, path, lines_clause, line_deciding):
        lines = file_lines(path)
        t.configure(state="normal")
        t.delete("1.0", "end")
        for n, line in enumerate(lines, 1):
            t.insert("end", f"{n:4d}  ", "num")
            t.insert("end", line + "\n")
        for n in lines_clause:
            t.tag_add("clause", f"{n}.0", f"{n}.end+1c")
        if line_deciding:
            t.tag_add("deciding", f"{line_deciding}.0", f"{line_deciding}.end+1c")
        t.configure(state="disabled")
        t.update_idletasks()
        target = line_deciding or (min(lines_clause) if lines_clause else 1)
        t.yview(f"{max(1, target - 8)}.0")

    def _mark_cells(self, r):
        """Where the verdict counts sprites in the level, colour every square that places one."""
        found = level_cells(r)
        if found:
            for n, col in found[1]:
                self.level_text.tag_add("cell", f"{n}.{col + 6}", f"{n}.{col + 7}")
        return found

    def show(self):
        r = self.rows[self.i]
        dec = r["deciding"]
        desc_name, level_name = r["description"].split("/")[-1], r["level_file"].split("/")[-1]
        self._fill_code(self.desc_text, r["description"],
                        {c["line"] for c in r["clauses"] if c["in"] == "description"},
                        dec["line"] if dec["in"] == "description" else None)
        self._fill_code(self.level_text, r["level_file"],
                        {c["line"] for c in r["clauses"] if c["in"] == "level"},
                        dec["line"] if dec["in"] == "level" else None)
        cells = self._mark_cells(r)
        self.tabs.tab(0, text=f"Description: {desc_name}")
        self.tabs.tab(1, text=f"Level file: {level_name}")
        self.tabs.select(1 if dec["in"] == "level" else 0)

        t = self.info
        t.configure(state="normal")
        t.delete("1.0", "end")
        t.insert("end", f"{r['game']}, level {r['level']}\n", "h")
        t.insert("end", f"{r['predicate']}. {r['name']}\n", "b")
        t.insert("end", r["question"] + "\n")
        t.insert("end", "The generator's verdict\n", "b")
        t.insert("end", r["verdict"].upper() + "\n", r["verdict"] if r["verdict"] in ("holds", "fails") else "b")
        where = desc_name if dec["in"] == "description" else level_name
        t.insert("end", f"The deciding line: {where}, line {dec['line']}\n", "b")
        t.insert("end", dec["text"] + "\n", "code")
        t.insert("end", "What it says\n", "b")
        t.insert("end", r["reading"] + "\n")
        t.insert("end", "For the verdict to be wrong\n", "b")
        t.insert("end", r["wrong_if"] + "\n")
        t.insert("end", "Every line the verdict rests on (blue on the left)\n", "b")
        for c in r["clauses"]:
            name = desc_name if c["in"] == "description" else level_name
            t.insert("end", f"{name}:{c['line']}  {c['text']}\n    read as: {c['reads']}\n", "small")
        if cells:
            t.insert("end", "In the level file\n", "b")
            t.insert("end", f"The {len(cells[1])} orange squares are those whose character places a {cells[0]} "
                            "or a kind under it in the SpriteSet.\n")
        t.insert("end", "Files\n", "b")
        t.insert("end", f"{r['description']}\n{r['level_file']}\n", "small")
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
                                f"The answers are in {rel(self.ans.path)}. Starting the tool again resumes at row "
                                f"{self.i + 1}.\n\nTo write the summary:\n"
                                r"D:\Research\horizon\.venv\Scripts\python.exe scripts\handcheck_report.py")
        self.root.destroy()

    def show_guide(self):
        tk, ttk = self.tk, self.ttk
        w = tk.Toplevel(self.root)
        w.title("Guide to the hand check")
        w.geometry("900x800")
        t = tk.Text(w, wrap="word", padx=12, pady=8)
        sb = ttk.Scrollbar(w, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        with open(GUIDE, encoding="utf-8") as f:
            t.insert("1.0", f.read())
        t.configure(state="disabled")


def main(argv=None):
    ap = argparse.ArgumentParser(description="The hand check of the truth tables, one row at a time.")
    ap.add_argument("--rows", action="store_true", help="write the rows file if it does not exist, and stop")
    ap.add_argument("--answers", default=ANSWERS, help="the answers file")
    a = ap.parse_args(argv)
    existed = os.path.exists(ROWS)
    data, changed = load_rows()
    rows = data["rows"]
    if a.rows:
        print(f"{rel(ROWS)} {'existed' if existed else 'written'}: {len(rows)} rows, "
              f"{len({r['game'] for r in rows})} games, sha256 {sha256(ROWS)}")
        for g in dict.fromkeys(r["game"] for r in rows):
            lv = sorted({r["level"] for r in rows if r["game"] == g})
            print(f"   {g}: levels {', '.join(map(str, lv))}; "
                  + ", ".join(f"{p} {'/'.join(r['verdict'] for r in rows if r['game'] == g and r['predicate'] == p)}"
                              for p in PRED))
        print("sources changed since written: " + (", ".join(changed) if changed else "none"))
        return 0
    import tkinter as tk
    root = tk.Tk()
    App(root, rows, Answers(os.path.abspath(a.answers), sha256(ROWS)), changed)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
