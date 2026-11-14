"""
analyze_horizon.py -- the registered analysis of HORIZON (docs/PREREG.md, Sections 7 and 11; docs/DESIGN.md,
Section 7), as adopted on 14 November 2026 (option E).  Frozen at the tag; the only permitted later change is a
crash fix, logged in docs/PREREG.md, Section 13.

Units: the 125 confirmatory (game, level) pairs, levels 0 to 4 of the 25 confirmatory games of scripts/suite.py
(the deterministic games minus the pilot drawn by scripts/draw_pilot.py minus the games the fit rule of
docs/PREREG.md, Section 4, removes; decided 14 November 2026: garbagecollector).  Games are the clusters.

Per unit (all larger = predicted easier):
    Y (per agent)   1 if the agent completed the level in at least 5 of its 10 seeds (Section 7.1).
    L_C             -L if a win state is among the first C states seen (seen_at_first_win <= C); "beyond C"
                    (ranked last, tied) if the search completed or saw at least C states without that; missing
                    (excluded) if it stopped by time or memory before C states without a win (Section 7.4).
    H_C             -log10 min(R, C); missing if the search stopped before C states without completing.
    b               minus the mean distinct successors over the states expanded; missing as H_C.
    S_M, A1..A5     from docs/truth/gvgai.json, per level (constant within a game).
    area, actions, colours   the nuisance features, each negated; B their in-sample logistic fit
                    (oracle_v2.fit_logistic, which reproduces study 1's logistic_fit_predict), refitted in every
                    resample on the units of the comparison.
AUROC: Mann-Whitney with ties 1/2 over the pairs of a completed and an uncompleted unit from different games
("all"), or from different games with the same S_M ("same"), the primary pairing (Section 7.2).
Bootstrap: 10,000 resamples of the games with replacement, each with all its levels and its S_M, seed 20261024
in 8 chunks (default_rng([20261024, k])) on a worker pool; two draws of one game share its label, so pairs
between them are within-game and excluded; a resample with no eligible pair for AUROC_L is skipped and counted
(Section 7.3).  Percentile intervals, two-sided 98.33% for AUROC_L and Delta, 95% for the other secondary lines.
Verdict per evidence agent (Section 7.5): "shown" if the lower end of AUROC_L's 98.33% interval is above 0.5 and
AUROC_L >= 0.70; else "not shown"; "void" first by Section 7.6.  Outcome by Section 10.
The ceiling C is the constant below; the script stops unless docs/PREREG.md, Section 6, states the same value.
It also stops on any campaign other than CONFIRMATORY_CAMPAIGN (the pilot, stage D and stage E are development
data and never enter it), and stops unless the annotated tag prereg-v1 exists in the repository and holds this
file as it is now (the analysis is frozen at the tag, docs/PREREG.md Section 11).

Inputs, read-only (docs/PREREG.md, Section 9: features only from search rows, the truth table and the features
file; outcomes only from agent rows):
    docs/truth/gvgai.json                 the truth table
    docs/truth/gvgai_features.json        {game: {level: {area, actions, colours}}}, written before the tag by the
                                          GVGAI adapter work (not yet built)
    runs/<campaign>/gvgaisearch/*.json    the confirmatory search rows of the kind gvgaisearch, suite "gvgai",
                                          level 0..4, schema horizon.search.v3 (counts and measures.branching)
    runs/<campaign>/gvgaiagent/*.json     the confirmatory agent rows of the kind gvgaiagent, schema
                                          horizon.agent.v2, which carries the level played
    docs/design/dev_reading.json          the development values of the effective-horizon bound, for the
                                          supplement (decision 6 of 14 November 2026)
Outputs: docs/tables/horizon.md, docs/tables/horizon.json, docs/tables/horizon_supplement.md (exploratory).
Synthetic tests: scripts/test_analyze_horizon.py.
Run, after the confirmatory campaign (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\analyze_horizon.py --campaign <name> --workers 4 > logs\\analyze_horizon.log
"""
from __future__ import annotations

import argparse
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

