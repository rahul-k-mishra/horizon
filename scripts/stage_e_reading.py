"""
stage_e_reading.py -- EXPLORATORY.  The reading of stage E, the censored development search (campaign
dev-minigrid-e, rows horizon.search.v3; docs/design/STAGE_E_OPTIONS.md, Section 4).  Development data only:
nothing here is evidence for any claim, and every line it prints is labelled EXPLORATORY.  It decides nothing and
changes no registered file.  Its job is to put on record, before the author fixes a ceiling C and a primary
search score, what each choice does to the development counts.

Reads only committed files:
    runs/dev-minigrid-e/devsearch/*.json    stage E's rows (schema horizon.search.v3)
    runs/dev-minigrid/devsearch/*.json      stage D's rows, for the agreement check
    D:\\Research\\arc3\\repo (read-only)     study 1's macro rows and truth table, as scripts/dev_reading.py reads them
    docs/truth/gvgai.json                   the confirmatory mechanics scores, through scripts/sdd.py
Writes logs/stage_e_reading.log (through the redirect below) and docs/design/stage_e_reading.json.

Scores, for a ceiling C at or below the run's seen cap (larger = predicted easier):
    H_C   -log10 min(R, C): R the states seen of a complete search; a search that saw at least C states before it
          stopped sits at -log10 C; a search stopped by the time or memory cap before seeing C states, without
          completing, is excluded (h_c below).
    L_C   -L if the first win state was seen among the first C states seen; a search that completed, or saw at
          least C states, without that is "beyond C", ranked last and tied; otherwise excluded (l_c below).
Sections:
  1  the rows: count, schema, caps hit, seconds; the units that are missing.
  2  agreement with stage D: on every unit stage D finished with at most the seen cap of states, stage E must
     finish with the same states seen, states expanded and solution length (the search is deterministic).
  3  per C: units determined and units at the ceiling for H_C and L_C; AUROC of each per agent over
     between-game pairs, overall, MiniGrid and BabyAI, and over pairs of games with the same mechanics score;
     95% bootstrap intervals of games (2,000 resamples) at every C.
  4  power on the confirmatory structure (26 clusters of 5 units, as scripts/stage_e_diagnosis.py, Section 6) for
     H_C and L_C at every C, all between-game pairs and pairs of games with the same mechanics score.
Run (working directory D:\\Research\\horizon\\repo), once every chunk of dev-minigrid-e is done:
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\stage_e_reading.py --workers 4 > logs\\stage_e_reading.log
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import stage_e_diagnosis as D  # noqa: E402 -- pair statistics, bootstrap, simulation and the study-1 loader

TAG = "EXPLORATORY"
E_ROWS = os.path.join(REPO, "runs", "dev-minigrid-e", "devsearch")
OUT = os.path.join(REPO, "docs", "design", "stage_e_reading.json")
CEILINGS = (10_000, 100_000, 300_000, 1_000_000, 2_000_000)
INF = -1e18
AGENTS = D.AGENTS


def determined(r, c):
    return r["complete"] or r["counts"]["states_seen"] >= c


def h_c(r, c):
    """-log10 min(R, C), or nan when the unit stopped before seeing C states without completing."""
    if not determined(r, c):
        return math.nan
    return -math.log10(min(r["counts"]["states_seen"], c))


def l_c(r, c):
    """-L when the first win was seen among the first C states; INF (beyond C, ranked last) when the unit is
    determined at C without that; nan otherwise."""
    s = r["counts"]["seen_at_first_win"]
    if s is not None and s <= c:
        return -float(r["counts"]["solution_length"])
    return INF if determined(r, c) else math.nan


def read_rows(folder):
    rows = {}
    for p in sorted(glob.glob(os.path.join(folder, "*.json"))):
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        rows[(r["game"], int(r["level"]))] = r
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-repo", default=r"D:\Research\arc3\repo")
    ap.add_argument("--workers", type=int, default=4)
    a_ = ap.parse_args(argv)
    print(f"stage_e_reading -- {TAG}: development reading of stage E (campaign dev-minigrid-e); development data, "
          f"not evidence for any claim")
    rows = read_rows(E_ROWS)
    if not rows:
        print(f"waiting: no stage E rows under {os.path.relpath(E_ROWS, REPO)}")
        return 2
    d_search, games, data = D.load(a_.old_repo)
    out = {}

    # ---- 1. rows
    print(f"\n== 1. the rows ({TAG}) ==")
    schemas = collections.Counter(r["schema"] for r in rows.values())
    caps = collections.Counter(r["cap_hit"] if r["capped"] else "none" for r in rows.values())
    seen_caps = sorted({r["caps"]["seen_cap"] for r in rows.values()})
    missing = sorted(set(d_search) - set(rows))
    secs = sorted(r["seconds_spent"] for r in rows.values())
    print(f"rows {len(rows)} of {len(d_search)} units; schemas {dict(schemas)}; seen caps {seen_caps}; stopped by "
          f"{dict(caps)}; units missing {len(missing)}; seconds per unit median {secs[len(secs) // 2]:.0f}, "
          f"largest {secs[-1]:.0f}, sum {sum(secs):.0f}")
    run_cap = min(seen_caps)
    out["rows"] = dict(rows=len(rows), schemas=dict(schemas), caps=dict(caps), seen_caps=seen_caps, missing=len(missing))

    # ---- 2. agreement with stage D
    print(f"\n== 2. agreement with stage D ({TAG}) ==")
    agree, differ, checked = 0, [], 0
    for k, rd in d_search.items():
        if k not in rows or not rd["complete"] or rd["counts"]["states_seen"] > run_cap:
            continue
        checked += 1
        re_ = rows[k]
        same = re_["complete"] and all(re_["counts"][x] == rd["counts"][x]
                                       for x in ("states_seen", "states_expanded", "solution_length"))
        agree += same
        if not same:
            differ.append(f"{k[0]} s{k[1]}")
    print(f"units stage D finished with at most {run_cap:,} states: {checked}; the same states seen, states expanded "
          f"and solution length in stage E: {agree}; different: {len(differ)}" + (f" ({', '.join(differ[:10])})" if differ else ""))
    out["agreement"] = dict(checked=checked, same=agree, different=differ)

    # ---- 3. per ceiling
    print(f"\n== 3. censored scores per ceiling ({TAG}) ==")
    p3 = {}
    for c in [x for x in CEILINGS if x <= run_cap]:
        line = {}
        for sname, fn in (("H_C", h_c), ("L_C", l_c)):
            vals = {k: fn(r, c) for k, r in rows.items()}
            det = sum(not math.isnan(v) for v in vals.values())
            top = sum(v == (-math.log10(c) if sname == "H_C" else INF) for v in vals.values() if not math.isnan(v))
            ent = dict(determined=det, excluded=len(vals) - det, at_ceiling_or_beyond=top, agents={})
            txt = []
            for ag in AGENTS:
                keys = sorted(k for k in data[ag] if k in vals and not math.isnan(vals[k]))
                gid = {g: i for i, g in enumerate(games)}
                a = dict(y=np.array([data[ag][k]["y"] for k in keys], bool),
                         S_M=np.array([data[ag][k]["S_M"] for k in keys], float),
                         game=np.array([gid[k[0]] for k in keys]),
                         fam=np.array([0 if k[0].startswith("MiniGrid") else 1 for k in keys]),
                         s=np.array([vals[k] for k in keys], float))
                res = {}
                for lab, mask in (("overall", np.ones(len(keys), bool)), ("MiniGrid", a["fam"] == 0),
                                  ("BabyAI", a["fam"] == 1)):
                    res[lab] = D.auroc_nested(a["s"][mask], a["y"][mask], a["game"][mask])
                res["same S_M"] = D.auroc_nested(a["s"], a["y"], a["game"], a["S_M"])
                res["ci95 overall"] = D.boot_ci(a, "s", a_.workers)[0]
                res["ci95 same S_M"] = D.boot_ci(a, "s", a_.workers, strat=True)[0]
                ent["agents"][ag] = res
                txt.append(f"{ag} {D.f4(res['overall'])} [{res['ci95 overall'][0]:.4f}, {res['ci95 overall'][1]:.4f}] "
                           f"(MiniGrid {D.f4(res['MiniGrid'])}, BabyAI {D.f4(res['BabyAI'])}; same S_M "
                           f"{D.f4(res['same S_M'])} [{res['ci95 same S_M'][0]:.4f}, {res['ci95 same S_M'][1]:.4f}])")
            word = "at the ceiling" if sname == "H_C" else "beyond C"
            print(f"  C {c:>9,} {sname}: determined {D.pc(det, len(vals))}, excluded {len(vals) - det}, {word} "
                  f"{D.pc(top, len(vals))}; AUROC with 95%: " + "; ".join(txt))
            line[sname] = ent
        p3[str(c)] = line
    out["per_ceiling"] = p3

    # ---- 4. power on the confirmatory structure
    print(f"\n== 4. power on the confirmatory structure ({TAG}; method of scripts/stage_e_diagnosis.py, Section 6) ==")
    import sdd  # noqa: PLC0415
    smv = [float(v) for v in sdd.confirmatory_mechanics()[0].values()]
    p4 = {}
    for c in [x for x in CEILINGS if x <= run_cap]:
        for sname, fn in (("H_C", h_c), ("L_C", l_c)):
            for ag in AGENTS:
                vals = {k: fn(r, c) for k, r in rows.items()}
                keys = [k for k in data[ag] if k in vals and not math.isnan(vals[k])]
                per = collections.defaultdict(list)
                for k in keys:
                    per[k[0]].append((vals[k], data[ag][k]["y"]))
                cl = [(np.array([x for x, _ in v], float), np.array([y for _, y in v], bool)) for _, v in sorted(per.items())]
                plain, strat = D.simulate(cl, smv, a_.workers)
                r = {lab: {alab: D.power_summary(v, al) for alab, al in (("98.33%", D.ALPHA), ("95%", 0.05))}
                     for lab, v in (("all", plain), ("same S_M", strat))}
                p4[f"{c} {sname} {ag}"] = r
                print(f"  C {c:>9,} {sname} {ag}: all pairs mean {r['all']['98.33%']['mean']:.4f} SE "
                      f"{r['all']['98.33%']['se']:.4f} power 98.33% {r['all']['98.33%']['power_above_half']:.4f} "
                      f"95% {r['all']['95%']['power_above_half']:.4f}; same S_M mean {r['same S_M']['98.33%']['mean']:.4f} "
                      f"SE {r['same S_M']['98.33%']['se']:.4f} power 98.33% {r['same S_M']['98.33%']['power_above_half']:.4f} "
                      f"95% {r['same S_M']['95%']['power_above_half']:.4f}")
    out["power"] = p4

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(label=TAG, **out), f, indent=1)
    print(f"\nwritten {os.path.relpath(OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
