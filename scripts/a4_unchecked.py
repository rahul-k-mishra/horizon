"""
a4_unchecked.py -- the ways an avatar's move can be cancelled, and which of them the generator checks
for A4's first clause: every move the avatar makes without effect is explained by a sprite that blocks
it (docs/PREREG.md draft v0, Section 5).  GVGAI's undoAll puts every sprite back, whichever sprite is
named first (third_party/gvgai/src/ontology/effects/unary/UndoAll.java:40-57), so an undoAll line that
does not name the avatar first also cancels the avatar's move.  Until 25 October 2026 the generator
looked only at lines with the avatar first; since then (docs/STATE.md, amendment (l)) it also checks
every such undoAll line (scripts/truth_vgdl.py, cancelling_lines).  For each deterministic game this
script lists those lines and whether the A4 clauses of docs/truth/gvgai.json cite each one, counts the
games where A4 holds and such a line exists, and lists every effect the descriptions apply to the
avatar as the first sprite and any notStype option, so that a way of cancelling a move other than
stepBack and undoAll would show.  It decides nothing and changes no verdict.

Reads only the vendored GVGAI files and docs/truth/gvgai.json, through scripts/truth_vgdl.py.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\a4_unchecked.py > logs\\a4_unchecked.log
"""
from __future__ import annotations

import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import draw_pilot  # noqa: E402  (the registered pilot draw)
import numpy as np  # noqa: E402
import truth_vgdl as tv  # noqa: E402

GP = os.path.join(REPO, "third_party", "gvgai", "examples", "gridphysics")


def main():
    with open(os.path.join(REPO, "docs", "truth", "gvgai.json"), encoding="utf-8") as f:
        truth = json.load(f)["games"]
    det = sorted(g for g, v in truth.items() if v["deterministic"])
    idx = np.random.default_rng(draw_pilot.SEED).choice(len(det), draw_pilot.N_PILOT, replace=False)
    pilot = {det[i] for i in idx}
    print(f"a4_unchecked: {len(det)} deterministic games, {len(det) - len(pilot)} confirmatory")
    hit = {"confirmatory": [], "pilot": []}
    checked = {"confirmatory": 0, "pilot": 0}
    first = collections.Counter()
    nots = []
    for g in det:
        d = tv.parse(os.path.join(GP, f"{g}.txt"))
        av = tv.avatar_types(d)
        for it in d["inter"]:
            if tv.touches_avatar(d, it["names"][0], av):
                first[it["effect"]] += 1
            if "notStype" in it["params"]:
                nots.append(f"{g} line {it['line']}")
        lines = [it for it in d["inter"] if it["effect"] == "undoAll" and not tv.touches_avatar(d, it["names"][0], av)]
        a4 = {truth[g]["levels"][k]["A4"]["verdict"] for k in truth[g]["levels"]}
        tag = "pilot" if g in pilot else "confirmatory"
        if lines:
            names_av = sum(any(tv.touches_avatar(d, n, av) for n in it["names"][1:]) for it in lines)
            cited = {c["line"] for k in truth[g]["levels"] for c in truth[g]["levels"][k]["A4"]["clauses"]}
            n_cited = sum(it["line"] in cited for it in lines)
            print(f"{g} ({tag}, A4 {'/'.join(sorted(a4))}): {len(lines)} undoAll line(s) without the avatar first, "
                  f"{names_av} of them naming the avatar later, {n_cited} cited by the A4 clauses: "
                  + "; ".join(f"line {it['line']} `{it['text']}`" for it in lines))
            checked[tag] += n_cited == len(lines)
            if a4 == {"holds"}:
                hit[tag].append(g)
    for tag, n_all in (("confirmatory", len(det) - len(pilot)), ("pilot", len(pilot))):
        print(f"{tag} games where A4 holds and such a line exists: {len(hit[tag])} of {n_all}"
              + (f" ({', '.join(hit[tag])})" if hit[tag] else ""))
        print(f"{tag} games with such lines, every one cited by the A4 clauses: {checked[tag]}")
    print("effects applied to the avatar as the first sprite, in the deterministic games (lines): "
          + ", ".join(f"{k} {v}" for k, v in first.most_common()))
    print(f"undoAll lines with a notStype option in the deterministic games: {', '.join(nots) if nots else 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