C = None             # the ceiling; entered when the author fixes it (docs/PREREG.md, Section 6)
# the void rule of L_C (docs/PREREG.md, Section 7.4, rule 5; decided 14 November 2026): its form and threshold are
# fixed by the author after the pilot search; until they are entered here, with synthetic tests, nothing is analysed
L_C_VOID_RULE = None
CONFIRMATORY_CAMPAIGN = "gvgai-confirmatory"
TAG = "prereg-v1"
SEARCH_KIND, AGENT_KIND = "gvgaisearch", "gvgaiagent"
AGENTS = ("N", "R", "I1")
REFERENCE = ("Rand",)
SEEDS = tuple(range(1000, 1010))
LEVELS = (0, 1, 2, 3, 4)
PRED = ("A1", "A2", "A3", "A4", "A5")
NUIS = ("area", "actions", "colours")
N_BOOT, SEED, CHUNKS = 10_000, 20261024, 8
CI = {"95%": (2.5, 97.5), "98.33%": (100 * 0.05 / 6, 100 - 100 * 0.05 / 6)}
FLOOR, BAND, EXCLUDED_MAX, MIN_GAMES = 0.70, (0.10, 0.90), 0.10, 20
INF = -1e18          # beyond C: ranked last, tied
PRIMARY = "L_same"
# line name: (score, pairing); "B" is refitted per resample; "L-B" is a difference on the same pairs
LINES = {"L_same": ("L", "same"), "L_all": ("L", "all"), "H_all": ("H", "all"), "H_same": ("H", "same"),
         "S_M_all": ("S_M", "all"), "S_M|H_all": ("S_M|H", "all"), "b_all": ("b", "all"),
         "B_all": ("B", "all"), "B_same": ("B", "same"), "L-B_all": ("L-B", "all"), "L-B_same": ("L-B", "same"),
         **{f"{f}_all": (f, "all") for f in NUIS}, **{f"{p}_all": (p, "all") for p in PRED}}
DELTA = "Delta"      # H_all minus S_M|H_all, the v0 contrast, a registered secondary estimate at 98.33%
TAG_SECONDARY = "secondary"


# ---------------------------------------------------------------- scores
def determined(row, c):
    return bool(row["complete"]) or row["counts"]["states_seen"] >= c


def l_c(row, c):
    s = row["counts"].get("seen_at_first_win")
    if s is not None and s <= c:
        return -float(row["counts"]["solution_length"])
    return INF if determined(row, c) else math.nan


def h_c(row, c):
    return -math.log10(min(row["counts"]["states_seen"], c)) if determined(row, c) else math.nan


def b_score(row, c):
    if not determined(row, c):
        return math.nan
    b = (row.get("measures") or {}).get("branching")
    return math.nan if b is None else -float(b)


def majority(outcomes):
    """Y from the 10 seeds' level1_completed: 1 if at least 5 completed."""
    if len(outcomes) != len(SEEDS):
        raise ValueError(f"expected {len(SEEDS)} seeds, got {len(outcomes)}")
    return int(sum(bool(x) for x in outcomes) >= 5)


# ---------------------------------------------------------------- the AUROC over eligible pairs
def _ranks_within(score, group):
    """Average ranks (1-based, ties averaged) of score inside each integer group."""
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


def _u_and_pairs(score, y, group):
    """Sum over groups of the Mann-Whitney U (positives above negatives, ties 1/2) and of the pair counts."""
    _, gi = np.unique(group, return_inverse=True)
    rw = _ranks_within(score, gi)
    n1g = np.bincount(gi, weights=y.astype(float))
    ng = np.bincount(gi).astype(float)
    u = rw[y].sum() - (n1g * (n1g + 1) / 2).sum()
    return float(u), float((n1g * (ng - n1g)).sum())


