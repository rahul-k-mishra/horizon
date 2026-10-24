"""
oracle_v2.py -- EXPLORATORY.  The oracle test of HORIZON Phase 1 (docs/PROJECT_BRIEF.md, Section 3).

Study 1 (D:\\Research\\arc3\\repo) tested whether its census score S predicts first-level completion
(test V2, its docs/PREREG.md v1 Section 10, scripts/analyze_v2.py).  Its census failed V1, so V2 could
not say whether mechanics predict success.  This script recomputes study 1's V2 on study 1's own rows,
exactly, with one change: the mechanics vector of each game is the truth table's A1 to A5 (exact
mechanics, "the oracle") in place of the seed-majority census.  A3 is the A3-raw truth under raw and
the A3-macro truth under macro, as in study 1 (analyze_common.truth_for).

Inputs, all read-only, from the study-1 repository (--old-repo):
    scripts/analyze_common.py, scripts/analyze_v2.py   imported by path, unchanged; bytecode writing is
                                                       switched off so nothing is written there
    docs/GROUND_TRUTH_minigrid.md, docs/GROUND_TRUTH_procgen.md   through analyze_common's parsers
    runs/suites/minigrid/raw/*/*.json, runs/suites/minigrid/macro/*/*.json,
    runs/suites/procgen/center_off/*/*.json            the rows of agents R (hash_state), N (nav), I1 (i1)
    docs/tables/v2.json                                the study-1 census values, shown side by side

For every line of study-1 V2 on those suites and conditions (suite, condition, subset, agent; the
subsets and exclusion lists of analyze_v2.v2_rows: primary, primary D9b included, all games; on
Procgen all and in_range), it reports:
    census   the study-1 values recomputed by analyze_v2.game_table and v2_stats, and the values of
             docs/tables/v2.json beside them (the reproduction check)
    oracle   the same functions with the truth-table vector: AUROC of S with its bootstrap interval,
             balanced accuracy of the conjunctive prediction P (A2, A3, A4, A5 all hold), the nuisance
             baseline AUROC_B, the void band and the verdict that the study-1 rule would print
    search   the first search features available without a simulator, each as a one-feature score
             (larger value = larger search = predicted harder, so the score is the negated value):
                 grid area, action count, colour count   per-game means over the agent's own rows
                                                        (the study-1 baseline features)
                 N states    median over N's seeds of the distinct hashed states N visited in level 0,
                             i.e. before its first level end (level_log[0]["states"], g_agent.py:523,
                             576); on a seed where N never ended level 1 it is the count over the whole
                             budget, and the seed is counted as censored
                 N actions   median over N's seeds of the actions to N's first level end
                             (level1_actions, run_suite.py:132); a seed with no level end counts as the
                             budget (20,000) and as censored
             N's features come from N's rows of the same suite, condition and game, whichever agent
             the line is about.  On N's own line they are circular: N's outcome and N's actions to the
             first level end describe the same runs.
             For each feature: AUROC with a 95% percentile bootstrap interval over games, and the paired
             bootstrap difference AUROC(feature) - AUROC(oracle S) on the same resamples.
    models   logistic regressions (the study-1 baseline fit: Newton, ridge 1e-6, standardised features,
             constant features dropped) on four feature sets: B (area, actions, colours), N search
             (N states, N actions), all five search features, the oracle vector (A1 to A5 as 0/1);
             AUROC in-sample and leave-one-game-out.

The bootstrap uses study 1's procedure: 2,000 resamples of games with replacement, seed 20260927, eight
chunks with default_rng([seed, k]), resamples with one class skipped, percentile interval.  All
statistics of one line share the same resamples, and the script checks that its own loop reproduces
the intervals of analyze_common.bootstrap_auroc_ci for the census and the oracle score.
Worker pool over lines (--workers).  Reads no game, plays nothing, writes nothing outside --out and
--log.  Every output is labelled EXPLORATORY.

Outputs: docs/oracle/oracle_v2.md, docs/oracle/oracle_v2.json, docs/oracle/fig_oracle_vs_census.png,
docs/oracle/fig_search_features.png; the console is also written to logs/oracle_v2.log (UTF-8).

Command (PowerShell; working directory D:\\Research\\horizon\\repo; the HORIZON venv):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\oracle_v2.py --workers 4

EXPECTED OUTPUT (shape):
    oracle_v2 -- EXPLORATORY: study-1 V2 recomputed with the truth-table mechanics vector
    old repository: D:\\Research\\arc3\\repo
    frozen analysis blob scripts/analyze_common.py: caad2273... registered caad2273... match
    frozen analysis blob scripts/analyze_v2.py: 90a849c4... registered 90a849c4... match
    truth tables: minigrid 178 ids, 161 confirmatory; procgen 16 games, 14 confirmatory; unparsed truth entries 0
    rows read: <F> files, <K> confirmatory rows kept, <P> pilot rows skipped
    rows minigrid macro I1: 1610 ... (one line per suite, condition and agent; 1610 on minigrid, 140 on procgen)
    rows with an error field: 0; rows short of their budget: 0
    lines: 20 (minigrid macro 7, minigrid raw 7, procgen center_off 6); workers 4
    line minigrid macro primary I1 (evidence): n=83 pos=61
      census  auroc=0.7187 ci=[0.5902, 0.8298] ba=0.5838 auroc_B=0.8413 verdict=neither | v2.json same
      oracle  auroc=... ci=[..., ...] ba=... auroc_B=... verdict(rule, exploratory)=...
      search  area=... actions=... colours=... N_states=... N_actions=... (censored N seeds: ...)
      models  in-sample B=... Nsearch=... search5=... oracle=... | leave-one-out B=... ...
    ... (one block per line)
    reproduction of study-1 census lines: 20 of 20 identical to docs/tables/v2.json
    bootstrap loop reproduces bootstrap_auroc_ci: 20 of 20 lines
    logistic refit reproduces logistic_fit_predict for B: 20 of 20 lines
    oracle suite line minigrid macro primary: ...
    ... (one per suite, condition and tested subset)
    wrote docs\\oracle\\oracle_v2.md, docs\\oracle\\oracle_v2.json, docs\\oracle\\fig_oracle_vs_census.png, docs\\oracle\\fig_search_features.png
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import importlib
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.dont_write_bytecode = True          # nothing may be written into the study-1 repository

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_OLD = r"D:\Research\arc3\repo"
SUITES = (("minigrid", "raw"), ("minigrid", "macro"), ("procgen", "center_off"))
REGISTERED_BLOBS = {                    # study 1, docs/PREREG.md v1.1 D11 (tag prereg-v1.1)
    "scripts/analyze_common.py": "caad22731807db78aff9c92c993a79a63f042ec3",
    "scripts/analyze_v2.py": "90a849c44e47addd8efdbfa579efdb16288edd50",
}
FEATURES = ("area", "actions", "colours", "N_states", "N_actions")
MODELS = {"B": ("area", "actions", "colours"), "Nsearch": ("N_states", "N_actions"),
          "search5": FEATURES, "oracle": ("A1", "A2", "A3", "A4", "A5")}
LABEL = "EXPLORATORY"
TITLES = {"oracle S": "oracle score S", "area": "grid area", "actions": "action count", "colours": "colour count",
          "N_states": "N states, level 0", "N_actions": "N actions to level end"}

C = None    # study-1 analyze_common, set by load_old
V2 = None   # study-1 analyze_v2


# ---------------------------------------------------------------- study-1 code, read-only
def load_old(old):
    global C, V2
    scripts = os.path.join(old, "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    C = importlib.import_module("analyze_common")
    V2 = importlib.import_module("analyze_v2")
    for mod in (C, V2):
        if os.path.normcase(os.path.dirname(os.path.abspath(mod.__file__))) != os.path.normcase(os.path.abspath(scripts)):
            raise SystemExit(f"{mod.__name__} was imported from {mod.__file__}, not from {scripts}")
    return C, V2


def git_blob(path):
    """git blob hash of a file, as stored and with CRLF read as LF (a Windows checkout)."""
    with open(path, "rb") as f:
        data = f.read()
    out = []
    for d in (data, data.replace(b"\r\n", b"\n")):
        out.append(hashlib.sha1(b"blob %d\0" % len(d) + d).hexdigest())
    return out


# ---------------------------------------------------------------- input
def read_rows(old, conf):
    """Stream the study-1 rows and keep, per confirmatory row, only the fields this analysis uses."""
    slim, n_files, n_pilot, n_err, n_short = [], 0, 0, 0, 0
    for suite, cond in SUITES:
        pat = os.path.join(old, "runs", "suites", suite, cond, "*", "*.json")
        for path in sorted(glob.glob(pat)):
            n_files += 1
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            for r in (d["rows"] if isinstance(d, dict) else d):
                r = C.normalise(r)
                if r.get("game") not in conf[suite]:
                    n_pilot += 1
                    continue
                n_err += "error" in r
                budget = int(r.get("budget") or 20000)
                n_short += int(r.get("actions", 0) or 0) < budget
                ad = r.get("adapter") or {}
                s = dict(suite=r["suite"], condition=r["condition"], agent=r["agent"], game=r["game"],
                         seed=r.get("seed"), level1_completed=bool(r.get("level1_completed")),
                         level1_actions=r.get("level1_actions"), budget=budget,
                         adapter=dict(grid=ad.get("grid"), action_list=ad.get("action_list"),
                                      n_colours=ad.get("n_colours")))
                if r["agent"] == "N":
                    ll = r.get("level_log") or [{}]
                    s["census"] = r.get("census")
                    s["l0_states"] = (ll[0] or {}).get("states")
                    s["l0_won"] = (ll[0] or {}).get("ended") == "won"
                slim.append(s)
    return slim, dict(files=n_files, pilot_rows_skipped=n_pilot, error_rows=n_err, short_rows=n_short)


def oracle_vectors(truth, conf):
    """{(suite, condition): {game: {A1..A5: truth}}}: the truth table read as a census."""
    out = {}
    for suite, cond in SUITES:
        out[(suite, cond)] = {g: {a: C.truth_for(suite, cond, truth[suite][g], a) for a in C.ASSUMPTIONS}
                              for g in conf[suite]}
    return out


def enumerate_lines(rows, truth):
    """The lines of analyze_v2.v2_rows (study 1, lines 106-153) for the three suites and conditions."""
    lines = []
    keys = sorted({(r["suite"], r["condition"], r["agent"]) for r in rows})
    for suite, cond in sorted({(k[0], k[1]) for k in keys}):
        games = C.confirmatory(suite, truth[suite])
        excl = C.V2_EXCLUDE.get((suite, cond), ())
        excl_i1 = C.V2_EXCLUDE_I1.get((suite, cond), excl)
        if excl or excl_i1:
            subsets = [("primary", None), ("primary, D9b included", None), ("all games", games)]
        else:
            subsets = [("all", games)]
        if suite == "procgen":
            subsets.append(("in_range", [g for g in games if g in C.IN_RANGE_C]))
        for name, gs in subsets:
            tested = name in ("primary", "all", "in_range")
            for agent in sorted(k[2] for k in keys if k[0] == suite and k[1] == cond):
                if name == "primary, D9b included" and (agent != "I1" or set(excl_i1) == set(excl)):
                    continue
                if name == "primary":
                    g2 = [g for g in games if g not in C.v2_exclusions(suite, cond, agent)]
                elif name == "primary, D9b included":
                    g2 = [g for g in games if g not in excl]
                else:
                    g2 = list(gs)
                role = "evidence" if agent in ("R", "I1") else "instrument check"
                lines.append(dict(suite=suite, condition=cond, subset=name, agent=agent, role=role,
                                  tested=tested, games=g2))
    return lines


# ---------------------------------------------------------------- statistics
def boot_loop(scores, labels, n_resamples, seed, chunks=8):
    """Study 1's bootstrap (analyze_common._boot_chunk) with several scores on the same resamples.
    Returns {name: list of AUROC values} over the resamples that kept both classes."""
    per = [n_resamples // chunks + (1 if k < n_resamples % chunks else 0) for k in range(chunks)]
    vals = {k: [] for k in scores}
    m = len(labels)
    for k in range(chunks):
        rng = np.random.default_rng([seed, k])
        for _ in range(per[k]):
            idx = rng.integers(0, m, size=m)
            lab = [labels[i] for i in idx]
            if all(lab) or not any(lab):
                continue
            for name, s in scores.items():
                vals[name].append(C.auroc([s[i] for i in idx], lab))
    return vals


def pct(v):
    if not v:
        return None, None
    s = sorted(v)
    return float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


def fit_logistic(X, y, ridge=1e-6, iters=100):
    """analyze_common.logistic_fit_predict, refitted so that it can predict a held-out game."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = X.std(axis=0) > 0 if X.size else np.array([], dtype=bool)
    if X.size == 0 or not keep.any():
        base = float(y.mean())
        return lambda Xn: np.full(len(Xn), base)
    mu, sd = X[:, keep].mean(0), X[:, keep].std(0)
    A = np.hstack([np.ones((len(y), 1)), (X[:, keep] - mu) / sd])
    w = np.zeros(A.shape[1])
    R = ridge * np.eye(A.shape[1])
    R[0, 0] = 0.0
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        for _ in range(iters):
            p = 1 / (1 + np.exp(-A @ w))
            g = A.T @ (p - y) + R @ w
            H = A.T @ (A * (p * (1 - p))[:, None]) + R
            step = np.linalg.solve(H + 1e-12 * np.eye(len(w)), g)
            w -= step
            if np.max(np.abs(step)) < 1e-10:
                break

    def predict(Xn):
        Xn = np.asarray(Xn, dtype=float)
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            return 1 / (1 + np.exp(-(w[0] + ((Xn[:, keep] - mu) / sd) @ w[1:])))
    return predict


