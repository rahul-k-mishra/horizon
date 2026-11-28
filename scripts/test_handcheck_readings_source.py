"""
test_handcheck_readings_source.py -- tests of scripts/handcheck_readings_source.py and of its committed output,
docs/truth/handcheck_readings_source.json (docs/PREREG.md, Section 5, decided 28 November 2026, option B).

1. Rows: the readings cover exactly the rows of the hand check (10 games of the draw of 25 October 2026, levels 0
   and the drawn level, 5 predicates) and of fresh round 1 (5 games), and a game and level has the same reading for
   every predicate.
2. Byte for byte: every quoted block equals the named lines of the named file of third_party/gvgai at the commit the
   output names, the commit that last changed third_party/gvgai; and that file in the working tree equals it but for
   line endings, which git converts on checkout for some of these files.
3. Nothing but quotes: read line by line, each reading is its quotes, each under a header of the fixed form
   "<label>, <file>, line <n>:" or "<label>, <file>, lines <n> to <m>:" whose numbers are the quote's own lines (and,
   for a level map, the row's level), separated by blank lines, with only two other kinds of line allowed: "Game
   description: <file>" and "The description has no <block> block."  So no line outside a quote holds a count.
4. No reading contains a predicate name (A1 to A5, or the name of any of them in docs/truth/HANDCHECK_GUIDE.md's
   headings, read here by the test, not by the script) or a verdict word (holds, hold, fails, fail, verdict).
6. Every effect the InteractionSet names is quoted from its own Java file under src/ontology/effects, in the order
   named (added 28 November 2026 with the effects).
7. The length of each reading before the effects were added (the readings as committed in 634fb3c) and now.
5. Run again with every opened file recorded, into a temporary folder: the script opens none of
   docs/truth/gvgai.json, scripts/truth_vgdl.py and docs/truth/handcheck_readings.json, its text names none of them,
   and its output equals the committed file.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe -W error scripts\\test_handcheck_readings_source.py > logs\\test_handcheck_readings_source.log
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
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import handcheck_readings_source as S  # noqa: E402

REPO = S.REPO
OUT = os.path.join(REPO, "docs", "truth", "handcheck_readings_source.json")
FORBIDDEN = ["docs/truth/gvgai.json", "scripts/truth_vgdl.py", "docs/truth/handcheck_readings.json"]
FAILS = []


def check(cond, what):
    if not cond:
        FAILS.append(what)
        print("FAIL  " + what)
    return cond


def git_bytes(commit, path):
    return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=REPO, capture_output=True, check=True).stdout


def expected_rows():
    with open(os.path.join(REPO, "logs", "draw_handcheck.log"), encoding="utf-8") as f:
        drawn = re.findall(r"(\w+) \(levels 0 and (\d+)\)", re.search(r"^drawn: (.+)$", f.read(), re.M).group(1))
    with open(os.path.join(REPO, "docs", "truth", "handcheck_fresh_1.json"), encoding="utf-8") as f:
        fresh = json.load(f)["games"]
    units = [(g, [0, int(k)]) for g, k in drawn] + [(d["game"], d["levels"]) for d in fresh]
    return {(g, lv) for g, lvs in units for lv in lvs}, len(drawn), len(fresh)


def part1(data):
    units, n0, n1 = expected_rows()
    want = {f"{g}/{p}/{lv}" for g, lv in units for p in S.PRED}
    r = data["readings"]
    check(set(r) == want, "the readings are exactly the rows of both row sets")
    same = all(r[f"{g}/{p}/{lv}"] == r[f"{g}/A1/{lv}"] for g, lv in units for p in S.PRED)
    check(same, "a game and level has the same reading for every predicate")
    print(f"1. rows: {len(r)} readings, the {n0} games of the hand check and the {n1} of fresh round 1, levels as "
          "drawn, every predicate; one reading per game and level")
    return units


def part2(data, units):
    commit = data["vendored_commit"]
    last = subprocess.run(["git", "log", "-1", "--format=%H", "--", "third_party/gvgai"], cwd=REPO,
                          capture_output=True, text=True, check=True).stdout.strip()
    check(commit == last, f"the output names the commit that last changed third_party/gvgai ({commit} vs {last})")
    blobs, n = {}, 0
    for g, lv in sorted(units):
        for q in data["readings"][f"{g}/A1/{lv}"]["quotes"]:
            path = q["file"]
            check(path.startswith("third_party/gvgai/"), f"{g} {lv}: quote from {path}, outside third_party/gvgai")
            if path not in blobs:
                blobs[path] = git_bytes(commit, path)
                with open(os.path.join(REPO, path), "rb") as f:
                    check(f.read().replace(b"\r\n", b"\n") == blobs[path].replace(b"\r\n", b"\n"),
                          f"{path}: the working tree equals the file at {commit}, line endings aside")
            lines = blobs[path].splitlines(keepends=True)
            got = b"".join(lines[q["first"] - 1:q["last"]]).rstrip(b"\r\n")
            check(1 <= q["first"] <= q["last"] <= len(lines) and got == q["text"].encode("utf-8"),
                  f"{g} level {lv}: {q['label']} is lines {q['first']} to {q['last']} of {path}, byte for byte")
            n += 1
    print(f"2. byte for byte: {n} quotes in {len(blobs)} files equal the named lines at {commit}, and the working "
          "tree equals that commit but for line endings")


HEAD = re.compile(r"^(SpriteSet|InteractionSet|TerminationSet|LevelMapping|Level (\d) map|Avatar sprite|"
                  r"Avatar class \w+|Defaults of \w+|Actions of \w+|Effect \w+), (third_party/gvgai/[\w/.]+), "
                  r"(?:line (\d+)|lines (\d+) to (\d+)):$")
OTHER = [re.compile(r"^Game description: third_party/gvgai/examples/gridphysics/\w+\.txt$"),
         re.compile(r"^The description has no (SpriteSet|InteractionSet|TerminationSet|LevelMapping) block\.$"),
         re.compile(r"^No source file for the effect \w+ under third_party/gvgai/src/ontology/effects\.$")]


def part3(data, units):
    bad = 0
    for g, lv in sorted(units):
        r = data["readings"][f"{g}/A1/{lv}"]
        lines, quotes, i, k, ok = r["reading"].split("\n"), r["quotes"], 0, 0, True
        while i < len(lines):
            ln = lines[i]
            m = HEAD.match(ln)
            if m:
                q = quotes[k] if k < len(quotes) else None
                first = int(m.group(4) or m.group(5))
                last = int(m.group(4) or m.group(6))
                ok &= q is not None and m.group(1) == q["label"] and m.group(3) == q["file"] \
                    and (first, last) == (q["first"], q["last"]) and (m.group(2) is None or int(m.group(2)) == lv)
                body = q["text"].replace("\r", "").split("\n") if q else []
                ok &= lines[i + 1:i + 1 + len(body)] == body
                i += 1 + len(body)
                k += 1
                ok &= i >= len(lines) or lines[i] == ""
                i += 1
                continue
            ok &= any(p.match(ln) for p in OTHER) and (i + 1 >= len(lines) or lines[i + 1] == "")
            i += 2
        ok &= k == len(quotes)
        if not check(ok, f"{g} level {lv}: the reading is its quotes under fixed headers and nothing else"):
            bad += 1
    print(f"3. nothing but quotes: {len(units) - bad} of {len(units)} readings are their quotes under fixed headers, "
          "whose only numbers are the quotes' own lines and the level; no other line")


def part4(data, units):
    with open(os.path.join(REPO, "docs", "truth", "HANDCHECK_GUIDE.md"), encoding="utf-8") as f:
        names = re.findall(r"^## A\d\. (.+)$", f.read(), re.M)
    pat = re.compile(r"\b(A[1-5]|holds?|fails?|verdicts?)\b|" + "|".join(re.escape(n) for n in names), re.I)
    hits = [(g, lv, m.group(0)) for g, lv in sorted(units)
            for m in [pat.search(data["readings"][f"{g}/A1/{lv}"]["reading"])] if m]
    for h in hits:
        check(False, f"{h[0]} level {h[1]}: the reading contains '{h[2]}'")
    print(f"4. words: no reading contains A1 to A5, any of the {len(names)} predicate names of the guide, or a "
          "verdict word" if not hits else f"4. words: {len(hits)} readings with a forbidden word")


def part5():
    with open(os.path.join(HERE, "handcheck_readings_source.py"), encoding="utf-8") as f:
        text = f.read()
    named = [p for p in FORBIDDEN if p in text or os.path.basename(p) in text]
    check(not named, f"the script's text names {named}")
    seen, real = [], builtins.open

    def traced(file, *a, **k):
        seen.append(os.path.abspath(str(file)))
        return real(file, *a, **k)
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "readings.json")
        old = S.OUT
        S.OUT = out
        builtins.open = traced
        try:
            with redirect_stdout(io.StringIO()):
                S.main()
        finally:
            builtins.open = real
            S.OUT = old
        with open(out, encoding="utf-8") as f:
            again = json.load(f)
    with open(OUT, encoding="utf-8") as f:
        committed = json.load(f)
    opened = [p for p in FORBIDDEN if os.path.abspath(os.path.join(REPO, p)) in seen]
    check(not opened, f"the script opened {opened}")
    check(again == committed, "a second run gives the committed output")
    outside = sorted({os.path.relpath(p, REPO).replace("\\", "/").split("/")[0] for p in seen
                      if p.startswith(os.path.abspath(REPO))})
    print(f"5. files: the script opened {len(seen)} files, none of the three forbidden ones; top folders read: "
          f"{', '.join(outside)}; its text names none of them; a second run gives the committed output")


BEFORE_COMMIT = "634fb3c"  # the readings as first committed, without the effects


def part6(data, units):
    """Every effect the InteractionSet names is quoted, from its own file, under its own header."""
    bad = 0
    for g, lv in sorted(units):
        qs = data["readings"][f"{g}/A1/{lv}"]["quotes"]
        inter = next((q["text"] for q in qs if q["label"] == "InteractionSet"), "")
        named = []
        for ln in inter.replace("\r", "").split("\n")[1:]:
            ln = ln.split("#", 1)[0]
            if ">" in ln:
                t = ln.split(">", 1)[1].split()
                if t and "=" not in t[0] and t[0] not in named:
                    named.append(t[0])
        quoted = [q["label"][len("Effect "):] for q in qs if q["label"].startswith("Effect ")]
        files_ok = all(q["file"].startswith("third_party/gvgai/src/ontology/effects/")
                       and q["file"].endswith("/" + q["label"][7:8].upper() + q["label"][8:] + ".java")
                       for q in qs if q["label"].startswith("Effect "))
        if not check(quoted == named and files_ok, f"{g} level {lv}: effects named {named}, quoted {quoted}"):
            bad += 1
    print(f"6. effects: in {len(units) - bad} of {len(units)} readings every effect the InteractionSet names is quoted "
          "from its own file under src/ontology/effects, in the order named")


def part7(data, units):
    """How much longer each reading is than the readings first committed, without the effects."""
    old = json.loads(git_bytes(BEFORE_COMMIT, "docs/truth/handcheck_readings_source.json").decode("utf-8"))["readings"]
    tot_b = tot_a = 0
    for g, lv in sorted(units, key=lambda x: (x[0], x[1])):
        b, a = len(old[f"{g}/A1/{lv}"]["reading"]), len(data["readings"][f"{g}/A1/{lv}"]["reading"])
        tot_b, tot_a = tot_b + b, tot_a + a
        print(f"   {g} level {lv}: {b} characters before, {a} now, {a / b:.2f} times")
    print(f"7. length: over the {len(units)} readings, {tot_b} characters before ({BEFORE_COMMIT}), {tot_a} now, "
          f"{tot_a / tot_b:.2f} times")


if __name__ == "__main__":
    with open(OUT, encoding="utf-8") as f:
        data = json.load(f)
    check(data.get("schema") == "horizon.handcheck_readings.v2", "schema horizon.handcheck_readings.v2")
    u = part1(data)
    part2(data, u)
    part3(data, u)
    part4(data, u)
    part5()
    part6(data, u)
    part7(data, u)
    print("OK" if not FAILS else f"FAILED: {len(FAILS)}")
    sys.exit(1 if FAILS else 0)
