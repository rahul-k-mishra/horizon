"""
handcheck_report.py -- writes docs/truth/HANDCHECK_RESULT.md from the answers of the hand check of the truth tables
(kept by scripts/handcheck_app.py in docs/truth/handcheck_answers.json) and the rows they answer
(docs/truth/handcheck_rows.json).  Standard library only; reads committed files only.

The result lists, per predicate and per game, how many rows were marked agree, disagree and unsure and how many
have no answer; every disagreement and every unsure row with its note; the games and levels covered; and the dates.
It resolves nothing: a disagreement is listed as the author marked it.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\handcheck_report.py > logs\\handcheck_report.log
Options: --answers P (default docs/truth/handcheck_answers.json), --out P (default docs/truth/HANDCHECK_RESULT.md).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRUTH = os.path.join(REPO, "docs", "truth")
ROWS = os.path.join(TRUTH, "handcheck_rows.json")
ANSWERS = os.path.join(TRUTH, "handcheck_answers.json")
OUT = os.path.join(TRUTH, "HANDCHECK_RESULT.md")
PRED = ("A1", "A2", "A3", "A4", "A5")
CHOICES = ("agree", "disagree", "unsure")


def rel(path):
    try:
        return os.path.relpath(path, REPO).replace("\\", "/")
    except ValueError:
        return path


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tally(rows, answers):
    c = {k: 0 for k in CHOICES + ("no answer",)}
    for r in rows:
        a = answers.get(r["id"], {}).get("answer")
        c[a if a in CHOICES else "no answer"] += 1
    return c


def table(title, groups, rows, answers):
    out = [f"| {title} | rows | agree | disagree | unsure | no answer |", "|---|---|---|---|---|---|"]
    for g in groups:
        sub = [r for r in rows if g in (r["predicate"], r["game"])]
        c = tally(sub, answers)
        out.append(f"| {g} | {len(sub)} | {c['agree']} | {c['disagree']} | {c['unsure']} | {c['no answer']} |")
    c = tally(rows, answers)
    out.append(f"| all | {len(rows)} | {c['agree']} | {c['disagree']} | {c['unsure']} | {c['no answer']} |")
    return out


def listing(rows, answers, pick):
    out = []
    for r in rows:
        e = answers.get(r["id"], {})
        if not pick(e):
            continue
        d = r["deciding"]
        where = (r["description"] if d["in"] == "description" else r["level_file"]).split("/")[-1]
        note = (e.get("note") or "").strip() or "(no note)"
        out.append(f"- **{r['game']}, level {r['level']}, {r['predicate']}** ({r['name']}): the generator's verdict "
                   f"**{r['verdict']}**, deciding line {where}:{d['line']} `{d['text']}`. Note: {note}")
    return out or ["None."]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", default=ANSWERS)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    if not os.path.exists(a.answers):
        print(f"no answers file at {a.answers}: start scripts/handcheck_app.py first")
        return 1
    rows_data, ans_data = read_json(ROWS), read_json(a.answers)
    rows, answers = rows_data["rows"], ans_data["answers"]
    rows_sha = sha256(ROWS)
    unknown = sorted(set(answers) - {r["id"] for r in rows})
    games = list(dict.fromkeys(r["game"] for r in rows))
    today = datetime.date.today().isoformat()

    out = ["# Result of the hand check of the truth tables", "",
           f"Written {today} by scripts/handcheck_report.py (console in logs/handcheck_report.log) from "
           f"{rel(a.answers)} and {rel(ROWS)}. The rows are the predicates of docs/PREREG.md draft v0, Section 5, on "
           "the games and levels drawn by scripts/draw_handcheck.py (logs/draw_handcheck.log), each with the verdict "
           "of scripts/truth_vgdl.py in docs/truth/gvgai.json. This file lists the answers as given; it resolves "
           "no disagreement.", "",
           f"- Answers started {ans_data.get('started_at')}, last changed {ans_data.get('updated_at')}, "
           f"finished {ans_data.get('finished_at') or 'not marked as finished'}.",
           f"- Rows file sha256 {rows_sha}; the answers were kept against "
           f"{'the same file' if ans_data.get('rows_sha256') == rows_sha else 'a different version of it: ' + str(ans_data.get('rows_sha256'))}.",
           ]
    if unknown:
        out.append(f"- Answers to rows not in the rows file, left out: {', '.join(unknown)}.")
    out += ["", "## Games and levels covered", "",
            "| game | levels | rows | answered |", "|---|---|---|---|"]
    for g in games:
        sub = [r for r in rows if r["game"] == g]
        lv = ", ".join(str(x) for x in sorted({r["level"] for r in sub}))
        c = tally(sub, answers)
        out.append(f"| {g} | {lv} | {len(sub)} | {len(sub) - c['no answer']} |")
    out += ["", "## Per predicate", ""] + table("predicate", PRED, rows, answers)
    out += ["", "## Per game", ""] + table("game", games, rows, answers)
    out += ["", "## Every disagreement", ""] + listing(rows, answers, lambda e: e.get("answer") == "disagree")
    out += ["", "## Every row marked unsure", ""] + listing(rows, answers, lambda e: e.get("answer") == "unsure")
    noted = listing(rows, answers, lambda e: e.get("answer") not in CHOICES and (e.get("note") or "").strip())
    out += ["", "## Rows without an answer that carry a note", ""] + noted
    out.append("")
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))

    c = tally(rows, answers)
    print(f"rows {len(rows)} ({rel(ROWS)}, sha256 {rows_sha}); answers {rel(a.answers)}, finished "
          f"{ans_data.get('finished_at')}")
    print(f"all: agree {c['agree']}, disagree {c['disagree']}, unsure {c['unsure']}, no answer {c['no answer']}")
    for g in PRED + tuple(games):
        sub = [r for r in rows if g in (r["predicate"], r["game"])]
        c = tally(sub, answers)
        print(f"   {g}: agree {c['agree']}, disagree {c['disagree']}, unsure {c['unsure']}, no answer {c['no answer']}")
    for r in rows:
        e = answers.get(r["id"], {})
        if e.get("answer") in ("disagree", "unsure"):
            print(f"{e['answer']}: {r['id']} (verdict {r['verdict']}); note: {(e.get('note') or '').strip()}")
    print(f"written {rel(a.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