def model_aurocs(X, Y):
    """In-sample and leave-one-game-out AUROC of one logistic model; NaN predictions count as 0.5."""
    X = np.asarray(X, dtype=float)
    y = np.array([int(v) for v in Y])
    if len(y) < 3 or y.min() == y.max():
        return None, None, 0
    p_in = np.nan_to_num(fit_logistic(X, y)(X), nan=0.5)
    loo, nan = [], 0
    for i in range(len(y)):
        tr = np.arange(len(y)) != i
        if y[tr].min() == y[tr].max():
            loo.append(float(y[tr].mean()))
            continue
        p = float(fit_logistic(X[tr], y[tr])(X[i:i + 1])[0])
        if not np.isfinite(p):
            p, nan = 0.5, nan + 1
        loo.append(p)
    return C.auroc(list(p_in), list(Y)), C.auroc(loo, list(Y)), nan


# ---------------------------------------------------------------- one line (worker)
_G = {}


def _init(old, rows, census, oracle, n_resamples, seed):
    load_old(old)
    _G.update(rows=rows, census=census, oracle=oracle, n_resamples=n_resamples, seed=seed)
    n_by = {}
    for r in rows:
        if r["agent"] == "N":
            n_by.setdefault((r["suite"], r["condition"], r["game"]), []).append(r)
    _G["n_by"] = n_by