def auroc_pairs(score, y, game, stratum=None):
    """AUROC over pairs of a positive and a negative unit from different games and, if stratum is given, the
    same stratum.  Units with a nan score are dropped.  Returns (AUROC or None, number of pairs)."""
    score, y, game = np.asarray(score, float), np.asarray(y, bool), np.asarray(game)
    stratum = np.zeros(len(score), int) if stratum is None else np.asarray(stratum)
    keep = ~np.isnan(score)
    score, y, game, stratum = score[keep], y[keep], game[keep], stratum[keep]
    if not len(score):
        return None, 0
    _, si = np.unique(stratum, return_inverse=True)
    _, gi = np.unique(game, return_inverse=True)
    sg = si * (gi.max() + 1) + gi
    u_s, n_s = _u_and_pairs(score, y, si)
    u_g, n_g = _u_and_pairs(score, y, sg)
    n = n_s - n_g
    return (None, 0) if n <= 0 else ((u_s - u_g) / n, int(round(n)))


# ---------------------------------------------------------------- one sample of games
def _baseline(X, y):
    import oracle_v2 as O  # noqa: PLC0415 -- the nuisance baseline of study 1, as dev_reading.py uses it
    if y.all() or not y.any():
        return np.full(len(y), 0.5)
    return np.nan_to_num(O.fit_logistic(X, y.astype(float))(X), nan=0.5)


def line_values(blocks, picks):
    """{line: AUROC or None} for one agent on the games picked (a game picked twice is two draws, one label)."""
    parts = [blocks[g] for g in picks]
    cat = {k: np.concatenate([p[k] for p in parts]) for k in parts[0] if k != "X"}
    X = np.concatenate([p["X"] for p in parts])
    y, game, sm = cat["y"].astype(bool), cat["game"], cat["S_M"]
    out = {}
    lkeep = ~np.isnan(cat["L"])
    bpred = np.full(len(y), np.nan)
    if lkeep.any():
        bpred[lkeep] = _baseline(X[lkeep], y[lkeep])
    ball = _baseline(X, y)
    for name, (score, pairing) in LINES.items():
        strat = sm if pairing == "same" else None
        if score == "B":
            v, _ = auroc_pairs(bpred if pairing == "same" else ball, y, game, strat)
        elif score == "L-B":
            a, _ = auroc_pairs(cat["L"], y, game, strat)
            b, _ = auroc_pairs(bpred, y, game, strat)
            v = None if a is None or b is None else a - b
        elif score == "S_M|H":
            v, _ = auroc_pairs(np.where(np.isnan(cat["H"]), np.nan, sm), y, game, strat)
        else:
            v, _ = auroc_pairs(cat[score], y, game, strat)
        out[name] = v
    h, m = out["H_all"], out["S_M|H_all"]
    out[DELTA] = None if h is None or m is None else h - m
    return out


def _boot_chunk(args):
    blocks, games, n, k = args
    rng = np.random.default_rng([SEED, k])
    vals, skipped = [], 0
    for _ in range(n):
        pick = [games[i] for i in rng.integers(0, len(games), len(games))]
        v = line_values(blocks, pick)
        if v[PRIMARY] is None:
            skipped += 1
            continue
        vals.append(v)
    return vals, skipped


