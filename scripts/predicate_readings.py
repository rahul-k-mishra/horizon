"""
predicate_readings.py -- for the four questions of docs/truth/PREDICATE_QUESTIONS.md, which (game, level)
verdicts would change if the registered predicate were read the other way.  EXPLORATORY: it decides
nothing and changes no predicate; docs/truth/gvgai.json stays the answer key until the author decides.

Reads only the vendored GVGAI files and docs/truth/gvgai.json, through scripts/truth_vgdl.py (imported).
Plays nothing.  For each question it recomputes one predicate on every game with one reading changed:
  Q1  A2 also fails where an interaction with an avatar type as partner creates a sprite (a spawn or a
      transform of a sprite other than the avatar), not only where the use action does (painter).
  Q2  A4: a transform of a blocking sprite into another blocking type, in the same cell, does not count
      as creating or removing a blocker (rivers).
  Q3  A4 also fails where the blocking types differ between the avatar's subtypes, so that changing
      subtype changes which sprites block (labyrinthdual).
  Q4  A4: undoAll blocks the avatar wherever the avatar is named in the line, not only when it is named
      first (colourescape).
  Q4b Q4, with an interaction counted as the avatar's own when every placeable (leaf) type a name stands
      for is agent-driven, rather than every type including an unplaced parent such as colourescape's
      "boxes" (line 62); with the present reading this changes no verdict on any unit, which is checked.
A4 is recomputed by a copy of the generator's pred_A4 with the readings as switches; with every switch
off the copy must give the generator's verdict on every unit, which the script checks first.  It
reports the units and games that change, among the 30 deterministic games and the 26 confirmatory
games (the deterministic games less the pilot drawn by scripts/draw_pilot.py), and S_M on the 26.

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\predicate_readings.py > logs\\predicate_readings.log
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
TRUTH = os.path.join(REPO, "docs", "truth", "gvgai.json")


def a2_alt(d, av, start_av, n_av, pos, level_path):
    v, _ = tv.pred_A2(d, av, start_av, n_av, pos, level_path)
    if v == "fails":
        return v
    for it in d["inter"]:
        if it["effect"] in tv.CREATE_EFFECTS and members_not_avatar(d, it["names"][0], av) and \
                any(tv.touches_avatar(d, p, av) for p in it["names"][1:]):
            return "fails"
    return "holds"


def members_not_avatar(d, name, av):
    return bool(tv.members(d, name) - av)


def caused_by_avatar_leaves(d, it, driven):
    return any(tv.members(d, n) and tv.leaves(d, tv.members(d, n)) <= driven for n in it["names"])


def a4(d, av, q2=False, q3=False, q4=False, leaf=False):
    """The generator's pred_A4, verdict only, with the readings of Q2 to Q4b as switches."""
    caused = caused_by_avatar_leaves if leaf else tv.caused_by_avatar
    driven = tv.agent_driven(d, av)
    blocking = {}
    for it in d["inter"]:
        if it["effect"] not in tv.BLOCK_EFFECTS:
            continue
        first = tv.touches_avatar(d, it["names"][0], av)
        anywhere = it["effect"] == "undoAll" and any(tv.touches_avatar(d, n, av) for n in it["names"])
        if first or (q4 and anywhere):
            for p in it["names"]:
                if p == "EOS" or (first and p == it["names"][0]):
                    continue
                for b in tv.leaves(d, tv.members(d, p)) - av:
                    blocking.setdefault(b, it)
    if not blocking:
        return "holds"
    if q3:
        per = {}
        for a in tv.leaves(d, av):
            per[a] = frozenset(b for it in d["inter"] if it["effect"] in tv.BLOCK_EFFECTS and a in tv.members(d, it["names"][0])
                               for p in it["names"][1:] if p != "EOS" for b in tv.leaves(d, tv.members(d, p)) - av)
        if len(set(per.values())) > 1:
            return "fails"
    for b in blocking:
        sp = d["sprites"][b]
        if sp["cls"] not in tv.STILL:
            return "fails"
        for n, ps in d["sprites"].items():
            if ps["cls"] in tv.PRODUCERS and ps["params"].get("stype") and b in tv.members(d, ps["params"]["stype"]):
                return "fails"
        for it2 in d["inter"]:
            st = it2["params"].get("stype")
            if q2 and it2["effect"].startswith("transform") and st and tv.members(d, st) and \
                    tv.leaves(d, tv.members(d, st)) <= set(blocking) and \
                    tv.leaves(d, tv.members(d, it2["names"][0])) <= set(blocking):
                continue
            creates = it2["effect"] in tv.CREATE_EFFECTS and bool(st) and b in tv.members(d, st)
            removes = (it2["effect"] in tv.REMOVE_EFFECTS and b in tv.members(d, it2["names"][0])) or \
                      (it2["effect"] in tv.REMOVE_BY_STYPE and bool(st) and b in tv.members(d, st))
            moves = it2["effect"] in tv.MOVERS_ANY and b in tv.members(d, it2["names"][0])
            if (creates or removes or moves) and not caused(d, it2, driven):
                return "fails"
    return "holds"