def _median(v):
    return float(np.median(v)) if v else None


def line_job(spec):
    rows, R, seed = _G["rows"], _G["n_resamples"], _G["seed"]
    suite, cond, agent, games = spec["suite"], spec["condition"], spec["agent"], spec["games"]
    census, oracle = _G["census"][(suite, cond)], _G["oracle"][(suite, cond)]
    gt_c = V2.game_table(rows, suite, cond, agent, games, census)
    gt_o = V2.game_table(rows, suite, cond, agent, games, oracle)
    st_c = V2.v2_stats(gt_c, R, seed, 1)
    st_o = V2.v2_stats(gt_o, R, seed, 1)
    if not spec["tested"]:
        st_c["verdict"] = st_o["verdict"] = "reported, not tested"

    per_game, feat = [], {k: [] for k in FEATURES}
    s_census = {x[0]: x[1] for x in gt_c}
    for g, S, P, Y, f in gt_o:
        nr = _G["n_by"].get((suite, cond, g), [])
        st = [r["l0_states"] for r in nr if r.get("l0_states") is not None]
        ac = [r["level1_actions"] if r["level1_actions"] is not None else r["budget"] for r in nr]
        rec = dict(game=g, truth=[oracle[g][a] for a in C.ASSUMPTIONS], S_oracle=S, P_oracle=bool(P),
                   S_census=s_census.get(g), Y=bool(Y), area=f[0], actions=f[1], colours=f[2],
                   N_states=_median(st), N_states_censored=sum(not r.get("l0_won") for r in nr),
                   N_actions=_median(ac), N_actions_censored=sum(r["level1_actions"] is None for r in nr),
                   N_seeds=len(nr))
        per_game.append(rec)
        for k in FEATURES:
            feat[k].append(rec[k])
    Y = [x["Y"] for x in per_game]
    missing = {k: sum(v is None for v in feat[k]) for k in FEATURES}

    scores = {"census": [x[1] for x in gt_c], "oracle": [x["S_oracle"] for x in per_game]}
    for k in FEATURES:
        if not missing[k]:
            scores[k] = [-v for v in feat[k]]
    have_both = bool(Y) and any(Y) and not all(Y)
    vals = boot_loop(scores, Y, R, seed) if have_both else {k: [] for k in scores}
    search = {}
    for k in FEATURES:
        if k not in scores:
            search[k] = dict(auroc=None, ci_low=None, ci_high=None, diff=None, diff_low=None, diff_high=None,
                             missing=missing[k])
            continue
        a = C.auroc(scores[k], Y) if have_both else None
        lo, hi = pct(vals[k])
        d = [x - y for x, y in zip(vals[k], vals["oracle"])]
        dlo, dhi = pct(d)
        search[k] = dict(auroc=a, ci_low=lo, ci_high=hi,
                         diff=None if a is None or st_o["auroc"] is None else a - st_o["auroc"],
                         diff_low=dlo, diff_high=dhi, missing=0)
    # the loop must reproduce v2_stats' intervals where v2_stats computed one
    same = True
    for name, st in (("census", st_c), ("oracle", st_o)):
        if st["ci_low"] is not None:
            lo, hi = pct(vals[name])
            same &= lo is not None and abs(lo - st["ci_low"]) < 1e-12 and abs(hi - st["ci_high"]) < 1e-12
    loop_ci = dict(census=pct(vals["census"]), oracle=pct(vals["oracle"]))

    models = {}
    for mname, cols in MODELS.items():
        if mname == "oracle":
            X = [[1.0 if v == C.HOLDS else 0.0 for v in x["truth"]] for x in per_game]
        elif any(missing[c] for c in cols):
            models[mname] = dict(in_sample=None, loo=None, nan=0)
            continue
        else:
            X = [[x[c] for c in cols] for x in per_game]
        a_in, a_loo, nan = model_aurocs(X, Y)
        models[mname] = dict(in_sample=a_in, loo=a_loo, nan=nan)
    b_old = C.logistic_fit_predict([x[4] for x in gt_o], [int(y) for y in Y]) if gt_o else []
    b_old_auroc = C.auroc(list(b_old), Y) if gt_o else None
    b_same = (b_old_auroc is None and models["B"]["in_sample"] is None) or (
        b_old_auroc is not None and models["B"]["in_sample"] is not None
        and abs(b_old_auroc - models["B"]["in_sample"]) < 1e-9)

    out = {k: v for k, v in spec.items() if k != "games"}
    out.update(census=st_c, oracle=st_o, search=search, models=models, loop_ci=loop_ci,
               loop_reproduces=same, baseline_refit_reproduces=b_same, per_game=per_game)
    return out


