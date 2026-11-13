"""
dev_reading.py -- EXPLORATORY.  The development reading of stage D (campaign dev-minigrid, kind devsearch;
docs/PREREG.md draft v0, Section 9.1).  Development data: it may not be used as evidence for the registered
claim, and every line it prints is labelled EXPLORATORY.  It decides nothing and changes no registered file.

Reads only committed files:
    runs/dev-minigrid/devsearch/*.json        stage D's 1,560 search rows (schema horizon.search.v2)
    D:\\Research\\arc3\\repo (read-only)        study 1's rows of MiniGrid/BabyAI in the macro condition and its
                                              truth table, through study 1's own parsers imported by
                                              scripts/oracle_v2.py, exactly as scripts/sdd.py reads them
Writes logs/dev_reading.log (the console, through the redirect below) and docs/design/dev_reading.json.

Units.  One unit per (game, seed), seeds 1000 to 1009, the layout produced by reset(seed); 156 games.  For
each evidence agent (N, R, I1), Y = that agent's level1_completed in study 1's macro row of the same game and
seed.  Games are the clusters.

Scores (larger = predicted easier), by the capped-game rule of docs/PREREG.md Section 7.4:
    H    -log10 R; R = states_seen of a complete search; a node-capped unit enters as the node cap (5,000,000),
         tied with every other node-capped unit; a time- or memory-capped unit is excluded.
    L    -L, the fewest actions to a win state; a complete search without a win, or a node-capped one without a
         win, is infinite (ranked last, tied); a time- or memory-capped unit is excluded unless a win was
         reached.
    b    -b, the mean distinct successors over the states expanded; time- or memory-capped units excluded.
    EH   -EH; "goal beyond horizon" and "not solvable" are infinite (ranked last, tied); a unit where EH was
         not computed for any reason is excluded.
    S_M  the mechanics score, the number of A1 to A5 holding in study 1's truth table (A3 as A3-macro), on
         every unit; S_M|H the same on the units where H is defined, the pairing of the registered contrast.
    area, actions, colours   study 1's nuisance features, from the agent's own row for that seed, each
         negated; and B, study 1's nuisance baseline: the in-sample logistic fit on the three
         (oracle_v2.fit_logistic, which reproduces study 1's logistic_fit_predict), refitted in every resample.

AUROC.  The registered statistic (docs/PREREG.md Section 7.2): Mann-Whitney with ties counted 1/2 over pairs of
a completed and an uncompleted unit from different games only.  The fast form here is checked against
sdd.auroc_between on every line.  Bootstrap as registered in Section 7.3: 10,000 resamples of games with
replacement, each game with all its units, seed 20261024 in 8 chunks with default_rng([seed, k]), the same
resamples for every score of a line; resamples with one class are skipped and counted; percentile intervals,
two-sided 95% and 98.33% (the registered Bonferroni level).  Delta = AUROC_H - AUROC of S_M|H, with its
interval; on the overall line its point value is the development Delta of scripts/sdd.py.

Lines: overall (156 games) and per family, MiniGrid and BabyAI (the split of study 1's
docs/GROUND_TRUTH_minigrid.md, "Count").  A table per finer family (study 1's
scripts/explore_v1_diagnosis.py, family(), copied below) gives point values only: those families hold 1 to 10
games, too few for an interval.

Capping (Section 7.4): units capped by node, time and memory, overall, per family and per game; games with every
unit capped; and per search quantity the shares the void rule of Section 7.4.3 reads (more than 25% capped by any
cap, or for EH not computed for any reason; more than 10% excluded under rule 2).

Images (docs/STATE.md, amendment u): the distinct KAGGLE_DOCKER_IMAGE values over every session entry of the rows.

Worker pool over bootstrap chunks.  Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\dev_reading.py --workers 4 > logs\\dev_reading.log
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import math
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import oracle_v2 as O  # noqa: E402 -- study-1 parsers, read-only
import sdd  # noqa: E402 -- the registered AUROC over between-game pairs, used as the check

DEV_ROWS = os.path.join(REPO, "runs", "dev-minigrid", "devsearch")
OUT = os.path.join(REPO, "docs", "design", "dev_reading.json")
AGENTS = ("N", "R", "I1")
NODE_CAP = 5_000_000
N_BOOT, SEED, CHUNKS = 10_000, 20261024, 8
LEVELS = {"95%": (2.5, 97.5), "98.33%": (100 * 0.05 / 6, 100 - 100 * 0.05 / 6)}
SEARCH = ("H", "L", "b", "EH")
NUIS = ("area", "actions", "colours")
SCORES = SEARCH + ("S_M", "S_M|H") + NUIS + ("B",)
INF = -1e18          # the score of an infinite L or EH: ranked last, tied with each other
TAG = "EXPLORATORY"


def family(game):
    """study 1, scripts/explore_v1_diagnosis.py, family(), copied unchanged."""
    if not (game.startswith("MiniGrid-") or game.startswith("BabyAI-")):
        return game
    prefix, rest = game.split("-", 1)
    rest = re.sub(r"-v\d+$", "", rest)
    toks = []
    for t in rest.split("-"):
        if re.match(r"^[A-Z]?\d", t) or t in ("Random", "Full"):
            break
        toks.append(t)
    name = "-".join(toks)
    name = re.sub(r"(S\d+)?(N\d+)?(R\d+)?(Random)?(Carrying)?(Debug)?\d*$", "", name) or name
    return f"{prefix}-{name}"


# ---------------------------------------------------------------- statistics
def _ranks_within(score, group):
    """Average ranks (1-based, ties averaged) of score inside each group."""
    order = np.lexsort((score, group))
    s, g = score[order], group[order]
    n = len(s)
    new_g = np.ones(n, bool)
    new_g[1:] = g[1:] != g[:-1]
    new_b = new_g.copy()
    new_b[1:] |= s[1:] != s[:-1]
    g_start = np.maximum.accumulate(np.where(new_g, np.arange(n), 0))
    b_id = np.cumsum(new_b) - 1
    b_start = np.flatnonzero(new_b)
    b_end = np.append(b_start[1:], n)
    avg = (b_start + b_end - 1) / 2.0
    r = np.empty(n)
    r[order] = avg[b_id] - g_start + 1
    return r


def auroc_between(score, y, group):
    """The registered AUROC: pairs of a positive and a negative from different groups; None if none."""
    score, y, group = np.asarray(score, float), np.asarray(y, bool), np.asarray(group)
    n1, n0 = int(y.sum()), int((~y).sum())
    if not n1 or not n0:
        return None
    zero = np.zeros(len(score), dtype=group.dtype)
    u_all = _ranks_within(score, zero)[y].sum() - n1 * (n1 + 1) / 2
    rw = _ranks_within(score, group)
    _, gi = np.unique(group, return_inverse=True)
    n1g = np.bincount(gi, weights=y.astype(float))
    ng = np.bincount(gi).astype(float)
    u_g = rw[y].sum() - (n1g * (n1g + 1) / 2).sum()
    pairs = n1 * n0 - (n1g * (ng - n1g)).sum()
    return None if pairs <= 0 else float((u_all - u_g) / pairs)


def baseline_pred(X, y):
    return np.nan_to_num(O.fit_logistic(X, y)(X), nan=0.5)


def line_values(units, games):
    """{score: AUROC} on the units of the listed games (a game listed twice is two draws with one label)."""
    parts = [units[g] for g in games]
    y = np.concatenate([p["y"] for p in parts])
    grp = np.concatenate([np.full(len(p["y"]), p["gid"]) for p in parts])
    out = {}
    for k in SCORES:
        if k == "B":
            X = np.concatenate([p["X"] for p in parts])
            s, keep = baseline_pred(X, y.astype(float)), np.ones(len(y), bool)
        elif k == "S_M|H":                     # the mechanics score on the units where H is defined
            s = np.concatenate([p["S_M"] for p in parts])
            keep = ~np.isnan(np.concatenate([p["H"] for p in parts]))
        else:
            s = np.concatenate([p[k] for p in parts])
            keep = ~np.isnan(s)
        out[k] = auroc_between(s[keep], y[keep], grp[keep])
    return out


def _boot_chunk(args):
    units, games, n, k = args
    rng = np.random.default_rng([SEED, k])
    vals, skipped = [], 0
    for _ in range(n):
        pick = [games[i] for i in rng.integers(0, len(games), len(games))]
        ys = np.concatenate([units[g]["y"] for g in pick])
        if ys.all() or not ys.any():
            skipped += 1
            continue
        vals.append(line_values(units, pick))
    return vals, skipped


def bootstrap(units, games, workers):
    per = [N_BOOT // CHUNKS + (1 if k < N_BOOT % CHUNKS else 0) for k in range(CHUNKS)]
    jobs = [(units, games, per[k], k) for k in range(CHUNKS)]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(_boot_chunk, jobs))
    vals = [v for r in res for v in r[0]]
    return vals, sum(r[1] for r in res)


def intervals(v):
    v = [x for x in v if x is not None]
    if not v:
        return {lev: (None, None) for lev in LEVELS}, 0
    return {lev: (float(np.percentile(v, lo)), float(np.percentile(v, hi))) for lev, (lo, hi) in LEVELS.items()}, len(v)


# ---------------------------------------------------------------- input
def read_search():
    rows = {}
    for path in sorted(glob.glob(os.path.join(DEV_ROWS, "*.json"))):
        with open(path, encoding="utf-8") as f:
            r = json.load(f)
        rows[(r["game"], int(r["level"]))] = r
    return rows


def search_scores(r):
    capped, hit = r["capped"], r["cap_hit"]
    tm = capped and hit in ("time", "memory")
    sol = r["counts"]["solution_length"]
    h = math.nan if tm else -math.log10(NODE_CAP if capped else r["counts"]["states_seen"])
    if sol is not None:
        lv = -float(sol)
    elif tm:
        lv = math.nan
    else:
        lv = INF
    b = math.nan if tm else -float(r["measures"]["branching"])
    st = r["measures"]["eh_status"]
    if st == "ok":
        eh = -float(r["measures"]["eh"])
    elif st in ("goal beyond horizon", "not solvable"):
        eh = INF
    else:
        eh = math.nan
    return dict(H=h, L=lv, b=b, EH=eh)


def f4(v):
    return "n/a" if v is None else f"{v:.4f}"


def ci(t):
    return "n/a" if t[0] is None else f"[{t[0]:.4f}, {t[1]:.4f}]"


def pc(a, b):
    return f"{a} of {b} ({100 * a / b:.1f}%)" if b else f"{a} of 0"


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-repo", default=r"D:\Research\arc3\repo")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    print(f"dev_reading -- {TAG}: development reading of stage D (campaign dev-minigrid); development data, "
          f"not evidence for the registered claim")

    search = read_search()
    games = sorted({g for g, _ in search})
    print(f"stage D rows: {len(search)} units, {len(games)} games, suites {sorted({r['suite'] for r in search.values()})}")

    # ---- 4. images (amendment u)
    img_sessions, img_rows, img_units = collections.Counter(), collections.Counter(), collections.defaultdict(set)
    missing = 0
    for key, r in search.items():
        seen = set()
        for s in r["sessions"]:
            im = (s.get("kaggle_env") or {}).get("KAGGLE_DOCKER_IMAGE")
            if im is None:
                missing += 1
                continue
            img_sessions[im] += 1
            seen.add(im)
            img_units[im].add(r["chunk_id"])
        for im in seen:
            img_rows[im] += 1
    n_sess = sum(len(r["sessions"]) for r in search.values())
    print(f"\n== images ({TAG}; amendment u) ==")
    print(f"session entries in the rows: {n_sess}; entries without KAGGLE_DOCKER_IMAGE: {missing}; "
          f"distinct images: {len(img_sessions)}")
    for im in sorted(img_sessions):
        print(f"  {im}: {img_sessions[im]} session entries, {img_rows[im]} rows, {len(img_units[im])} chunks")

    # ---- 3. capping
    print(f"\n== capping ({TAG}; docs/PREREG.md Section 7.4, read on development units) ==")
    caps = collections.Counter((r["cap_hit"] if r["capped"] else "none") for r in search.values())
    n = len(search)
    print(f"units: {n}; complete {pc(caps['none'], n)}; capped by node {pc(caps['node'], n)}; by time "
          f"{pc(caps['time'], n)}; by memory {pc(caps['memory'], n)}; by any cap {pc(n - caps['none'], n)}")
    sc = {k: search_scores(r) for k, r in search.items()}

    def void_lines(keys, label):
        m = len(keys)
        capped = sum(search[k]["capped"] for k in keys)
        out = {}
        for q in SEARCH:
            # rule 2: time- or memory-capped before the node cap; for L only those without a win
            excl = sum(search[k]["capped"] and search[k]["cap_hit"] in ("time", "memory")
                       and (q != "L" or search[k]["counts"]["solution_length"] is None) for k in keys)
            if q == "EH":
                cap_share = sum(search[k]["measures"]["eh_status"] != "ok" and
                                search[k]["measures"]["eh_status"] not in ("goal beyond horizon", "not solvable")
                                for k in keys)
                cap_word = "EH not computed for any reason"
            else:
                cap_share, cap_word = capped, "capped by any cap"
            over25, over10 = cap_share > 0.25 * m, excl > 0.10 * m
            out[q] = dict(units=m, capped_or_not_computed=cap_share, excluded=excl,
                          void=over25 or over10, over_25=over25, over_10=over10)
            print(f"  {label} {q}: {cap_word} {pc(cap_share, m)} (rule: void above 25%: "
                  f"{'over' if over25 else 'within'}); excluded under rule 2 {pc(excl, m)} (void above 10%: "
                  f"{'over' if over10 else 'within'}); would be void under Section 7.4.3: "
                  f"{'yes' if over25 or over10 else 'no'}")
        return out

    fam2 = {g: g.split("-", 1)[0] for g in games}
    voids = {"overall": void_lines(list(search), "overall")}
    for f in ("MiniGrid", "BabyAI"):
        ks = [k for k in search if fam2[k[0]] == f]
        c = collections.Counter((search[k]["cap_hit"] if search[k]["capped"] else "none") for k in ks)
        print(f"{f}: {len(ks)} units; capped by node {pc(c['node'], len(ks))}; by time {pc(c['time'], len(ks))}; "
              f"by memory {pc(c['memory'], len(ks))}")
        voids[f] = void_lines(ks, f)
    per_game = {}
    for g in games:
        ks = [k for k in search if k[0] == g]
        c = collections.Counter((search[k]["cap_hit"] if search[k]["capped"] else "none") for k in ks)
        per_game[g] = dict(units=len(ks), node=c["node"], time=c["time"], memory=c["memory"])
    all_capped = [g for g, v in per_game.items() if v["node"] + v["time"] + v["memory"] == v["units"]]
    some_capped = [g for g, v in per_game.items() if v["node"] + v["time"] + v["memory"] > 0]
    print(f"games with every unit capped: {pc(len(all_capped), len(games))}; with at least one unit capped: "
          f"{pc(len(some_capped), len(games))}")
    for f in ("MiniGrid", "BabyAI"):
        gf = [g for g in games if fam2[g] == f]
        print(f"  {f}: every unit capped {pc(sum(g in all_capped for g in gf), len(gf))}; at least one "
              f"{pc(sum(g in some_capped for g in gf), len(gf))}")
    print("per game (units capped by node / time / memory, of 10):")
    for g in games:
        v = per_game[g]
        tot = v["node"] + v["time"] + v["memory"]
        print(f"  {g}: node {v['node']}, time {v['time']}, memory {v['memory']}; capped {tot} of {v['units']}"
              + ("; every unit capped" if tot == v["units"] else ""))

    # ---- outcomes and units per agent
    O.load_old(a.old_repo)
    C = O.C
    truth = {"minigrid": C.parse_truth_minigrid(os.path.join(a.old_repo, "docs", "GROUND_TRUTH_minigrid.md")),
             "procgen": C.parse_truth_procgen(os.path.join(a.old_repo, "docs", "GROUND_TRUTH_procgen.md"))}
    conf = {s: set(C.confirmatory(s, truth[s])) for s in truth}
    oracle = O.oracle_vectors(truth, conf)[("minigrid", "macro")]
    rows, _ = O.read_rows(a.old_repo, conf)
    print(f"\n== units per agent ({TAG}) ==")
    data = {}
    for ag in AGENTS:
        recs = {}
        for r in rows:
            if r["suite"] != "minigrid" or r["condition"] != "macro" or r["agent"] != ag:
                continue
            key = (r["game"], int(r["seed"]))
            if key not in search:
                continue
            ad = r["adapter"]
            grid = ad.get("grid") or [0, 0]
            sm = sum(oracle[r["game"]][x] == C.HOLDS for x in C.ASSUMPTIONS)
            recs[key] = dict(y=bool(r["level1_completed"]), S_M=float(sm), area=-float(grid[0] * grid[1]),
                             actions=-float(len(ad.get("action_list") or [])), colours=-float(ad.get("n_colours") or 0),
                             **sc[key])
        units = {}
        for gid, g in enumerate(games):
            ks = sorted(k for k in recs if k[0] == g)
            if not ks:
                continue
            d = {k: np.array([recs[x][k] for x in ks], float) for k in SEARCH + ("S_M",) + NUIS}
            d["y"] = np.array([recs[x]["y"] for x in ks], bool)
            d["X"] = -np.column_stack([d[k] for k in NUIS])
            d["gid"] = gid
            units[g] = d
        nu = sum(len(u["y"]) for u in units.values())
        pos = sum(int(u["y"].sum()) for u in units.values())
        print(f"{ag}: {nu} units matched to a study-1 macro row ({len(search) - nu} without one), {len(units)} games; "
              f"completed {pc(pos, nu)}")
        data[ag] = units

    # ---- 2. AUROC lines
    print(f"\n== AUROC over between-game pairs, bootstrap of games ({TAG}) ==")
    print(f"{N_BOOT} resamples, seed {SEED}, {CHUNKS} chunks; intervals 95% and 98.33%; larger score = predicted "
          f"easier; H = -log10 R, L, b, EH the search quantities, S_M the mechanics score, area/actions/colours the "
          f"nuisance features, B the nuisance baseline (in-sample logistic on the three)")
    lines = {}
    for ag in AGENTS:
        for lab in ("overall", "MiniGrid", "BabyAI"):
            gs = [g for g in games if g in data[ag] and (lab == "overall" or fam2[g] == lab)]
            units = data[ag]
            point = line_values(units, gs)
            # check against the registered implementation of scripts/sdd.py
            mism = 0
            for k in SEARCH + ("S_M",):
                s = np.concatenate([units[g][k] for g in gs])
                y = np.concatenate([units[g]["y"] for g in gs])
                grp = np.concatenate([np.full(len(units[g]["y"]), units[g]["gid"]) for g in gs])
                keep = ~np.isnan(s)
                ref = sdd.auroc_between(s[keep], y[keep], grp[keep])
                mine = point[k]
                mism += not ((ref is None and mine is None) or (ref is not None and mine is not None and abs(ref - mine) < 1e-12))
            y = np.concatenate([units[g]["y"] for g in gs])
            vals, skipped = bootstrap(units, gs, a.workers)
            res = {}
            for k in SCORES:
                iv, used = intervals([v[k] for v in vals])
                nk = len(y) if k == "B" else int(sum((~np.isnan(units[g]["H" if k == "S_M|H" else k])).sum() for g in gs))
                res[k] = dict(auroc=point[k], ci=iv, resamples=used, units=nk)
            dv = [v["H"] - v["S_M|H"] for v in vals if v["H"] is not None and v["S_M|H"] is not None]
            div, dused = intervals(dv)
            dpt = None if point["H"] is None or point["S_M|H"] is None else point["H"] - point["S_M|H"]
            res["Delta"] = dict(auroc=dpt, ci=div, resamples=dused)
            lines[(ag, lab)] = dict(games=len(gs), units=len(y), completed=int(y.sum()), skipped=skipped,
                                    check_mismatches=mism, scores=res)
            print(f"\n{ag} {lab}: {len(gs)} games, {len(y)} units, completed {pc(int(y.sum()), len(y))}; resamples "
                  f"skipped (one class) {skipped}; check against sdd.auroc_between: {5 - mism} of 5 equal")
            for k in SCORES + ("Delta",):
                r = res[k]
                extra = f", units {r['units']}" if "units" in r else ""
                print(f"  {k:8s} AUROC {f4(r['auroc'])}  95% {ci(r['ci']['95%'])}  98.33% {ci(r['ci']['98.33%'])}"
                      f"{extra}")
            h = res["H"]
            if h["auroc"] is not None:
                lo95, lo98 = h["ci"]["95%"][0], h["ci"]["98.33%"][0]
                hi95 = h["ci"]["95%"][1]
                print(f"  reading of H: AUROC above 0.5 with the 95% interval above 0.5: "
                      f"{'yes' if lo95 is not None and lo95 > 0.5 else 'no'}; with the 98.33% interval above 0.5: "
                      f"{'yes' if lo98 is not None and lo98 > 0.5 else 'no'}; 95% interval below 0.5: "
                      f"{'yes' if hi95 is not None and hi95 < 0.5 else 'no'}; point at or above the registered "
                      f"floor 0.70: {'yes' if h['auroc'] >= 0.70 else 'no'}")

    # ---- finer families, point values only
    print(f"\n== finer families (study 1's family()), point values only ({TAG}) ==")
    fams = sorted({family(g) for g in games})
    fine = {}
    for fm in fams:
        gs = [g for g in games if family(g) == fm]
        ent = dict(games=len(gs))
        parts = []
        for ag in AGENTS:
            gg = [g for g in gs if g in data[ag]]
            y = np.concatenate([data[ag][g]["y"] for g in gg]) if gg else np.array([], bool)
            pv = line_values(data[ag], gg) if gg else {}
            ent[ag] = dict(units=len(y), completed=int(y.sum()), H=pv.get("H"), S_M=pv.get("S_M"), B=pv.get("B"))
            parts.append(f"{ag} completed {int(y.sum())}/{len(y)} H {f4(pv.get('H'))} S_M {f4(pv.get('S_M'))} "
                         f"B {f4(pv.get('B'))}")
        ks = [k for k in search if family(k[0]) == fm]
        ent["capped"] = sum(search[k]["capped"] for k in ks)
        fine[fm] = ent
        print(f"  {fm}: {len(gs)} games, capped {ent['capped']} of {len(ks)}; " + "; ".join(parts))

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(label=TAG, n_boot=N_BOOT, seed=SEED, node_cap=NODE_CAP,
                       images=dict(session_entries=n_sess, missing=missing, by_image=dict(img_sessions)),
                       caps=dict(caps), void_rule=voids, per_game_caps=per_game, games_all_capped=all_capped,
                       lines={f"{k[0]} {k[1]}": v for k, v in lines.items()}, finer_families=fine), f, indent=1)
    print(f"\nwritten {os.path.relpath(OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
