"""
stage_e_diagnosis.py -- EXPLORATORY.  What stage D says about whether the registered contrast of docs/PREREG.md
draft v0 can be tested as written, and the counts behind each option of docs/design/STAGE_E_OPTIONS.md.
Development data only: nothing here is evidence for any claim, and every line it prints is labelled EXPLORATORY.
It decides nothing and changes no registered file.

Reads only committed files:
    runs/dev-minigrid/devsearch/*.json     stage D's 1,560 search rows
    docs/design/sdd.json                    the smallest detectable difference of scripts/sdd.py
    docs/truth/gvgai.json                   the confirmatory mechanics scores, through scripts/sdd.py
    D:\\Research\\arc3\\repo (read-only)     study 1's macro rows and truth table, through scripts/oracle_v2.py
Writes logs/stage_e_diagnosis.log (through the redirect below) and docs/design/stage_e_diagnosis.json.

Sections:
  1  power of the registered contrast at the development Delta, from docs/design/sdd.json: the probability that
     the registered 98.33% interval excludes zero if the true Delta equals the development value, under the
     normal approximation scripts/sdd.py uses; and the number of game clusters at which it would reach 0.80.
  2  where the development Delta comes from: the mechanics score per family; AUROC of H and of S_M over
     between-game pairs split into pairs inside MiniGrid, inside BabyAI, and across the two families.
  3  censoring: the search score H_C = -log10 min(R, C), with R the states seen (a lower bound on R for a capped
     unit).  A unit is determined when it completed, or when it saw at least C states before it stopped; it
     then sits at the ceiling.  Per C: units determined, units at the ceiling, and AUROC of H_C per agent.
  4  the agents: agreement of N, R and I1 per unit and per game.
  5  within-game variation of the outcome.
  6  power of smaller claims on the confirmatory structure (26 clusters of 5 units when logs/stage_e_diagnosis.log was
     written; sdd.N_CLUSTERS, one per confirmatory game, which is 25 since the fit rule of 14 November 2026; the
     25-game values are in logs/power_primary.log), between-game pairs:
     AUROC of H_C, and of L (the fewest actions to a win), above one half, over all between-game pairs and over
     pairs of games with the same mechanics score; and the true AUROC at which power would be 0.80.
  7  the stratified reading on development data: AUROC of H_C and of L over between-game pairs whose games have
     the same development mechanics score, with a bootstrap interval.

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\stage_e_diagnosis.py --workers 4 > logs\\stage_e_diagnosis.log
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import dev_reading as DR  # noqa: E402 -- stage D's reader and the registered AUROC, unchanged
import sdd  # noqa: E402 -- the confirmatory mechanics scores, unchanged

TAG = "EXPLORATORY"
AGENTS = ("N", "R", "I1")
ALPHA = 0.05 / 3
CEILINGS = (10_000, 100_000, 300_000, 1_000_000, 2_000_000, 3_000_000, 5_000_000)
C_PROPOSED = 1_000_000
N_BOOT, BOOT_SEED, CHUNKS = 2000, 20261113, 8
SIMS, SIM_SEED, LEVELS = 4000, 20261114, 5
OUT = os.path.join(REPO, "docs", "design", "stage_e_diagnosis.json")
ND = statistics.NormalDist()


# ---------------------------------------------------------------- pair statistics
def u_within(score, y, grp):
    """Mann-Whitney U and pair count over positive-negative pairs inside each group."""
    r = DR._ranks_within(score, grp)
    _, gi = np.unique(grp, return_inverse=True)
    n1 = np.bincount(gi, weights=y.astype(float))
    n = np.bincount(gi).astype(float)
    return r[y].sum() - (n1 * (n1 + 1) / 2).sum(), (n1 * (n - n1)).sum()


def auroc_nested(score, y, game, outer=None):
    """AUROC over pairs from different games; with outer, only pairs inside the same outer group (games nest in
    outer groups).  None if no pair."""
    score, y, game = np.asarray(score, float), np.asarray(y, bool), np.asarray(game)
    outer = np.zeros(len(y), int) if outer is None else np.asarray(outer)
    uo, po = u_within(score, y, outer)
    ug, pg = u_within(score, y, game)
    return None if po - pg <= 0 else float((uo - ug) / (po - pg))


def auroc_across(score, y, game, outer):
    """AUROC over pairs whose two units lie in different outer groups."""
    score, y = np.asarray(score, float), np.asarray(y, bool)
    ua, pa = u_within(score, y, np.zeros(len(y), int))
    uo, po = u_within(score, y, np.asarray(outer))
    return None if pa - po <= 0 else float((ua - uo) / (pa - po))


def pairs_count(y, game, outer=None):
    y, game = np.asarray(y, bool), np.asarray(game)
    outer = np.zeros(len(y), int) if outer is None else np.asarray(outer)
    s = np.zeros(len(y))
    return int(u_within(s, y, outer)[1] - u_within(s, y, game)[1])


# ---------------------------------------------------------------- input
def h_c(r, c):
    """-log10 min(R, C), or nan when the unit stopped before seeing C states without completing."""
    seen = r["counts"]["states_seen"]
    if r["complete"]:
        return -math.log10(min(seen, c))
    return -math.log10(c) if seen >= c else math.nan


def load(old):
    search = DR.read_search()
    games = sorted({g for g, _ in search})
    DR.O.load_old(old)
    C = DR.O.C
    truth = {"minigrid": C.parse_truth_minigrid(os.path.join(old, "docs", "GROUND_TRUTH_minigrid.md")),
             "procgen": C.parse_truth_procgen(os.path.join(old, "docs", "GROUND_TRUTH_procgen.md"))}
    conf = {s: set(C.confirmatory(s, truth[s])) for s in truth}
    oracle = DR.O.oracle_vectors(truth, conf)[("minigrid", "macro")]
    rows, _ = DR.O.read_rows(old, conf)
    data = {}
    for ag in AGENTS:
        recs = {}
        for r in rows:
            if r["suite"] != "minigrid" or r["condition"] != "macro" or r["agent"] != ag:
                continue
            key = (r["game"], int(r["seed"]))
            if key in search:
                recs[key] = dict(y=bool(r["level1_completed"]),
                                 S_M=float(sum(oracle[r["game"]][x] == C.HOLDS for x in C.ASSUMPTIONS)))
        data[ag] = recs
    return search, games, data


def arrays(search, games, recs, keys=None):
    keys = sorted(k for k in recs if keys is None or k in keys)
    gid = {g: i for i, g in enumerate(games)}
    a = dict(keys=keys,
             y=np.array([recs[k]["y"] for k in keys], bool),
             S_M=np.array([recs[k]["S_M"] for k in keys], float),
             game=np.array([gid[k[0]] for k in keys]),
             fam=np.array([0 if k[0].startswith("MiniGrid") else 1 for k in keys]),
             H=np.array([DR.search_scores(search[k])["H"] for k in keys], float),
             L=np.array([DR.search_scores(search[k])["L"] for k in keys], float))
    for c in CEILINGS:
        a[c] = np.array([h_c(search[k], c) for k in keys], float)
    return a


def sub(a, mask):
    return {k: (v[mask] if isinstance(v, np.ndarray) else [x for x, m in zip(v, mask) if m]) for k, v in a.items()}


def defined(a, score):
    return sub(a, ~np.isnan(a[score]))


# ---------------------------------------------------------------- bootstrap and simulation
def _boot(args):
    a, score, strat, n, k = args
    rng = np.random.default_rng([BOOT_SEED, k])
    gs = np.unique(a["game"])
    idx = {g: np.flatnonzero(a["game"] == g) for g in gs}
    out = []
    for _ in range(n):
        pick = gs[rng.integers(0, len(gs), len(gs))]
        sel = np.concatenate([idx[g] for g in pick])
        y = a["y"][sel]
        if y.all() or not y.any():
            continue
        v = auroc_nested(a[score][sel], y, a["game"][sel], a["S_M"][sel] if strat else None)
        if v is not None:
            out.append(v)
    return out


def boot_ci(a, score, workers, strat=False):
    per = [N_BOOT // CHUNKS + (1 if k < N_BOOT % CHUNKS else 0) for k in range(CHUNKS)]
    with ProcessPoolExecutor(workers) as ex:
        res = [v for r in ex.map(_boot, [(a, score, strat, per[k], k) for k in range(CHUNKS)]) for v in r]
    return (float(np.percentile(res, 2.5)), float(np.percentile(res, 97.5))), len(res)


def _sim(args):
    clusters, sm_games, n, k = args
    rng = np.random.default_rng([SIM_SEED, k])
    plain, strat = [], []
    for _ in range(n):
        hs, ys, gs, ms = [], [], [], []
        for j, c in enumerate(rng.integers(0, len(clusters), sdd.N_CLUSTERS)):
            h, y = clusters[c]
            take = rng.choice(len(y), LEVELS, replace=len(y) < LEVELS)
            hs.append(h[take]); ys.append(y[take]); gs.append(np.full(LEVELS, int(c)))
            ms.append(np.full(LEVELS, sm_games[int(rng.integers(0, len(sm_games)))]))
        h, y, g, m = map(np.concatenate, (hs, ys, gs, ms))
        if y.all() or not y.any():
            continue
        # a game drawn twice keeps one label, so pairs between its two draws are within-game, as registered;
        # the mechanics label is per draw, so a game drawn twice may carry two labels: strata use the draw
        p = auroc_nested(h, y, g)
        if p is not None:
            plain.append(p)
        s = auroc_nested(h, y, g * 10 + m, m)
        if s is not None:
            strat.append(s)
    return plain, strat


def simulate(clusters, sm_games, workers):
    per = [SIMS // CHUNKS + (1 if k < SIMS % CHUNKS else 0) for k in range(CHUNKS)]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(_sim, [(clusters, sm_games, per[k], k) for k in range(CHUNKS)]))
    return [v for r in res for v in r[0]], [v for r in res for v in r[1]]


def power_summary(v, alpha):
    m, se = statistics.fmean(v), statistics.stdev(v)
    z = ND.inv_cdf(1 - alpha / 2)
    return dict(mean=m, se=se, power_above_half=ND.cdf((m - 0.5) / se - z),
                share_point_at_least_070=sum(x >= 0.70 for x in v) / len(v),
                power_above_half_and_point_070=sum((x >= 0.70) and (x - z * se > 0.5) for x in v) / len(v),
                studies=len(v))


def f4(v):
    return "n/a" if v is None else f"{v:.4f}"


def pc(a, b):
    return f"{a} of {b} ({100 * a / b:.1f}%)" if b else f"{a} of 0"


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-repo", default=r"D:\Research\arc3\repo")
    ap.add_argument("--workers", type=int, default=4)
    a_ = ap.parse_args(argv)
    out = {}
    print(f"stage_e_diagnosis -- {TAG}: development data, not evidence for any claim")

    # ---- 1. power of the registered contrast
    with open(os.path.join(REPO, "docs", "design", "sdd.json"), encoding="utf-8") as f:
        S = json.load(f)
    z_a, z_b = ND.inv_cdf(1 - S["alpha"] / 2), ND.inv_cdf(S["power"])
    print(f"\n== 1. power of the registered contrast at the development Delta ({TAG}; docs/design/sdd.json) ==")
    print(f"registered alpha {S['alpha']:.6f} two-sided, z {z_a:.4f}; power target {S['power']}, z {z_b:.4f}; "
          f"{S['n_clusters']} clusters; registered d {S['registered_mdd']}")
    p1 = {}
    for ag in AGENTS:
        r = S["agents"][ag]
        d = r["delta_development"]
        row = {}
        for lab, se in (("estimate 1", r["se"]), ("estimate 2", r["se_confirmatory_structure"])):
            pw = ND.cdf(abs(d) / se - z_a) + ND.cdf(-abs(d) / se - z_a)
            need = S["n_clusters"] * ((z_a + z_b) * se / d) ** 2
            pw95 = ND.cdf(abs(d) / se - 1.959964) + ND.cdf(-abs(d) / se - 1.959964)
            mdd95 = (1.959964 + z_b) * se
            row[lab] = dict(se=se, power=pw, clusters_for_080=need, power_single_test_95=pw95, mdd_single_test_95=mdd95)
            print(f"  {ag} {lab}: development Delta {d:.4f}, SE at {S['n_clusters']} clusters {se:.4f}; power to exclude zero at the "
                  f"registered level if the true Delta were {d:.4f}: {pw:.4f}; clusters needed for power 0.80 at that "
                  f"Delta: {math.ceil(need)}; one test at 95% instead: power {pw95:.4f}, smallest detectable "
                  f"difference {mdd95:.4f}")
        p1[ag] = row
    out["power_registered"] = p1

    search, games, data = load(a_.old_repo)
    fam_of = {g: ("MiniGrid" if g.startswith("MiniGrid") else "BabyAI") for g in games}

    # ---- 2. where Delta comes from
    print(f"\n== 2. where the development Delta comes from ({TAG}) ==")
    a0 = arrays(search, games, data["N"])
    for fam, fi in (("MiniGrid", 0), ("BabyAI", 1)):
        sm = collections.Counter()
        for g in games:
            if fam_of[g] == fam:
                k = next(k for k in data["N"] if k[0] == g)
                sm[int(data["N"][k]["S_M"])] += 1
        print(f"  mechanics score per game, {fam}: " + ", ".join(f"S_M={v}: {n} games" for v, n in sorted(sm.items())))
    p2 = {}
    for ag in AGENTS:
        a = defined(arrays(search, games, data[ag]), "H")
        parts = {}
        for lab, fn in (("inside MiniGrid", lambda s: auroc_nested(s[a["fam"] == 0], a["y"][a["fam"] == 0], a["game"][a["fam"] == 0])),
                        ("inside BabyAI", lambda s: auroc_nested(s[a["fam"] == 1], a["y"][a["fam"] == 1], a["game"][a["fam"] == 1])),
                        ("across the families", lambda s: auroc_across(s, a["y"], a["game"], a["fam"])),
                        ("all between-game pairs", lambda s: auroc_nested(s, a["y"], a["game"]))):
            h, m = fn(a["H"]), fn(a["S_M"])
            if lab == "inside MiniGrid":
                n = pairs_count(a["y"][a["fam"] == 0], a["game"][a["fam"] == 0])
            elif lab == "inside BabyAI":
                n = pairs_count(a["y"][a["fam"] == 1], a["game"][a["fam"] == 1])
            elif lab == "across the families":
                n = pairs_count(a["y"], a["game"]) - pairs_count(a["y"], a["game"], a["fam"])
            else:
                n = pairs_count(a["y"], a["game"])
            parts[lab] = dict(pairs=n, H=h, S_M=m, delta=None if h is None or m is None else h - m)
        tot = parts["all between-game pairs"]["pairs"]
        print(f"  {ag} (units where H is defined, {len(a['y'])}):")
        for lab, v in parts.items():
            print(f"    {lab}: {pc(v['pairs'], tot)} of the pairs; AUROC H {f4(v['H'])}, S_M {f4(v['S_M'])}, "
                  f"difference {f4(v['delta'])}")
        p2[ag] = parts
    out["delta_by_pair_type"] = p2

    # ---- 3. censoring
    print(f"\n== 3. censoring of the search score ({TAG}) ==")
    rows = list(search.values())
    comp = [r for r in rows if r["complete"]]
    node = [r for r in rows if r["capped"] and r["cap_hit"] == "node"]
    tim = [r for r in rows if r["capped"] and r["cap_hit"] in ("time", "memory")]
    mx_c = max(r["counts"]["states_seen"] for r in comp)
    mn_n = min(r["counts"]["states_seen"] for r in node)
    mn_t = min(r["counts"]["states_seen"] for r in tim)
    print(f"  complete units {len(comp)}, largest R {mx_c}; node-capped units {len(node)}, fewest states seen {mn_n}; "
          f"time- or memory-capped units {len(tim)}, fewest states seen {mn_t}")
    print(f"  every node-capped unit saw more states than any complete unit has: {'yes' if mn_n > mx_c else 'no'}; "
          f"so the registered rule 1 ranks node-capped units correctly against complete ones, and loses only the "
          f"order among them")
    p3 = {}
    for c in CEILINGS:
        det = sum(not math.isnan(h_c(r, c)) for r in rows)
        ceil_ = sum((not r["complete"] and r["counts"]["states_seen"] >= c) or (r["complete"] and r["counts"]["states_seen"] >= c)
                    for r in rows)
        line = dict(determined=det, excluded=len(rows) - det, at_ceiling=ceil_, auroc={})
        txt = []
        for ag in AGENTS:
            a = defined(arrays(search, games, data[ag]), c)
            line["auroc"][ag] = {}
            for lab, mask in (("overall", np.ones(len(a["y"]), bool)), ("MiniGrid", a["fam"] == 0), ("BabyAI", a["fam"] == 1)):
                v = auroc_nested(a[c][mask], a["y"][mask], a["game"][mask])
                line["auroc"][ag][lab] = v
            txt.append(f"{ag} {f4(line['auroc'][ag]['overall'])} (MiniGrid {f4(line['auroc'][ag]['MiniGrid'])}, "
                       f"BabyAI {f4(line['auroc'][ag]['BabyAI'])})")
        print(f"  C {c:>9,}: determined {pc(det, len(rows))}, excluded {len(rows) - det}, at the ceiling "
              f"{pc(ceil_, len(rows))}; AUROC of H_C: " + "; ".join(txt))
        p3[c] = line
    out["censoring"] = {str(k): v for k, v in p3.items()}
    print("  the registered rule for comparison (node cap as R, time-capped units excluded): " + "; ".join(
        f"{ag} {f4(auroc_nested(*(lambda a: (a['H'], a['y'], a['game']))(defined(arrays(search, games, data[ag]), 'H'))))}"
        for ag in AGENTS))
    ci3 = {}
    for ag in AGENTS:
        a = defined(arrays(search, games, data[ag]), C_PROPOSED)
        iv, used = boot_ci(a, C_PROPOSED, a_.workers)
        ci3[ag] = dict(ci95=iv, resamples=used)
        print(f"  C {C_PROPOSED:,}, {ag}: AUROC {f4(p3[C_PROPOSED]['auroc'][ag]['overall'])} 95% [{iv[0]:.4f}, "
              f"{iv[1]:.4f}] ({used} resamples of games, seed {BOOT_SEED})")
    out["censoring_ci"] = ci3

    # ---- 4. agents
    print(f"\n== 4. agreement of the agents ({TAG}) ==")
    keys = sorted(set(data["N"]) & set(data["R"]) & set(data["I1"]))
    p4 = {}
    for x, y_ in (("N", "R"), ("N", "I1"), ("R", "I1")):
        same = sum(data[x][k]["y"] == data[y_][k]["y"] for k in keys)
        gsame = 0
        for g in games:
            ks = [k for k in keys if k[0] == g]
            gsame += sum(data[x][k]["y"] for k in ks) == sum(data[y_][k]["y"] for k in ks)
        p4[f"{x}-{y_}"] = dict(units_same=same, units=len(keys), games_same_count=gsame, games=len(games))
        print(f"  {x} and {y_}: same outcome on {pc(same, len(keys))} units; the same number of completed seeds on "
              f"{pc(gsame, len(games))} games")
    out["agents"] = p4

    # ---- 5. within-game variation
    print(f"\n== 5. within-game variation of the outcome ({TAG}) ==")
    p5 = {}
    for ag in AGENTS:
        mixed = 0
        for g in games:
            ys = [data[ag][k]["y"] for k in data[ag] if k[0] == g]
            mixed += 0 < sum(ys) < len(ys)
        a = arrays(search, games, data[ag])
        allp = int(a["y"].sum()) * int((~a["y"]).sum())
        bet = pairs_count(a["y"], a["game"])
        p5[ag] = dict(games_mixed=mixed, games=len(games), pairs_all=allp, pairs_within_game=allp - bet)
        print(f"  {ag}: games with both outcomes among their 10 seeds {pc(mixed, len(games))}; within-game pairs "
              f"{pc(allp - bet, allp)} of all positive-negative pairs")
    out["within_game"] = p5

    # ---- 6. power of smaller claims on the confirmatory structure
    print(f"\n== 6. smaller claims on the confirmatory structure ({TAG}) ==")
    sm, _holds = sdd.confirmatory_mechanics()
    smv = [float(v) for v in sm.values()]
    print(f"  {SIMS} simulated studies of {sdd.N_CLUSTERS} clusters of {LEVELS} units, seed {SIM_SEED}; a cluster takes "
          f"5 units of one development game and the mechanics score of one confirmatory game, each drawn with "
          f"replacement; H_C with C = {C_PROPOSED:,}; between-game pairs; power by the normal approximation of "
          f"scripts/sdd.py: P(lower end of the interval > 0.5)")
    p6 = {}
    for score, slab in ((C_PROPOSED, f"H_C, C = {C_PROPOSED:,}"), ("L", "L (time-capped units without a win excluded)")):
        for ag in AGENTS:
            a = defined(arrays(search, games, data[ag]), score)
            cl = [(a[score][a["game"] == g], a["y"][a["game"] == g]) for g in np.unique(a["game"])]
            plain, strat = simulate(cl, smv, a_.workers)
            res = {}
            for lab, v in (("all between-game pairs", plain), ("pairs of games with the same mechanics score", strat)):
                for alab, al in (("98.33%", ALPHA), ("95%", 0.05)):
                    res[f"{lab} {alab}"] = power_summary(v, al)
                r98, r95 = res[f"{lab} 98.33%"], res[f"{lab} 95%"]
                need98 = 0.5 + (ND.inv_cdf(1 - ALPHA / 2) + ND.inv_cdf(0.8)) * r98["se"]
                need95 = 0.5 + (ND.inv_cdf(0.975) + ND.inv_cdf(0.8)) * r98["se"]
                res[f"{lab} true AUROC for power 0.80"] = {"98.33%": need98, "95%": need95}
                print(f"  {slab}, {ag}, {lab}: mean AUROC {r98['mean']:.4f}, SE {r98['se']:.4f} ({r98['studies']} "
                      f"studies); power above 0.5 at 98.33% {r98['power_above_half']:.4f}, at 95% "
                      f"{r95['power_above_half']:.4f}; share of studies with the point at or above 0.70 "
                      f"{r98['share_point_at_least_070']:.4f}; both at 98.33% {r98['power_above_half_and_point_070']:.4f}; "
                      f"true AUROC needed for power 0.80: {need98:.4f} at 98.33%, {need95:.4f} at 95%")
            p6[f"{'H_C' if score == C_PROPOSED else 'L'} {ag}"] = res
    out["smaller_claims"] = p6

    # ---- 7. stratified reading on development data
    print(f"\n== 7. search score among games with the same development mechanics score ({TAG}) ==")
    p7 = {}
    for score, slab in ((C_PROPOSED, f"H_C (C = {C_PROPOSED:,})"), ("L", "L")):
        for ag in AGENTS:
            a = defined(arrays(search, games, data[ag]), score)
            v = auroc_nested(a[score], a["y"], a["game"], a["S_M"])
            n = pairs_count(a["y"], a["game"], a["S_M"])
            iv, used = boot_ci(a, score, a_.workers, strat=True)
            p7[f"{'H_C' if score == C_PROPOSED else 'L'} {ag}"] = dict(auroc=v, pairs=n, ci95=iv, resamples=used)
            print(f"  {slab}, {ag}: AUROC over {n} between-game pairs with equal S_M: {f4(v)} "
                  f"95% [{iv[0]:.4f}, {iv[1]:.4f}] ({used} resamples)")
    out["stratified_development"] = p7

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(label=TAG, ceiling_proposed=C_PROPOSED, **out), f, indent=1)
    print(f"\nwritten {os.path.relpath(OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