# ---------------------------------------------------------------- output
def f4(v):
    return "" if v is None else (f"{v:.4f}" if isinstance(v, float) else str(v))


def ci(lo, hi):
    return "" if lo is None else f"[{lo:.4f}, {hi:.4f}]"


def same_as_v2json(st, ref):
    if ref is None:
        return False
    keys = (("n", 5), ("pos", 6), ("auroc", 7), ("ci_low", 8), ("ci_high", 9), ("ba", 10), ("auroc_B", 11),
            ("verdict", 12))
    for k, i in keys:
        a, b = st[k], ref[i]
        if isinstance(a, float) or isinstance(b, float):
            if a is None or b is None or round(a, 4) != round(b, 4):
                return False
        elif a != b:
            return False
    return True


def suite_lines(results):
    """analyze_v2.v2_rows' suite-level rule (study 1, lines 156-169), applied to the oracle lines."""
    out = []
    seen = []
    for r in results:
        key = (r["suite"], r["condition"], r["subset"])
        if key not in seen:
            seen.append(key)
    for key in seen:
        per = {r["agent"]: r["oracle"] for r in results if (r["suite"], r["condition"], r["subset"]) == key}
        tested = any(r["tested"] for r in results if (r["suite"], r["condition"], r["subset"]) == key)
        if not tested:
            sv = "reported, not tested"
        else:
            live = [(a, per[a]) for a in ("R", "I1") if a in per and per[a]["verdict"] != "VOID"
                    and per[a]["auroc"] is not None]
            by = " and ".join(a for a, _ in live) + (" alone" if len(live) == 1 else "")
            if not live:
                sv = "not decidable (no non-void evidence agent)"
            elif all(st["auroc"] <= 0.65 for _, st in live):
                sv = f"suite FAIL (decided by {by})"
            else:
                sv = f"not failed (decided by {by})"
        out.append(list(key) + [sv])
    return out


