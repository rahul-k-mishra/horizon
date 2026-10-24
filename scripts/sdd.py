"""
sdd.py -- the smallest detectable difference of HORIZON's registered contrast (docs/DESIGN.md, Section 7.1;
docs/PREREG.md, Section 7.8).  Run before the tag, on development data only.

The contrast is Delta = AUROC_H - AUROC_M, where AUROC_H is the AUROC of the search score -log10 R for
first-level completion and AUROC_M that of the mechanics score S_M (the number of A1 to A5 holding).
Its registered interval is a two-sided 98.33% interval (Bonferroni over the three evidence agents) from
a bootstrap of 26 game clusters.  This script estimates how large a true Delta must be for that interval
to exclude zero with probability 0.80:
    1. Development units: study 1's confirmatory MiniGrid/BabyAI games in the macro condition (the condition
       study 1 tested), one unit per (game, seed), seeds 1000 to 1009.  Per unit: R from the stage-D search
       row (runs/dev-minigrid/search/, written by the loop; the capped-game rule of PREREG Section 7.4
       applies: node-capped R = the node cap, time- or memory-capped units dropped); S_M from study 1's
       truth table; Y = the row's level1_completed for that agent and seed.  Study 1's rows and truth tables
       are read, never written, through study 1's own parsers (as scripts/oracle_v2.py does).
    2. For each evidence agent (N, R, I1): SIMS simulated studies, each drawing 26 games with replacement,
       each game with all its units, and computing Delta on them (draws with one outcome class are
       skipped and counted).  SE = the standard deviation of Delta over the simulated studies.
    3. MDD = (z(1 - alpha/2) + z(0.80)) x SE with alpha = 0.05 / 3: the true difference at which a normal
       estimate with that SE clears zero at the registered level with probability 0.80.
    4. The registered number is the largest MDD over the three agents, rounded up to two decimals.
Differences from the confirmatory design, stated rather than corrected: a development cluster holds 10
seed layouts of one environment, a confirmatory cluster 5 levels of one game; a development outcome is one
seed's completion, a confirmatory outcome the majority of 10 seeds; and S_M takes only two values on
MiniGrid/BabyAI under macro (docs/oracle/READING.md, Section 5).
Worker pool over chunks of simulated studies.  Console to logs/sdd.log, numbers to docs/design/sdd.json.
Run (working directory D:\\Research\\horizon\\repo), once stage D's rows are committed:
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\sdd.py --workers 4 > logs\\sdd.log
"""
from __future__ import annotations

import argparse
import glob
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
N_CLUSTERS, SIMS, SEED, ALPHA, POWER = 26, 4000, 20261026, 0.05 / 3, 0.80
AGENTS = ("N", "R", "I1")
DEV_ROWS = os.path.join(REPO, "runs", "dev-minigrid", "search")


def auroc(score, y):
    """Mann-Whitney AUROC with ties counted 1/2; None if one class is empty."""
    score, y = np.asarray(score, float), np.asarray(y, bool)
    pos, neg = score[y], score[~y]
    if not len(pos) or not len(neg):
        return None
    order = np.argsort(np.concatenate([pos, neg]), kind="mergesort")
    allv = np.concatenate([pos, neg])[order]
    ranks = np.empty(len(allv))
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        ranks[i:j + 1] = (i + j) / 2 + 1
        i = j + 1
    r = np.empty(len(allv))
    r[order] = ranks
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def delta(clusters, picks):
    h = np.concatenate([clusters[i][0] for i in picks])
    m = np.concatenate([clusters[i][1] for i in picks])
    y = np.concatenate([clusters[i][2] for i in picks])
    a, b = auroc(h, y), auroc(m, y)
    return None if a is None or b is None else a - b


def _chunk(args):
    clusters, n, sims, seed, k = args
    rng = np.random.default_rng([seed, k])
    out = []
    for _ in range(sims):
        out.append(delta(clusters, rng.integers(0, len(clusters), n)))
    return out


