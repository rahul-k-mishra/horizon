"""
handcheck_seen.py -- checks and expands the contamination register of the blind hand check,
docs/truth/handcheck_seen.json (docs/PREREG.md, Section 5, decided 28 November 2026, option B).  Standard library only;
reads committed files and the commit messages named in the register.

For each statement of the register it looks for the statement's quoted text ("excerpt", stored word for word with
the file and line) in its source: a file in the working tree, a file at a named commit ("at"), or the subject of a
named commit ("commit").  It matches on the text, not the line (changed 28 November 2026): a statement whose text
is on another line than the register names is reported as moved, with its new line, and still counts; only a
statement whose text is gone fails.  The rows keep the file and line the register names as their label.  It expands the
statements into rows, a statement about a game counting for every level of the game in the row sets, with
*confirmatory* and *deterministic* read from scripts/suite.py.  The row sets are those of the hand check (the draw of
25 October 2026, logs/draw_handcheck.log) and of fresh round 1 (docs/truth/handcheck_fresh_1.json).  It checks that
every file under must_not_open exists.  It prints, per row set, the rows seen and the rows left blind.
With --write it writes the expanded rows into the register's "rows" (each row id with the statements that give it);
without, it checks that "rows" equals the expansion.  Exit 0 if every check passes, 1 otherwise.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\handcheck_seen.py > logs\\handcheck_seen.log
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
REGISTER = os.path.join(REPO, "docs", "truth", "handcheck_seen.json")
PRED = ("A1", "A2", "A3", "A4", "A5")
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import suite  # noqa: E402


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout


def row_sets():
    with open(os.path.join(REPO, "logs", "draw_handcheck.log"), encoding="utf-8") as f:
        drawn = re.findall(r"(\w+) \(levels 0 and (\d+)\)", re.search(r"^drawn: (.+)$", f.read(), re.M).group(1))
    with open(os.path.join(REPO, "docs", "truth", "handcheck_fresh_1.json"), encoding="utf-8") as f:
        fresh = json.load(f)["games"]
    return {"hand check (100 rows)": [(g, [0, int(k)]) for g, k in drawn],
            "fresh round 1 (50 rows)": [(d["game"], list(d["levels"])) for d in fresh]}


def locate(st):
    """Where the statement's quoted text is now: (state, where, note).  state is "here" when the text is on the line
    the register names, "moved" when it is on another line (note names the line or lines), "gone" when it is
    nowhere in the source.  where is the label the register's rows use: the file and the line the register names."""
    if "commit" in st:
        found = st["excerpt"] in git("log", "-1", "--format=%s", st["commit"])
        return ("here" if found else "gone"), f"commit {st['commit']}", ""
    if "at" in st:
        lines = git("show", f"{st['at']}:{st['file']}").splitlines()
        where = f"{st['file']}:{st['line']} at {st['at']}"
    else:
        with open(os.path.join(REPO, st["file"]), encoding="utf-8") as f:
            lines = f.read().splitlines()
        where = f"{st['file']}:{st['line']}"
    hits = [n for n, ln in enumerate(lines, 1) if st["excerpt"] in ln]
    if st["line"] in hits:
        return "here", where, ""
    if hits:
        return "moved", where, "now on line " + ", ".join(map(str, hits))
    return "gone", where, ""


def main(argv=None):
    write = "--write" in (argv if argv is not None else sys.argv[1:])
    with open(REGISTER, encoding="utf-8") as f:
        reg = json.load(f)
    sets = row_sets()
    games_in = {g for units in sets.values() for g, _ in units}
    levels = {g: lv for units in sets.values() for g, lv in units}
    groups = {"*confirmatory*": set(suite.confirmatory()) & games_in,
              "*deterministic*": set(suite.deterministic()) & games_in}
    ok, rows = True, {}
    print(f"register {os.path.relpath(REGISTER, REPO)}: {len(reg['statements'])} statements")
    for st in reg["statements"]:
        state, where, note = locate(st)
        found = state != "gone"
        ok &= found
        names = []
        for g, preds in st["games"].items():
            gs = sorted(groups[g]) if g in groups else [g]
            for game in gs:
                if game not in games_in:
                    print(f"  FAIL {where}: {game} is in no row set")
                    ok = False
                    continue
                for p in preds:
                    for lv in levels[game]:
                        rows.setdefault(f"{game}/{p}/{lv}", []).append(where)
                names.append(f"{game} {'/'.join(preds)}")
        mark = {"here": "ok  ", "moved": "MOVED", "gone": "FAIL"}[state]
        print(f"  {mark} {where}{' (' + note + ')' if note else ''} ({st['how'].split(':')[0].split(',')[0]}): "
              f"{', '.join(names)}")
    rows = {k: sorted(set(v)) for k, v in sorted(rows.items())}
    for p in reg["must_not_open"]:
        if " " in p:
            continue
        if not os.path.exists(os.path.join(REPO, p)):
            print(f"  FAIL must_not_open: {p} does not exist")
            ok = False
    print(f"must not be opened during the blind pass: {len(reg['must_not_open'])} entries")
    total = 0
    for name, units in sets.items():
        ids = [f"{g}/{p}/{lv}" for g, lvs in units for p in PRED for lv in lvs]
        seen = [i for i in ids if i in rows]
        total += len(seen)
        per_p = ", ".join(f"{p} {sum(1 for i in seen if f'/{p}/' in i)}" for p in PRED)
        print(f"{name}: {len(ids)} rows, seen {len(seen)} ({per_p}), blind {len(ids) - len(seen)}")
    print(f"rows seen in all: {total} of {sum(len(u) * 10 for u in sets.values())}")
    if write:
        reg["rows"] = rows
        with open(REGISTER, "w", encoding="utf-8", newline="\n") as f:
            json.dump(reg, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print("rows written into the register")
    else:
        same = reg.get("rows") == rows
        ok &= same
        print(f"the register's rows {'equal' if same else 'DIFFER FROM'} the expansion")
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