def write_md(path, meta, results, slines):
    L = []
    w = L.append
    w("# Oracle test (EXPLORATORY)")
    w("")
    w("**EXPLORATORY.** Written by scripts/oracle_v2.py from the committed rows and truth tables of study 1 "
      "(read-only). Nothing here is registered, nothing here is a claim, and no verdict word below is a "
      "registered verdict: where a column says what the study-1 V2 rule would print, it applies a rule "
      "registered for study 1's census to a different score, after study 1's outcome was known.")
    w("")
    w("## Inputs and checks")
    w("")
    w("*EXPLORATORY.*")
    for k, v in meta["checks"].items():
        w(f"- {k}: {v}")
    w("")
    w("## Table 1. Study-1 V2 with the census and with the oracle")
    w("")
    w("*EXPLORATORY.* Census columns: recomputed by study 1's analyze_v2 functions; \"v2.json\" says whether "
      "they equal docs/tables/v2.json of study 1 to four decimals. Oracle columns: the same functions with "
      "the truth-table vector A1 to A5. AUROC_B is the study-1 nuisance baseline; it does not depend on the "
      "mechanics vector, so it is the same in both. \"rule\" is the verdict the study-1 V2 rule prints.")
    w("")
    hdr = ["suite", "condition", "subset", "agent", "role", "n", "pos", "census AUROC", "census CI",
           "census BA", "census rule", "v2.json", "oracle AUROC", "oracle CI", "oracle BA", "oracle rule",
           "AUROC_B"]
    w("| " + " | ".join(hdr) + " |")
    w("|" + "---|" * len(hdr))
    for r in results:
        c, o = r["census"], r["oracle"]
        w("| " + " | ".join([r["suite"], r["condition"], r["subset"], r["agent"], r["role"], str(o["n"]),
                             str(o["pos"]), f4(c["auroc"]), ci(c["ci_low"], c["ci_high"]), f4(c["ba"]),
                             c["verdict"], "same" if r["v2json_same"] else "DIFFERS", f4(o["auroc"]),
                             ci(o["ci_low"], o["ci_high"]), f4(o["ba"]), o["verdict"], f4(o["auroc_B"])]) + " |")
    w("")
    w("Suite lines that the study-1 rule would print for the oracle (EXPLORATORY):")
    w("")
    for s in slines:
        w(f"- {s[0]} {s[1]} {s[2]}: {s[3]}")
    w("")
    w("## Table 2. One-feature search scores")
    w("")
    w("*EXPLORATORY.* AUROC of each feature, negated (a larger search predicts no completion), with its 95% "
      "bootstrap interval; the intervals are computed on every line, void or not, on the same resamples as "
      "the oracle. N states and N actions are taken from N's rows, whatever the line's agent; on N's own "
      "lines they describe the same runs as the outcome and are circular. An AUROC below 0.5 means the "
      "feature runs the other way.")
    w("")
    hdr = ["suite", "condition", "subset", "agent", "n", "oracle AUROC"] + list(FEATURES)
    w("| " + " | ".join(hdr) + " |")
    w("|" + "---|" * len(hdr))
    for r in results:
        cells = [r["suite"], r["condition"], r["subset"], r["agent"], str(r["oracle"]["n"]),
                 f4(r["oracle"]["auroc"]) + " " + ci(*r["loop_ci"]["oracle"])]
        for k in FEATURES:
            s = r["search"][k]
            cells.append(f4(s["auroc"]) + " " + ci(s["ci_low"], s["ci_high"]))
        w("| " + " | ".join(cells) + " |")
    w("")
    w("## Table 3. Paired difference, feature minus oracle")
    w("")
    w("*EXPLORATORY.* AUROC(feature) minus AUROC(oracle S) on the same games, with the 95% percentile "
      "interval of the difference over the same 2,000 resamples.")
    w("")
    hdr = ["suite", "condition", "subset", "agent"] + list(FEATURES)
    w("| " + " | ".join(hdr) + " |")
    w("|" + "---|" * len(hdr))
    for r in results:
        cells = [r["suite"], r["condition"], r["subset"], r["agent"]]
        for k in FEATURES:
            s = r["search"][k]
            cells.append(f4(s["diff"]) + " " + ci(s["diff_low"], s["diff_high"]))
        w("| " + " | ".join(cells) + " |")
    w("")
    w("## Table 4. Logistic models, in-sample and leave-one-game-out")
    w("")
    w("*EXPLORATORY.* AUROC of the fitted probabilities. In-sample values favour models with more features; "
      "the leave-one-game-out values do not. B = area, actions, colours; Nsearch = N states, N actions; "
      "search5 = all five; oracle = A1 to A5 as 0/1 (constant columns dropped).")
    w("")
    hdr = ["suite", "condition", "subset", "agent", "n"] + [f"{m} in" for m in MODELS] + [f"{m} loo" for m in MODELS]
    w("| " + " | ".join(hdr) + " |")
    w("|" + "---|" * len(hdr))
    for r in results:
        cells = [r["suite"], r["condition"], r["subset"], r["agent"], str(r["oracle"]["n"])]
        cells += [f4(r["models"][m]["in_sample"]) for m in MODELS] + [f4(r["models"][m]["loo"]) for m in MODELS]
        w("| " + " | ".join(cells) + " |")
    w("")
    w("## Table 5. What the oracle vector looks like")
    w("")
    w("*EXPLORATORY.* Per suite and condition, over the confirmatory games: how many games have each oracle "
      "score S, and how many have P (A2, A3, A4 and A5 all hold).")
    w("")
    for (suite, cond), d in meta["oracle_shape"].items():
        w(f"- {suite} {cond}: S counts {d['S']}; P holds on {d['P']} of {d['n']}")
    w("")
    w("Per-game values for every line (truth vector, scores, outcome, features, censored seeds) are in "
      "docs/oracle/oracle_v2.json, key \"lines\" -> \"per_game\".")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