def main():
    with open(TRUTH, encoding="utf-8") as f:
        truth = json.load(f)["games"]
    det = sorted(g for g, v in truth.items() if v["deterministic"])
    idx = np.random.default_rng(draw_pilot.SEED).choice(len(det), draw_pilot.N_PILOT, replace=False)
    pilot = {det[i] for i in idx}
    conf = [g for g in det if g not in pilot]
    print(f"predicate_readings (EXPLORATORY): {len(truth)} games in docs/truth/gvgai.json, "
          f"{len(det)} deterministic, {len(conf)} confirmatory (pilot {', '.join(sorted(pilot))})")
    new = collections.defaultdict(dict)   # question -> {(game, level): verdict}
    mismatch = []
    for g in sorted(truth):
        d = tv.parse(os.path.join(GP, f"{g}.txt"))
        av = tv.avatar_types(d)
        for k in truth[g]["levels"]:
            lp = os.path.join(GP, f"{g}_lvl{k}.txt")
            counts = tv.level_counts(d, lp)
            start_av = {n for n in av if counts.get(n)}
            pos = sorted(p for n in av for p in counts.get(n, []))
            if a4(d, av) != truth[g]["levels"][k]["A4"]["verdict"] or a4(d, av, leaf=True) != a4(d, av):
                mismatch.append((g, k))
            new["Q1"][g, k] = a2_alt(d, av, start_av, len(pos), pos, lp)
            new["Q2"][g, k] = a4(d, av, q2=True)
            new["Q3"][g, k] = a4(d, av, q3=True)
            new["Q4"][g, k] = a4(d, av, q4=True)
            new["Q4b"][g, k] = a4(d, av, q4=True, leaf=True)
    print(f"self-check: the copy of pred_A4 with every switch off gives the generator's A4 verdict on "
          f"{sum(len(truth[g]['levels']) for g in truth) - len(mismatch)} of {sum(len(truth[g]['levels']) for g in truth)} units, "
          f"and with the leaf count of Q4b alone it gives the same" + (f"; differs on {mismatch}" if mismatch else ""))
    if mismatch:
        return 1
    pred = {"Q1": "A2", "Q2": "A4", "Q3": "A4", "Q4": "A4", "Q4b": "A4"}
    sm0 = {g: sum(truth[g]["levels"]["0"][p]["verdict"] == "holds" for p in tv.PREDICATES) for g in conf}
    print(f"S_M on the {len(conf)} confirmatory games now: " + ", ".join(
        f"{s}: {c}" for s, c in sorted(collections.Counter(sm0.values()).items())))
    for q in ("Q1", "Q2", "Q3", "Q4", "Q4b"):
        p = pred[q]
        ch = sorted((g, k) for (g, k), v in new[q].items() if v != truth[g]["levels"][k][p]["verdict"])
        games = sorted({g for g, _ in ch})
        print(f"\n== {q} ({p} read the other way)")
        for g in games:
            ks = [k for gg, k in ch if gg == g]
            tag = "confirmatory" if g in conf else ("pilot" if g in pilot else "not deterministic")
            print(f"{g} ({tag}): {p} {truth[g]['levels'][ks[0]][p]['verdict']} -> {new[q][g, ks[0]]} on levels {', '.join(ks)}")
        nd = sum(1 for g, _ in ch if g in det)
        nc = sum(1 for g, _ in ch if g in conf)
        print(f"units changed: {len(ch)} of all, {nd} of the deterministic, {nc} of the confirmatory; "
              f"games changed: {len(games)} of all, {sum(g in det for g in games)} deterministic, "
              f"{sum(g in conf for g in games)} confirmatory")
        sm = {g: sm0[g] + (new[q][g, "0"] == "holds") - (truth[g]["levels"]["0"][p]["verdict"] == "holds") for g in conf}
        print(f"S_M on the confirmatory games under this reading: " + ", ".join(
            f"{s}: {c}" for s, c in sorted(collections.Counter(sm.values()).items())))
        held = sum(new[q][g, "0"] == "holds" for g in conf)
        print(f"{p} holds on {held} of the {len(conf)} confirmatory games under this reading, "
              f"{sum(truth[g]['levels']['0'][p]['verdict'] == 'holds' for g in conf)} now")
    return 0


if __name__ == "__main__":
    sys.exit(main())