def bootstrap(blocks, games, workers=1, n_boot=N_BOOT, chunks=CHUNKS):
    per = [n_boot // chunks + (1 if k < n_boot % chunks else 0) for k in range(chunks)]
    jobs = [(blocks, games, per[k], k) for k in range(chunks)]
    if workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            res = list(ex.map(_boot_chunk, jobs))
    else:
        res = [_boot_chunk(j) for j in jobs]
    return [v for r in res for v in r[0]], sum(r[1] for r in res)


def intervals(vals, name):
    v = [x[name] for x in vals if x[name] is not None]
    if not v:
        return {lev: None for lev in CI}, 0
    return {lev: [float(np.percentile(v, lo)), float(np.percentile(v, hi))] for lev, (lo, hi) in CI.items()}, len(v)


# ---------------------------------------------------------------- the units of one agent
def build_blocks(units, y_of):
    """{game: arrays} for one agent; units {(game, level): dict of scores}; y_of {(game, level): 0/1}."""
    games = sorted({g for g, _ in units})
    gid = {g: i for i, g in enumerate(games)}
    blocks = {}
    for g in games:
        keys = sorted(k for k in units if k[0] == g)
        u = [units[k] for k in keys]
        blocks[g] = dict(y=np.array([y_of[k] for k in keys], int), game=np.full(len(keys), gid[g]),
                         L=np.array([x["L"] for x in u], float), H=np.array([x["H"] for x in u], float),
                         b=np.array([x["b"] for x in u], float), S_M=np.array([x["S_M"] for x in u], float),
                         X=np.array([[x[f] for f in NUIS] for x in u], float),
                         **{f: np.array([-x[f] for x in u], float) for f in NUIS},
                         **{p: np.array([float(x[p]) for x in u]) for p in PRED})
    return blocks, games


def void_reasons(units, y_of, c_counts, blocks, games):
    """The void rules of Section 7.6 for one agent; [] if not void."""
    reasons = []
    ys = [y_of[k] for k in units]
    share = sum(ys) / len(ys)
    if not BAND[0] <= share <= BAND[1]:
        reasons.append(f"completed share {share:.4f} outside [{BAND[0]:.2f}, {BAND[1]:.2f}]")
    if c_counts["L"]["excluded"] / len(units) > EXCLUDED_MAX:
        reasons.append(f"L_C void: {c_counts['L']['excluded']} of {len(units)} levels excluded, over 10%")
    sm = [units[k]["S_M"] for k in units]
    common = [v for v in sorted(set(sm)) if sm.count(v) / len(sm) >= 0.10]
    if len(common) < 2:
        reasons.append("fewer than two values of S_M each held by at least 10% of the levels")
    if line_values(blocks, games)[PRIMARY] is None:
        reasons.append("no pair of a completed and an uncompleted level from different games with the same S_M")
    return reasons


def censor_counts(rows, c):
    out = {}
    for q, fn in (("L", l_c), ("H", h_c), ("b", b_score)):
        vals = {k: fn(r, c) for k, r in rows.items()}
        out[q] = dict(units=len(vals), complete=sum(bool(r["complete"]) for r in rows.values()),
                      excluded=sum(math.isnan(v) for v in vals.values()))
    out["L"]["beyond_C"] = sum(v == INF for v in out_vals(rows, c, l_c))
    out["H"]["at_ceiling"] = sum((not r["complete"]) and r["counts"]["states_seen"] >= c for r in rows.values())
    return out


def out_vals(rows, c, fn):
    return [fn(r, c) for r in rows.values()]


def verdict(point, ci98):
    return "shown" if point is not None and ci98 is not None and ci98[0] > 0.5 and point >= FLOOR else "not shown"


def outcome(verdicts, n_games):
    """Section 10: verdicts {agent: "shown" | "not shown" | "void"}."""
    voids = sum(v == "void" for v in verdicts.values())
    if n_games < MIN_GAMES or verdicts["N"] == "void" or voids >= 2:
        return "Void", "this repository and a preprint on Zenodo, reported as void"
    if verdicts["N"] == "shown" and any(verdicts[a] == "shown" for a in ("R", "I1")) and voids == 0:
        venue = "JAIR" if all(verdicts[a] == "shown" for a in AGENTS) else "IEEE Transactions on Games"
        return "Support", venue
    return "Refute", "this repository and a preprint on Zenodo"


def agreement(y_by_agent, a, b):
    keys = sorted(y_by_agent[a])
    same = sum(y_by_agent[a][k] == y_by_agent[b][k] for k in keys)
    return dict(same=same, units=len(keys))


# ---------------------------------------------------------------- the whole analysis on in-memory tables
def analyze(rows, truth, features, outcomes, c, workers=1, n_boot=N_BOOT):
    """rows {(game, level): search row}; truth {(game, level): {A1..A5: bool}}; features {(game, level):
    {area, actions, colours}}; outcomes {(agent, game, level, seed): bool}.  Returns the result dict."""
    keys = sorted(rows)
    if set(truth) < set(keys) or set(features) < set(keys):
        raise ValueError("every search unit needs a truth-table entry and features")
    units = {}
    for k in keys:
        t = truth[k]
        units[k] = dict(L=l_c(rows[k], c), H=h_c(rows[k], c), b=b_score(rows[k], c),
                        S_M=sum(bool(t[p]) for p in PRED), **{p: bool(t[p]) for p in PRED},
                        **{f: float(features[k][f]) for f in NUIS})
    counts = censor_counts(rows, c)
    n_games = len({g for g, _ in keys})
    res = dict(C=c, units=len(keys), games=n_games, n_boot=n_boot, seed=SEED, counts=counts, agents={})
    y_all = {}
    for agent in AGENTS + REFERENCE:
        y_of = {k: majority([outcomes[(agent, k[0], k[1], s)] for s in SEEDS]) for k in keys}
        y_all[agent] = y_of
        blocks, games = build_blocks(units, y_of)
        point = line_values(blocks, games)
        vals, skipped = bootstrap(blocks, games, workers, n_boot)
        lines = {}
        for name in list(LINES) + [DELTA]:
            ci, used = intervals(vals, name)
            lines[name] = dict(point=point[name], ci=ci, resamples=used)
        npairs = auroc_pairs(np.concatenate([blocks[g]["L"] for g in games]),
                             np.concatenate([blocks[g]["y"] for g in games]).astype(bool),
                             np.concatenate([blocks[g]["game"] for g in games]),
                             np.concatenate([blocks[g]["S_M"] for g in games]))[1]
        allpairs = auroc_pairs(np.concatenate([blocks[g]["L"] for g in games]),
                               np.concatenate([blocks[g]["y"] for g in games]).astype(bool),
                               np.concatenate([blocks[g]["game"] for g in games]))[1]
        l0 = {k: u for k, u in units.items() if k[1] == 0}
        b0, g0 = build_blocks(l0, y_of)
        p0 = line_values(b0, g0)
        v0, s0 = bootstrap(b0, g0, workers, n_boot)
        level0 = {name: dict(point=p0[name], ci=intervals(v0, name)[0]) for name in (PRIMARY, DELTA)}
        reasons = void_reasons(units, y_of, counts, blocks, games) if agent in AGENTS else []
        ver = ("void" if reasons else verdict(point[PRIMARY], lines[PRIMARY]["ci"]["98.33%"])) \
            if agent in AGENTS else None
        res["agents"][agent] = dict(completed=sum(y_of.values()), lines=lines, skipped=skipped,
                                    pairs_same=npairs, pairs_all=allpairs, level0=level0, level0_skipped=s0,
                                    void=reasons, verdict=ver)
    res["agreement"] = {"N-R": agreement(y_all, "N", "R"), "N-I1": agreement(y_all, "N", "I1")}
    res["outcome"], res["venue"] = outcome({a: res["agents"][a]["verdict"] for a in AGENTS}, n_games)
    return res


# ---------------------------------------------------------------- report
def f4(v):
    return "none" if v is None else f"{v:.4f}"


def ci_text(ci):
    return "none" if ci is None else f"[{ci[0]:.4f}, {ci[1]:.4f}]"


def report(res):
    out = [f"# HORIZON: the registered analysis", "",
           f"Ceiling C = {res['C']:,}; {res['units']} confirmatory levels of {res['games']} games; "
           f"{res['n_boot']:,} resamples of games, seed {res['seed']}.", "",
           f"**Outcome: {res['outcome']}** ({res['venue']}).", "",
           "## Registered: AUROC_L over between-game pairs with the same S_M (Sections 7.2 to 7.6)", "",
           "| agent | completed | pairs | AUROC_L | 98.33% interval | resamples skipped | verdict |",
           "|---|---|---|---|---|---|---|"]
    for a in AGENTS:
        r = res["agents"][a]
        ln = r["lines"][PRIMARY]
        out.append(f"| {a} | {r['completed']} of {res['units']} | {r['pairs_same']} of {r['pairs_all']} between-game "
                   f"| {f4(ln['point'])} | {ci_text(ln['ci']['98.33%'])} | {r['skipped']} | {r['verdict']} |")
    for a in AGENTS:
        if res["agents"][a]["void"]:
            out.append(f"\n{a} void: " + "; ".join(res["agents"][a]["void"]))
    c = res["counts"]
    out += ["", "## Censoring at C (Section 7.4)", "",
            f"L_C: complete {c['L']['complete']}, beyond C {c['L']['beyond_C']}, excluded {c['L']['excluded']} of "
            f"{c['L']['units']}. H_C: at the ceiling {c['H']['at_ceiling']}, excluded {c['H']['excluded']}. "
            f"b: excluded {c['b']['excluded']}.", "",
            "## Secondary, registered, outside the outcome table (Section 7.7)", "",
            "Each line is secondary. Delta keeps the 98.33% level; the others are unadjusted 95% intervals.", "",
            "| agent | line | value | interval |", "|---|---|---|---|"]
    for a in AGENTS + REFERENCE:
        for name in [DELTA] + [n for n in LINES if n != PRIMARY]:
            ln = res["agents"][a]["lines"][name]
            lev = "98.33%" if name == DELTA else "95%"
            out.append(f"| {a} | {name} | {f4(ln['point'])} | {lev} {ci_text(ln['ci'][lev])} |")
        if a in REFERENCE:
            ln = res["agents"][a]["lines"][PRIMARY]
            out.append(f"| {a} | {PRIMARY} (reference, no verdict) | {f4(ln['point'])} | 95% {ci_text(ln['ci']['95%'])} |")
        l0 = res["agents"][a]["level0"]
        for name in (PRIMARY, DELTA):
            out.append(f"| {a} | level 0 alone: {name} | {f4(l0[name]['point'])} | 95% {ci_text(l0[name]['ci']['95%'])} |")
    ag = res["agreement"]
    out += ["", f"Agreement of the outcomes (secondary): N and R the same on {ag['N-R']['same']} of "
                f"{ag['N-R']['units']} levels; N and I1 on {ag['N-I1']['same']} of {ag['N-I1']['units']}."]
    return "\n".join(out) + "\n"


def supplement(dev):
    out = ["# HORIZON: supplement (EXPLORATORY)", "",
           "Everything in this file is exploratory and enters no registered verdict.", "",
           "## The effective-horizon bound on the development data (decision 6 of 14 November 2026)", "",
           "*Exploratory.* Dropped from every registered verdict. Its AUROC for first-level completion on stage D's "
           "development units, where it could be computed, from docs/design/dev_reading.json:", ""]
    for a in AGENTS:
        e = dev["lines"][f"{a} overall"]["scores"]["EH"]
        out.append(f"- {a}: AUROC {e['auroc']:.4f}, 95% [{e['ci']['95%'][0]:.4f}, {e['ci']['95%'][1]:.4f}], "
                   f"{e['units']} units")
    v = dev["void_rule"]["overall"]["EH"]
    out += ["", f"*Exploratory.* Not computed on {v['capped_or_not_computed']} of {v['units']} development units "
                f"({100 * v['capped_or_not_computed'] / v['units']:.1f}%)."]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- inputs
def prereg_c(path=os.path.join(REPO, "docs", "PREREG.md")):
    """The ceiling stated in docs/PREREG.md, Section 6, or None while it is open."""
    with open(path, encoding="utf-8") as f:
        m = re.search(r"^- \*\*C = ([0-9,]+)\*\*", f.read(), re.M)
    return None if m is None else int(m.group(1).replace(",", ""))


def confirmatory_games():
    import suite  # noqa: PLC0415 -- the registered game lists, with the pilot draw and the fit rule
    with open(os.path.join(REPO, "docs", "truth", "gvgai.json"), encoding="utf-8") as f:
        t = json.load(f)["games"]
    games = sorted(g for g, v in t.items() if v["deterministic"])
    if games != suite.deterministic():
        raise SystemExit("the deterministic games of docs/truth/gvgai.json differ from docs/design/vgdl_scan.json")
    return suite.confirmatory(), t


def load(campaign):
    sys.path.insert(0, os.path.join(HERE, "automation"))
    import schema  # noqa: PLC0415 -- the row schemas of the loop
    conf, t = confirmatory_games()
    truth = {(g, lv): {p: t[g]["levels"][str(lv)][p]["verdict"] == "holds" for p in PRED}
             for g in conf for lv in LEVELS}
    with open(os.path.join(REPO, "docs", "truth", "gvgai_features.json"), encoding="utf-8") as f:
        fe = json.load(f)
    features = {(g, lv): fe[g][str(lv)] for g in conf for lv in LEVELS}
    rows = {}
    for p in sorted(glob.glob(os.path.join(REPO, "runs", campaign, SEARCH_KIND, "*.json"))):
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        e = schema.validate_search_row(r)
        if e:
            raise ValueError(f"{p}: {e}")
        if r["game"] in conf:
            rows[(r["game"], int(r["level"]))] = r
    outcomes = {}
    for p in sorted(glob.glob(os.path.join(REPO, "runs", campaign, AGENT_KIND, "*.json"))):
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        e = schema.validate_agent_row(r)
        if e or r.get("schema") != schema.AGENT_SCHEMA_V2:
            raise ValueError(f"{p}: not a horizon.agent.v2 row (an agent row of the confirmatory campaign must "
                             f"carry its level): {e}")
        if r["game"] in conf:
            outcomes[(r["agent"], r["game"], int(r["level"]), int(r["seed"]))] = bool(r["outcome"]["level1_completed"])
    missing = [k for k in truth if k not in rows]
    if missing:
        raise ValueError(f"{len(missing)} confirmatory levels have no search row, e.g. {missing[:3]}")
    return rows, truth, features, outcomes


def tag_refusal(repo=REPO, tag=TAG, script=os.path.abspath(__file__)):
    """None if the annotated tag exists and holds this script byte for byte, else the reason to refuse."""
    import subprocess  # noqa: PLC0415

    def git(*args):
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    r = git("cat-file", "-t", f"refs/tags/{tag}")
    if r.returncode or r.stdout.strip() != "tag":
        return f"the annotated tag {tag} does not exist: the registration comes first (docs/PREREG.md, Section 0)"
    rel = os.path.relpath(script, repo).replace(os.sep, "/")
    at_tag = git("rev-parse", f"{tag}:{rel}")
    if at_tag.returncode:
        return f"{rel} is not in the tag {tag}"
    now = git("hash-object", script).stdout.strip()       # with the repository's line-ending filters
    if now != at_tag.stdout.strip():
        return f"{rel} differs from its version at the tag {tag} (blob {now} against {at_tag.stdout.strip()})"
    return None


def main(argv=None, repo=REPO):
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    if a.campaign != CONFIRMATORY_CAMPAIGN:
        raise SystemExit(f"campaign {a.campaign!r} is not the confirmatory campaign {CONFIRMATORY_CAMPAIGN!r}; "
                         "development and pilot data never enter this analysis (docs/PREREG.md, Sections 4 and 9)")
    why = tag_refusal(repo)
    if why:
        raise SystemExit(why)
    stated = prereg_c()
    if C is None or stated is None:
        raise SystemExit("the ceiling C is not fixed yet (docs/PREREG.md, Section 6); nothing is analysed")
    if stated != C:
        raise SystemExit(f"C in this script ({C}) differs from docs/PREREG.md, Section 6 ({stated})")
    if L_C_VOID_RULE is None:
        raise SystemExit("the threshold of the void rule of L_C is not fixed yet (docs/PREREG.md, Section 7.4, rule 5); "
                         "nothing is analysed")
    rows, truth, features, outcomes = load(a.campaign)
    res = analyze(rows, truth, features, outcomes, C, workers=a.workers)
    os.makedirs(os.path.join(REPO, "docs", "tables"), exist_ok=True)
    text = report(res)
    with open(os.path.join(REPO, "docs", "tables", "horizon.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    with open(os.path.join(REPO, "docs", "tables", "horizon.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, default=float)
    with open(os.path.join(REPO, "docs", "design", "dev_reading.json"), encoding="utf-8") as f:
        dev = json.load(f)
    with open(os.path.join(REPO, "docs", "tables", "horizon_supplement.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(supplement(dev))
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