# ---------------------------------------------------------------- figures
def label(r):
    sub = {"primary": "primary", "primary, D9b included": "D9b incl.", "all games": "all games", "all": "all",
           "in_range": "in range"}[r["subset"]]
    return f"{r['suite']} {r['condition']} {sub} {r['agent']}"


def figures(out, results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ink, muted, grid = "#2b2b29", "#6f6e69", "#e4e3de"
    blue, orange = "#2a78d6", "#eb6834"      # categorical slots 1 and 2 of the reference palette
    plt.rcParams.update({"font.size": 8, "axes.edgecolor": muted, "axes.labelcolor": ink,
                         "xtick.color": muted, "ytick.color": ink, "axes.spines.top": False,
                         "axes.spines.right": False})
    n = len(results)
    ys = np.arange(n)[::-1]

    fig, ax = plt.subplots(figsize=(7.5, 0.32 * n + 1.4))
    for y, r in zip(ys, results):
        c, o = r["census"], r["oracle"]
        lo, hi = r["loop_ci"]["oracle"]
        if lo is not None:
            ax.plot([lo, hi], [y - 0.12, y - 0.12], color=orange, lw=2, solid_capstyle="round")
        clo, chi = r["loop_ci"]["census"]
        if clo is not None:
            ax.plot([clo, chi], [y + 0.12, y + 0.12], color=blue, lw=2, solid_capstyle="round")
        if c["auroc"] is not None:
            ax.plot(c["auroc"], y + 0.12, "o", ms=6, color=blue, mec="white", mew=1.5, zorder=3)
        if o["auroc"] is not None:
            ax.plot(o["auroc"], y - 0.12, "D", ms=6, color=orange, mec="white", mew=1.5, zorder=3)
        if o["auroc_B"] is not None:
            ax.plot(o["auroc_B"], y, "s", ms=6, mfc="none", mec=muted, mew=1.2, zorder=2)
    for x, st in ((0.5, ":"), (0.65, "--"), (0.80, "--")):
        ax.axvline(x, color=muted, lw=0.8, ls=st, zorder=0)
    ax.set_yticks(ys)
    ax.set_yticklabels([label(r) for r in results])
    ax.set_xlim(-0.02, 1.02)
    ax.set_xlabel("AUROC for level-1 completion")
    ax.grid(axis="x", color=grid, lw=0.6)
    ax.set_axisbelow(True)
    h = [plt.Line2D([], [], marker="o", color=blue, lw=2, label="census score (study 1)"),
         plt.Line2D([], [], marker="D", color=orange, lw=2, label="oracle score (truth table)"),
         plt.Line2D([], [], marker="s", ls="none", mfc="none", mec=muted, label="nuisance baseline B")]
    fig.legend(handles=h, loc="lower center", ncol=3, frameon=False)
    ax.set_title("EXPLORATORY. Study-1 V2: census score and oracle score, 95% bootstrap intervals",
                 loc="left", color=ink)
    fig.tight_layout(rect=(0, 0.6 / (0.32 * n + 1.4), 1, 1))
    p1 = os.path.join(out, "fig_oracle_vs_census.png")
    fig.savefig(p1, dpi=200)
    plt.close(fig)

    panels = [("oracle S", lambda r: (r["oracle"]["auroc"],) + tuple(r["loop_ci"]["oracle"]))] + [
        (k, (lambda k: lambda r: (r["search"][k]["auroc"], r["search"][k]["ci_low"], r["search"][k]["ci_high"]))(k))
        for k in FEATURES]
    fig, axes = plt.subplots(1, len(panels), figsize=(11, 0.32 * n + 1.4), sharey=True)
    for ax, (title, get) in zip(axes, panels):
        col = orange if title == "oracle S" else blue
        for y, r in zip(ys, results):
            a, lo, hi = get(r)
            if lo is not None:
                ax.plot([lo, hi], [y, y], color=col, lw=2, solid_capstyle="round")
            if a is not None:
                ax.plot(a, y, "o", ms=5, color=col, mec="white", mew=1.2, zorder=3)
        ax.axvline(0.5, color=muted, lw=0.8, ls=":")
        ax.set_xlim(-0.03, 1.03)
        ax.set_title(TITLES.get(title, title), color=ink)
        ax.grid(axis="x", color=grid, lw=0.6)
        ax.set_axisbelow(True)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels([label(r) for r in results])
    fig.suptitle("EXPLORATORY. AUROC of one score at a time for level-1 completion (a larger search is "
                 "scored as harder), 95% bootstrap intervals", x=0.01, ha="left", color=ink)
    fig.tight_layout()
    p2 = os.path.join(out, "fig_search_features.png")
    fig.savefig(p2, dpi=200)
    plt.close(fig)
    return p1, p2


# ---------------------------------------------------------------- main
def rel(p):
    try:
        return os.path.relpath(p, REPO)
    except ValueError:                  # another drive
        return p


class Tee:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.f = open(path, "w", encoding="utf-8")

    def __call__(self, s=""):
        print(s, flush=True)
        self.f.write(s + "\n")
        self.f.flush()


def main(argv=None):
    ap = argparse.ArgumentParser(description="EXPLORATORY oracle test on study-1 data")
    ap.add_argument("--old-repo", default=DEFAULT_OLD)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--resamples", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260927)
    ap.add_argument("--out", default=os.path.join(REPO, "docs", "oracle"))
    ap.add_argument("--log", default=os.path.join(REPO, "logs", "oracle_v2.log"))
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args(argv)
    say = Tee(args.log)
    try:
        return _main(args, say)
    finally:
        say.f.close()


def _main(args, say):
    old = os.path.abspath(args.old_repo)
    say("oracle_v2 -- EXPLORATORY: study-1 V2 recomputed with the truth-table mechanics vector")
    say(f"old repository: {old}")
    load_old(old)
    checks = {}
    for relpath, reg in REGISTERED_BLOBS.items():
        raw, lf = git_blob(os.path.join(old, *relpath.split("/")))
        ok = "match" if reg in (raw, lf) else "DIFFERS"
        got = raw if raw == reg else lf
        say(f"frozen analysis blob {relpath}: {got} registered {reg} {ok}")
        checks[f"blob {relpath}"] = f"{got} (registered at study-1 prereg-v1.1: {reg}) {ok}"

    truth = {"minigrid": C.parse_truth_minigrid(os.path.join(old, "docs", "GROUND_TRUTH_minigrid.md")),
             "procgen": C.parse_truth_procgen(os.path.join(old, "docs", "GROUND_TRUTH_procgen.md"))}
    conf = {s: set(C.confirmatory(s, truth[s])) for s in truth}
    unparsed = sum(truth[s][g][k] is None for s in truth for g in conf[s]
                   for k in truth[s][g] if k != "status")
    say(f"truth tables: minigrid {len(truth['minigrid'])} ids, {len(conf['minigrid'])} confirmatory; "
        f"procgen {len(truth['procgen'])} games, {len(conf['procgen'])} confirmatory; unparsed truth entries {unparsed}")
    checks["truth tables"] = (f"minigrid {len(truth['minigrid'])} ids, {len(conf['minigrid'])} confirmatory; "
                              f"procgen {len(truth['procgen'])} games, {len(conf['procgen'])} confirmatory; "
                              f"unparsed truth entries {unparsed}")
    if unparsed:
        raise SystemExit("a confirmatory truth entry could not be parsed; stopping")

    rows, info = read_rows(old, conf)
    say(f"rows read: {info['files']} files, {len(rows)} confirmatory rows kept, {info['pilot_rows_skipped']} pilot rows skipped")
    checks["rows"] = f"{info['files']} files, {len(rows)} confirmatory rows kept, {info['pilot_rows_skipped']} pilot rows skipped"
    counts = {}
    for r in rows:
        counts[(r["suite"], r["condition"], r["agent"])] = counts.get((r["suite"], r["condition"], r["agent"]), 0) + 1
    for k in sorted(counts):
        say(f"rows {k[0]} {k[1]} {k[2]}: {counts[k]}")
        checks[f"rows {k[0]} {k[1]} {k[2]}"] = counts[k]
    say(f"rows with an error field: {info['error_rows']}; rows short of their budget: {info['short_rows']}")
    checks["rows with an error field"] = info["error_rows"]
    checks["rows short of their budget"] = info["short_rows"]

    census = {sc: C.census_by_game(rows, *sc) for sc in SUITES}
    oracle = oracle_vectors(truth, conf)
    shape = {}
    for (suite, cond), d in oracle.items():
        S = [sum(v[a] == C.HOLDS for a in C.ASSUMPTIONS) for v in d.values()]
        P = sum(all(v[a] == C.HOLDS for a in ("A2", "A3", "A4", "A5")) for v in d.values())
        shape[(suite, cond)] = dict(n=len(d), S={s: S.count(s) for s in sorted(set(S))}, P=P)

    lines = enumerate_lines(rows, truth)
    per_sc = {}
    for ln in lines:
        per_sc[f"{ln['suite']} {ln['condition']}"] = per_sc.get(f"{ln['suite']} {ln['condition']}", 0) + 1
    say(f"lines: {len(lines)} ({', '.join(f'{k} {v}' for k, v in per_sc.items())}); workers {args.workers}")

    initargs = (old, rows, census, oracle, args.resamples, args.seed)
    if args.workers > 1:
        with Pool(args.workers, initializer=_init, initargs=initargs) as pool:
            results = pool.map(line_job, lines, chunksize=1)
    else:
        _init(*initargs)
        results = [line_job(ln) for ln in lines]

    with open(os.path.join(old, "docs", "tables", "v2.json"), encoding="utf-8") as f:
        v2ref = {tuple(r[:4]): r for r in json.load(f)["rows"]}
    n_same = n_loop = n_b = 0
    for r in results:
        ref = v2ref.get((r["suite"], r["condition"], r["subset"], r["agent"]))
        r["v2json"] = ref
        r["v2json_same"] = same_as_v2json(r["census"], ref)
        n_same += r["v2json_same"]
        n_loop += r["loop_reproduces"]
        n_b += r["baseline_refit_reproduces"]
        c, o = r["census"], r["oracle"]
        cen = sum(x["N_states_censored"] for x in r["per_game"])
        cen_a = sum(x["N_actions_censored"] for x in r["per_game"])
        say(f"line {r['suite']} {r['condition']} {r['subset']} {r['agent']} ({r['role']}): n={o['n']} pos={o['pos']}")
        say(f"  census  auroc={f4(c['auroc'])} ci={ci(c['ci_low'], c['ci_high']) or 'none'} ba={f4(c['ba'])} "
            f"auroc_B={f4(c['auroc_B'])} verdict={c['verdict']} | v2.json {'same' if r['v2json_same'] else 'DIFFERS'}")
        say(f"  oracle  auroc={f4(o['auroc'])} ci={ci(o['ci_low'], o['ci_high']) or 'none'} ba={f4(o['ba'])} "
            f"auroc_B={f4(o['auroc_B'])} verdict(rule, exploratory)={o['verdict']}")
        say("  search  " + " ".join(f"{k}={f4(r['search'][k]['auroc'])}" for k in FEATURES)
            + f" (censored N seeds: states {cen}, actions {cen_a})")
        say("  models  in-sample " + " ".join(f"{m}={f4(r['models'][m]['in_sample'])}" for m in MODELS)
            + " | leave-one-out " + " ".join(f"{m}={f4(r['models'][m]['loo'])}" for m in MODELS))
    say(f"reproduction of study-1 census lines: {n_same} of {len(results)} identical to docs/tables/v2.json")
    say(f"bootstrap loop reproduces bootstrap_auroc_ci: {n_loop} of {len(results)} lines")
    say(f"logistic refit reproduces logistic_fit_predict for B: {n_b} of {len(results)} lines")
    checks["reproduction of study-1 census lines"] = f"{n_same} of {len(results)} identical to docs/tables/v2.json"
    checks["bootstrap loop reproduces bootstrap_auroc_ci"] = f"{n_loop} of {len(results)} lines"
    checks["logistic refit reproduces logistic_fit_predict for B"] = f"{n_b} of {len(results)} lines"
    sl = suite_lines(results)
    for s in sl:
        say(f"oracle suite line {s[0]} {s[1]} {s[2]}: {s[3]}")

    os.makedirs(args.out, exist_ok=True)
    meta = dict(label=LABEL, script="scripts/oracle_v2.py", old_repo=old, resamples=args.resamples,
                seed=args.seed, checks=checks,
                oracle_shape={k: v for k, v in shape.items()})
    md = os.path.join(args.out, "oracle_v2.md")
    write_md(md, meta, results, sl)
    js = os.path.join(args.out, "oracle_v2.json")
    with open(js, "w", encoding="utf-8") as f:
        json.dump(dict(meta=dict(meta, oracle_shape={f"{k[0]} {k[1]}": v for k, v in shape.items()}),
                       suite_lines=sl, lines=results), f, indent=1, default=str)
    written = [md, js]
    if not args.no_figures:
        written += list(figures(args.out, results))
    say("wrote " + ", ".join(rel(p) for p in written))
    return results


if __name__ == "__main__":
    main()
