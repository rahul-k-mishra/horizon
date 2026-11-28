"""
test_predicate_definitions.py -- tests of docs/truth/PREDICATE_DEFINITIONS.md, the only definition text the author
reads during the blind hand check (docs/PREREG.md, Section 5, decided 28 November 2026).  Reads committed files only.

1. Registered wording: the file has one section per predicate, A1 to A5, and every piece of text in each section,
   cut at the marks [...] where something was left out, is a piece of the bullet of that predicate in
   docs/PREREG.md, Section 5 (with its bold marks removed), word for word.
2. No game: the file names none of the 30 deterministic games of scripts/suite.py (the suite, the pilot and the pool
   of the fresh rounds), none of the games of the fresh draws, and none of the other games of
   third_party/gvgai/examples/gridphysics, matched as whole words without regard to case.
3. No verdict: every use of holds, hold, holding, fails, fail and verdict in the file is one of the fixed forms in
   which the definitions state their rule ("A1 holds iff", "It fails if" and the others listed below); none is a
   statement about a game.  No digit appears outside the predicate names, the rule's own "speed 1", "speed other
   than 1" and "limit 0", and the file's reference to "Section 5".
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe -W error scripts\\test_predicate_definitions.py > logs\\test_predicate_definitions.log
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import suite  # noqa: E402

DEFS = os.path.join(REPO, "docs", "truth", "PREDICATE_DEFINITIONS.md")
PRED = ("A1", "A2", "A3", "A4", "A5")
RULE_FORMS = ["A1 holds iff", "Fails if", "A2 holds iff", "It fails if", "A2 also fails wherever", "A3 holds iff",
              "It fails for", "A4 holds iff", "holds A4, because", "A5 holds iff", "the level holds exactly one",
              "keeps A5 holding"]
ALLOWED_NUMBERS = ["at least two actions", "speed 1", "speed other than 1", "limit 0", "Section 5"]
FAILS = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        FAILS.append(what)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    text = read(DEFS)
    sections = dict(re.findall(r"^## (A\d)\n\n(.+?)(?=\n## |\Z)", text, re.M | re.S))
    check(list(sections) == list(PRED), "one section per predicate, A1 to A5, in order")
    prereg = read(os.path.join(REPO, "docs", "PREREG.md"))
    sec5 = prereg[prereg.index("## 5. Truth tables"):prereg.index("## 6. ")].replace("**", "")
    pieces = 0
    for p in PRED:
        m = re.search(rf"^- {p} (.+)$", sec5, re.M)
        bullet = (p + " " + m.group(1)) if m else ""
        for piece in sections.get(p, "").split("[...]"):
            piece = piece.strip()
            if piece:
                pieces += 1
                check(piece in bullet, f"{p}: \"{piece[:50]}...\" is word for word in PREREG Section 5's {p}")
    print(f"1. registered wording: {pieces} pieces, each word for word in its predicate's bullet of PREREG Section 5")

    games = set(suite.deterministic())
    for name in os.listdir(os.path.join(REPO, "docs", "truth")):
        if re.fullmatch(r"handcheck_fresh_\d+\.json", name):
            games |= {d["game"] for d in json.loads(read(os.path.join(REPO, "docs", "truth", name)))["games"]}
    games |= {f[:-4] for f in os.listdir(os.path.join(REPO, "third_party", "gvgai", "examples", "gridphysics"))
              if f.endswith(".txt") and "_lvl" not in f}
    named = sorted(g for g in games if re.search(rf"\b{re.escape(g)}\b", text, re.I))
    check(not named, f"2. no game: none of {len(games)} game names appears" + (f"; found {named}" if named else ""))

    rest = text
    for form in RULE_FORMS:
        rest = rest.replace(form, "")
    left = re.findall(r"\b(holds?|holding|fails?|verdicts?)\b", rest, re.I)
    check(not left, "3. no verdict: every verdict word is in one of the fixed forms of the rule"
          + (f"; outside them: {left}" if left else ""))
    rest2 = text
    for p in PRED:
        rest2 = rest2.replace(p, "")
    for n in ALLOWED_NUMBERS:
        rest2 = rest2.replace(n, "")
    digits = re.findall(r"\d+", rest2)
    check(not digits, "3. no count: no digit outside the predicate names and the rule's own numbers"
          + (f"; found {digits}" if digits else ""))
    print("OK" if not FAILS else f"FAILED: {len(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
