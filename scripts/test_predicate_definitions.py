"""
test_predicate_definitions.py -- tests of docs/truth/PREDICATE_DEFINITIONS.md, the only definition text the author
reads during the blind hand check (docs/PREREG.md, Section 5, decided 28 November 2026).  Reads committed files only.

1. Registered wording: the file has one section per predicate, A1 to A5, each with one question and its definition.
   Every piece of each definition, cut at the marks [...] where something was left out, is word for word a piece of
   the bullet of that predicate in docs/PREREG.md, Section 5 (bold marks removed); and every piece of the paragraph
   "From Section 1:" under A4 is word for word a piece of Section 1's bullet on A4's first clause, where each mark
   [a game] stands for one word, the name of a game the file does not give (added 28 November 2026).
2. No game: the file names none of the 30 deterministic games of scripts/suite.py (the suite, the pilot and the pool
   of the fresh rounds), none of the games of the fresh draws, and none of the other games of
   third_party/gvgai/examples/gridphysics, matched as whole words without regard to case.
3. No verdict: every use of holds, hold, holding, fails, fail and verdict in the file is one of the fixed forms in
   which the definitions and questions state their rule; none is a statement about a game.  No digit appears outside
   the predicate names, the rule's own "speed 1", "speed other than 1" and "limit 0", and "Section 5" and "Section 1".
4. The questions: each section's question is a single line beginning "Question: " and ending with a question mark,
   and the app reads its questions from this file (added 28 November 2026; until then from
   docs/truth/HANDCHECK_GUIDE.md).
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
import handcheck_app as app  # noqa: E402

DEFS = os.path.join(REPO, "docs", "truth", "PREDICATE_DEFINITIONS.md")
PRED = ("A1", "A2", "A3", "A4", "A5")
SEC1_PREFIX = "From Section 1: "
RULE_FORMS = ["A1 holds iff", "Fails if", "A2 holds iff", "It fails if", "A2 also fails wherever", "A3 holds iff",
              "It fails for", "A4 holds iff", "holds A4, because", "A5 holds iff", "the level holds exactly one",
              "keeps A5 holding", "otherwise A4 fails", "of which the level holds exactly one"]
ALLOWED_NUMBERS = ["at least two actions", "speed 1", "speed other than 1", "limit 0", "Section 5", "Section 1"]
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
    sec1 = prereg[prereg.index("## 1. "):prereg.index("## 2. ")].replace("**", "")
    a4_sec1 = next((ln for ln in sec1.splitlines() if ln.startswith("- A4's first clause")), "")
    pieces = sec1_pieces = 0
    questions = {}
    for p in PRED:
        paras = [x.strip() for x in sections.get(p, "").split("\n\n") if x.strip()]
        q = paras[0] if paras else ""
        questions[p] = q
        check(q.startswith("Question: ") and q.endswith("?") and "\n" not in q, f"{p}: one question line")
        m = re.search(rf"^- {p} (.+)$", sec5, re.M)
        bullet = (p + " " + m.group(1)) if m else ""
        for para in paras[1:]:
            if para.startswith(SEC1_PREFIX):
                check(p == "A4", f"{p}: a paragraph from Section 1 only under A4")
                for piece in para[len(SEC1_PREFIX):].split("[...]"):
                    piece = piece.strip()
                    if piece:
                        sec1_pieces += 1
                        pat = re.escape(piece).replace(re.escape("[a game]"), r"\w+")
                        check(re.search(pat, a4_sec1) is not None,
                              f"A4: \"{piece[:50]}...\" is word for word in PREREG Section 1, game names apart")
                continue
            for piece in para.split("[...]"):
                piece = piece.strip()
                if piece:
                    pieces += 1
                    check(piece in bullet, f"{p}: \"{piece[:50]}...\" is word for word in PREREG Section 5's {p}")
    print(f"1. registered wording: {pieces} pieces each word for word in their predicate's bullet of Section 5, and "
          f"{sec1_pieces} pieces of A4's paragraph from Section 1 word for word in its bullet there, game names apart")

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

    got = app.definitions()
    check(all(got[p][0] == questions[p][len("Question: "):] for p in PRED),
          "4. the app reads each question from this file")
    with open(os.path.join(HERE, "handcheck_app.py"), encoding="utf-8") as f:
        app_text = f.read()
    check("HANDCHECK_GUIDE.md\")" not in app_text and "GUIDE = " not in app_text,
          "4. the app names no path to docs/truth/HANDCHECK_GUIDE.md to read")
    print("OK" if not FAILS else f"FAILED: {len(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
