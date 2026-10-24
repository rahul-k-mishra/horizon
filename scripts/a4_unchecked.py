"""
a4_unchecked.py -- where the first clause of A4 is not checked by the generator.  A4 says every move the
avatar makes without effect is explained by a sprite that blocks it (docs/PREREG.md draft v0, Section
5); scripts/truth_vgdl.py examines only the sprites named after the avatar in a stepBack or undoAll line
with the avatar first.  GVGAI's undoAll puts every sprite back, whichever sprite is named first
(third_party/gvgai/src/ontology/effects/unary/UndoAll.java:40-57), so an undoAll line that does not
name the avatar first also cancels the avatar's move, and the generator does not look at it.  This
script lists, for each deterministic game, every such line, and counts the games where A4 holds in
docs/truth/gvgai.json and such a line exists: the games where the answer key's A4 rests on a check
narrower than the predicate's wording.  It decides nothing and changes no verdict.

Reads only the vendored GVGAI files and docs/truth/gvgai.json, through scripts/truth_vgdl.py.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\a4_unchecked.py > logs\\a4_unchecked.log
"""
from __future__ import annotations

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
    for g in det:
        d = tv.parse(os.path.join(GP, f"{g}.txt"))
        av = tv.avatar_types(d)
        lines = [it for it in d["inter"] if it["effect"] == "undoAll" and not tv.touches_avatar(d, it["names"][0], av)]
        a4 = {truth[g]["levels"][k]["A4"]["verdict"] for k in truth[g]["levels"]}
        tag = "pilot" if g in pilot else "confirmatory"
        if lines:
            names_av = sum(any(tv.touches_avatar(d, n, av) for n in it["names"][1:]) for it in lines)
            print(f"{g} ({tag}, A4 {'/'.join(sorted(a4))}): {len(lines)} undoAll line(s) without the avatar first, "
                  f"{names_av} of them naming the avatar later: "
                  + "; ".join(f"line {it['line']} `{it['text']}`" for it in lines))
            if a4 == {"holds"}:
                hit[tag].append(g)
    for tag, n_all in (("confirmatory", len(det) - len(pilot)), ("pilot", len(pilot))):
        print(f"{tag} games where A4 holds and such a line exists: {len(hit[tag])} of {n_all}"
              + (f" ({', '.join(hit[tag])})" if hit[tag] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