def simulate(clusters, n=N_CLUSTERS, sims=SIMS, seed=SEED, workers=1, chunks=8):
    """Delta over `sims` simulated studies of `n` clusters drawn with replacement; returns (deltas, skipped)."""
    per = [sims // chunks + (1 if k < sims % chunks else 0) for k in range(chunks)]
    jobs = [(clusters, n, per[k], seed, k) for k in range(chunks)]
    if workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            res = list(ex.map(_chunk, jobs))
    else:
        res = [_chunk(j) for j in jobs]
    flat = [d for r in res for d in r]
    good = [d for d in flat if d is not None]
    return good, len(flat) - len(good)


def mdd_from(deltas, alpha=ALPHA, power=POWER):
    nd = statistics.NormalDist()
    se = statistics.stdev(deltas)
    return se, (nd.inv_cdf(1 - alpha / 2) + nd.inv_cdf(power)) * se


def load(old, node_cap):
    """{agent: [(h, m, y) arrays per game]} for the development units, and a summary."""
    import oracle_v2 as O  # noqa: E402 -- study-1 parsers, read-only, as in Phase 1
    O.load_old(old)
    C = O.C
    truth = {"minigrid": C.parse_truth_minigrid(os.path.join(old, "docs", "GROUND_TRUTH_minigrid.md")),
             "procgen": C.parse_truth_procgen(os.path.join(old, "docs", "GROUND_TRUTH_procgen.md"))}
    conf = {s: set(C.confirmatory(s, truth[s])) for s in truth}
    oracle = O.oracle_vectors(truth, conf)[("minigrid", "macro")]
    rows, _ = O.read_rows(old, conf)
    search, dropped = {}, 0
    for path in sorted(glob.glob(os.path.join(DEV_ROWS, "*.json"))):
        with open(path, encoding="utf-8") as f:
            r = json.load(f)
        if r.get("suite") != "minigrid":
            continue
        if r["capped"] and r["cap_hit"] in ("time", "memory"):
            dropped += 1
            continue
        R = node_cap if r["capped"] else r["counts"]["states_seen"]
        search[(r["game"], int(r["level"]))] = -math.log10(R)
    out, n_units = {}, {}
    for a in AGENTS:
        per_game = {}
        for r in rows:
            if r["suite"] != "minigrid" or r["condition"] != "macro" or r["agent"] != a:
                continue
            key = (r["game"], int(r["seed"]))
            if key not in search:
                continue
            sm = sum(oracle[r["game"]][x] == C.HOLDS for x in C.ASSUMPTIONS)
            per_game.setdefault(r["game"], []).append((search[key], sm, bool(r["level1_completed"])))
        out[a] = [tuple(np.array(c) for c in zip(*units)) for _, units in sorted(per_game.items())]
        n_units[a] = sum(len(u) for u in per_game.values())
    return out, dict(search_rows=len(search), dropped_time_memory=dropped, units=n_units)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-repo", default=r"D:\Research\arc3\repo")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--node-cap", type=int, default=5_000_000)
    a = ap.parse_args(argv)
    print(f"sdd: smallest detectable difference, {N_CLUSTERS} clusters, {SIMS} simulated studies, seed {SEED}, "
          f"alpha {ALPHA:.6f} two-sided, power {POWER}")
    if not glob.glob(os.path.join(DEV_ROWS, "*.json")):
        print(f"waiting: no development search rows under {os.path.relpath(DEV_ROWS, REPO)}; stage D has not run")
        return 2
    data, info = load(a.old_repo, a.node_cap)
    print(f"development: {info['search_rows']} search units used, {info['dropped_time_memory']} dropped (time or memory cap); "
          f"units per agent {info['units']}")
    res = {}
    for ag in AGENTS:
        cl = data[ag]
        full = delta(cl, range(len(cl)))
        deltas, skipped = simulate(cl, workers=a.workers)
        se, mdd = mdd_from(deltas)
        res[ag] = dict(games=len(cl), delta_development=full, se=se, mdd=mdd, skipped=skipped, used=len(deltas))
        print(f"{ag}: {len(cl)} games; development Delta (EXPLORATORY) {full if full is None else round(full, 4)}; "
              f"simulated studies used {len(deltas)}, skipped {skipped}; SE {se:.4f}; MDD {mdd:.4f}")
    reg = math.ceil(max(r["mdd"] for r in res.values()) * 100) / 100
    print(f"registered smallest detectable difference (largest over N, R, I1, rounded up): {reg:.2f}")
    out = os.path.join(REPO, "docs", "design", "sdd.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(n_clusters=N_CLUSTERS, sims=SIMS, seed=SEED, alpha=ALPHA, power=POWER, agents=res,
                       registered_mdd=reg, info=info), f, indent=1)
    print(f"written {os.path.relpath(out, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
