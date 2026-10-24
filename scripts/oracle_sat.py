"""
oracle_sat.py -- EXPLORATORY.  How the perfect separations of the oracle test arise.

The oracle test (scripts/oracle_v2.py; output docs/oracle/oracle_v2.json, console logs/oracle_v2.log)
reported AUROC 1.0000 for some search features and some logistic models.  This script says, for every
line and every such feature or model, what lies behind the 1.0000:
    - the values for the completing games (Y = 1) and the non-completing games (Y = 0): every value
      when the line has at most 20 games, otherwise n, minimum, median and maximum (all values are in
      the JSON);
    - the overlap: the number of completing games whose value lies inside the range of the
      non-completing games, the number of non-completing games inside the range of the completing ones,
      and the gap between the two ranges (positive = no overlap);
    - the censoring flag: a seed of N "censored" never ended level 1 within its 20,000-action budget
      (level1_actions null; run_suite.py:132).  Per game, flag "majority" = more than half of N's seeds
      censored, flag "any" = at least one censored.  For each flag: whether it alone separates the
      completing games from the others, and the AUROC of the flag alone (flagged = predicted not to
      complete).  For a feature it also counts the non-completing games whose median N actions equals
      the budget, i.e. whose value is the censoring value itself.
Features are oriented as in oracle_v2.py: a larger value predicts no completion.  Models are oracle_v2's
logistic fits (B, Nsearch, search5, oracle), in-sample and leave-one-game-out; their "values" are the
fitted probabilities (a larger probability predicts completion).

It also reports, for every line, the honest pre-run number: the AUROC of the three features known
before any agent runs (grid area, action count, colour count), each alone and together in oracle_v2's
logistic model, in-sample and leave-one-game-out.

A consistency check comes first: the per-game N medians and censored-seed counts of oracle_v2.json are
recomputed from the study-1 rows and must agree on every game of every line.

Inputs, read only: docs/oracle/oracle_v2.json (committed); the study-1 rows under
D:\\Research\\arc3\\repo\\runs\\suites and study-1 scripts/analyze_common.py and analyze_v2.py, through
oracle_v2.read_rows and oracle_v2.load_old (bytecode writing off).  Worker pool over lines.  Plays
nothing.  Writes docs/oracle/saturation.md, docs/oracle/saturation.json and logs/oracle_sat.log (UTF-8).

Command (PowerShell; working directory D:\\Research\\horizon\\repo; the HORIZON venv):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\oracle_sat.py --workers 4

EXPECTED OUTPUT (shape):
    oracle_sat -- EXPLORATORY: how the perfect separations of the oracle test arise
    oracle_v2.json: 20 lines
    rows read: 10500 files, 10080 confirmatory rows kept, 420 pilot rows skipped
    consistency with oracle_v2.json (N medians and censored seeds): <G> of <G> games agree on 20 of 20 lines
    line minigrid macro primary I1 (evidence): n=83 pos=61
      pre-run  area=... actions=... colours=... | B in-sample=... leave-one-out=...
      censoring flag  majority: separates no, auroc=...; any: separates no, auroc=...
      saturated  (none) | or one line per item:
      N_actions auroc=1.0000 complete n=.. [min .., med .., max ..] not n=.. [...] overlap 0/0 gap=.. at budget ../..
    ... (one block per line)
    saturated items: <K> on <L> lines; of them separated by the majority censoring flag alone: <M> lines
    wrote docs\\oracle\\saturation.md, docs\\oracle\\saturation.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import oracle_v2 as O  # noqa: E402

PRE = ("area", "actions", "colours")
LIST_MAX = 20
_G = {}


def _init(old):
    O.load_old(old)


def summary(v):
    if not v:
        return dict(n=0)
    return dict(n=len(v), min=float(min(v)), median=float(np.median(v)), max=float(max(v)))


def separation(pos, neg, larger_is_pos):
    """Overlap of two value sets; values oriented so that larger means predicted completion."""
    p = [x if larger_is_pos else -x for x in pos]
    q = [x if larger_is_pos else -x for x in neg]
    if not p or not q:
        return dict(pos_in_neg_range=None, neg_in_pos_range=None, gap=None)
    lo_q, hi_q, lo_p, hi_p = min(q), max(q), min(p), max(p)
    return dict(pos_in_neg_range=sum(lo_q <= x <= hi_q for x in p),
                neg_in_pos_range=sum(lo_p <= x <= hi_p for x in q),
                gap=float(lo_p - hi_q))          # > 0: every completing game above every other


def flag_report(flags, Y):
    sep = all(f != y for f, y in zip(flags, Y))   # flagged exactly the non-completing games
    a = O.C.auroc([0 if f else 1 for f in flags], Y) if any(Y) and not all(Y) else None
    return dict(separates=sep, auroc=a, flagged=sum(flags))


def line_job(line):
    pg = line["per_game"]
    Y = [bool(x["Y"]) for x in pg]
    out = {k: line[k] for k in ("suite", "condition", "subset", "agent", "role")}
    out["n"], out["pos"] = len(pg), sum(Y)
    both = any(Y) and not all(Y)
    # the pre-run number: area, action count, colour count, alone and together
    pre = {}
    for k in PRE:
        pre[k] = O.C.auroc([-x[k] for x in pg], Y) if both else None
    a_in, a_loo, nan = O.model_aurocs([[x[k] for k in PRE] for x in pg], Y) if both else (None, None, 0)
    pre["B_in_sample"], pre["B_loo"], pre["B_loo_nan"] = a_in, a_loo, nan
    pre["constant"] = [k for k in PRE if len({x[k] for x in pg}) == 1]
    out["pre_run"] = pre
    # the censoring flags
    maj = [2 * x["N_actions_censored"] > x["N_seeds"] for x in pg]
    anyf = [x["N_actions_censored"] > 0 for x in pg]
    out["censor_flag"] = dict(majority=flag_report(maj, Y), any=flag_report(anyf, Y))
    # the saturated items
    sat = []
    for k in O.FEATURES:
        if any(x[k] is None for x in pg) or not both:
            continue
        a = O.C.auroc([-x[k] for x in pg], Y)
        if round(a, 4) != 1.0:
            continue
        pos = [x[k] for x, y in zip(pg, Y) if y]
        neg = [x[k] for x, y in zip(pg, Y) if not y]
        item = dict(kind="feature", name=k, auroc=a, complete=sorted(pos), not_complete=sorted(neg),
                    complete_summary=summary(pos), not_complete_summary=summary(neg))
        item.update(separation(pos, neg, larger_is_pos=False))
        if k == "N_actions":
            item["not_complete_at_budget"] = sum(x["N_actions"] >= 20000 for x, y in zip(pg, Y) if not y)
            item["complete_at_budget"] = sum(x["N_actions"] >= 20000 for x, y in zip(pg, Y) if y)
        sat.append(item)
    for mname, cols in O.MODELS.items():
        if not both:
            continue
        if mname == "oracle":
            X = np.array([[1.0 if v == O.C.HOLDS else 0.0 for v in x["truth"]] for x in pg])
        elif any(x[c] is None for x in pg for c in cols):
            continue
        else:
            X = np.array([[x[c] for c in cols] for x in pg], dtype=float)
        y = np.array([int(v) for v in Y])
        p_in = np.nan_to_num(O.fit_logistic(X, y)(X), nan=0.5)
        loo = []
        for i in range(len(y)):
            tr = np.arange(len(y)) != i
            if y[tr].min() == y[tr].max():
                loo.append(float(y[tr].mean()))
                continue
            p = float(O.fit_logistic(X[tr], y[tr])(X[i:i + 1])[0])
            loo.append(p if np.isfinite(p) else 0.5)
        for fit, p in (("in-sample", list(map(float, p_in))), ("leave-one-out", loo)):
            a = O.C.auroc(p, Y)
            if a is None or round(a, 4) != 1.0:
                continue
            pos = [v for v, yy in zip(p, Y) if yy]
            neg = [v for v, yy in zip(p, Y) if not yy]
            item = dict(kind="model", name=f"{mname} {fit}", auroc=a, complete=sorted(pos),
                        not_complete=sorted(neg), complete_summary=summary(pos), not_complete_summary=summary(neg))
            item.update(separation(pos, neg, larger_is_pos=True))
            sat.append(item)
    out["saturated"] = sat
    out["games"] = [dict(game=x["game"], Y=x["Y"], **{k: x[k] for k in PRE + ("N_states", "N_actions")},
                         N_censored=x["N_actions_censored"], N_seeds=x["N_seeds"]) for x in pg]
    return out


def check_consistency(rows, lines):
    """Recompute N's per-game medians and censored counts from the rows; compare with oracle_v2.json."""
    by = {}
    for r in rows:
        if r["agent"] == "N":
            by.setdefault((r["suite"], r["condition"], r["game"]), []).append(r)
    ok_lines, games_ok, games_all = 0, 0, 0
    for ln in lines:
        good = True
        for x in ln["per_game"]:
            nr = by.get((ln["suite"], ln["condition"], x["game"]), [])
            st = [r["l0_states"] for r in nr if r.get("l0_states") is not None]
            ac = [r["level1_actions"] if r["level1_actions"] is not None else r["budget"] for r in nr]
            same = (len(nr) == x["N_seeds"]
                    and sum(r["level1_actions"] is None for r in nr) == x["N_actions_censored"]
                    and (float(np.median(ac)) if ac else None) == x["N_actions"]
                    and (float(np.median(st)) if st else None) == x["N_states"])
            games_all += 1
            games_ok += same
            good &= same
        ok_lines += good
    return games_ok, games_all, ok_lines


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.4f}" if abs(v) < 1000 else f"{v:.1f}"
    return str(v)


def values(item, key):
    v = item[key]
    if len(v) <= LIST_MAX:
        return ", ".join(fmt(float(x)) for x in v)
    s = item[key + "_summary"]
    return f"n {s['n']}: min {fmt(s['min'])}, median {fmt(s['median'])}, max {fmt(s['max'])}"


def write_md(path, res, meta):
    L = []
    w = L.append
    w("# How the perfect separations of the oracle test arise (EXPLORATORY)")
    w("")
    w("**EXPLORATORY.** Written by scripts/oracle_sat.py from docs/oracle/oracle_v2.json and the study-1 rows. "
      "Nothing here is registered and nothing here is a claim.")
    w("")
    w("## Checks")
    w("")
    w("*EXPLORATORY.*")
    for k, v in meta.items():
        w(f"- {k}: {v}")
    w("")
    w("## Table 1. The pre-run number")
    w("")
    w("*EXPLORATORY.* AUROC of the three features known before any agent runs, each alone (a larger value "
      "predicts no completion) and together in oracle_v2's logistic model, in-sample and leave-one-game-out. "
      "\"constant\" names a feature with one value on every game of the line.")
    w("")
    hdr = ["suite", "condition", "subset", "agent", "n", "pos", "area", "actions", "colours", "B in-sample",
           "B leave-one-out", "constant"]
    w("| " + " | ".join(hdr) + " |")
    w("|" + "---|" * len(hdr))
    for r in res:
        p = r["pre_run"]
        w("| " + " | ".join([r["suite"], r["condition"], r["subset"], r["agent"], str(r["n"]), str(r["pos"]),
                             fmt(p["area"]), fmt(p["actions"]), fmt(p["colours"]), fmt(p["B_in_sample"]),
                             fmt(p["B_loo"]), ", ".join(p["constant"])]) + " |")
    w("")
    w("## Table 2. The censoring flag alone")
    w("")
    w("*EXPLORATORY.* A game is flagged when more than half of N's seeds (\"majority\") or at least one of N's "
      "seeds (\"any\") never ended level 1 within the 20,000-action budget. \"separates\" = the flagged games are "
      "exactly the non-completing games of the line's agent.")
    w("")
    hdr = ["suite", "condition", "subset", "agent", "n", "pos", "majority flagged", "majority separates",
           "majority AUROC", "any flagged", "any separates", "any AUROC"]
    w("| " + " | ".join(hdr) + " |")
    w("|" + "---|" * len(hdr))
    for r in res:
        m, a = r["censor_flag"]["majority"], r["censor_flag"]["any"]
        w("| " + " | ".join([r["suite"], r["condition"], r["subset"], r["agent"], str(r["n"]), str(r["pos"]),
                             str(m["flagged"]), fmt(m["separates"]), fmt(m["auroc"]), str(a["flagged"]),
                             fmt(a["separates"]), fmt(a["auroc"])]) + " |")
    w("")
    w("## Table 3. Every feature and model at AUROC 1.0000")
    w("")
    w("*EXPLORATORY.* Values of the completing and the non-completing games (every value up to 20 games, else "
      "a summary; all values in saturation.json). Features: raw values, a smaller value predicting completion. "
      "Models: fitted probabilities, a larger one predicting completion. Overlap: completing games inside the "
      "non-completing range / non-completing games inside the completing range. Gap: distance between the "
      "two ranges in the predicting direction (positive = no overlap). \"at budget\": non-completing games "
      "whose median N actions is the 20,000-action budget, i.e. the censoring value.")
    w("")
    hdr = ["suite", "condition", "subset", "agent", "item", "completing", "not completing", "overlap", "gap",
           "at budget"]
    w("| " + " | ".join(hdr) + " |")
    w("|" + "---|" * len(hdr))
    for r in res:
        for it in r["saturated"]:
            w("| " + " | ".join([r["suite"], r["condition"], r["subset"], r["agent"], it["name"],
                                 values(it, "complete"), values(it, "not_complete"),
                                 f"{it['pos_in_neg_range']} / {it['neg_in_pos_range']}", fmt(it["gap"]),
                                 "" if "not_complete_at_budget" not in it else
                                 f"{it['not_complete_at_budget']} of {it['not_complete_summary']['n']}"]) + " |")
    w("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="EXPLORATORY: how the oracle test's perfect separations arise")
    ap.add_argument("--old-repo", default=O.DEFAULT_OLD)
    ap.add_argument("--oracle-json", default=os.path.join(REPO, "docs", "oracle", "oracle_v2.json"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(REPO, "docs", "oracle"))
    ap.add_argument("--log", default=os.path.join(REPO, "logs", "oracle_sat.log"))
    args = ap.parse_args(argv)
    say = O.Tee(args.log)
    try:
        return _main(args, say)
    finally:
        say.f.close()


def _main(args, say):
    old = os.path.abspath(args.old_repo)
    say("oracle_sat -- EXPLORATORY: how the perfect separations of the oracle test arise")
    with open(args.oracle_json, encoding="utf-8") as f:
        lines = json.load(f)["lines"]
    say(f"oracle_v2.json: {len(lines)} lines")
    C, _ = O.load_old(old)
    truth = {"minigrid": C.parse_truth_minigrid(os.path.join(old, "docs", "GROUND_TRUTH_minigrid.md")),
             "procgen": C.parse_truth_procgen(os.path.join(old, "docs", "GROUND_TRUTH_procgen.md"))}
    conf = {s: set(C.confirmatory(s, truth[s])) for s in truth}
    rows, info = O.read_rows(old, conf)
    say(f"rows read: {info['files']} files, {len(rows)} confirmatory rows kept, {info['pilot_rows_skipped']} pilot rows skipped")
    g_ok, g_all, l_ok = check_consistency(rows, lines)
    say(f"consistency with oracle_v2.json (N medians and censored seeds): {g_ok} of {g_all} games agree on "
        f"{l_ok} of {len(lines)} lines")
    meta = {"oracle_v2.json lines": len(lines),
            "rows": f"{info['files']} files, {len(rows)} confirmatory rows kept, {info['pilot_rows_skipped']} pilot rows skipped",
            "consistency with oracle_v2.json": f"{g_ok} of {g_all} games agree on {l_ok} of {len(lines)} lines"}
    del rows

    if args.workers > 1:
        with Pool(args.workers, initializer=_init, initargs=(old,)) as pool:
            res = pool.map(line_job, lines, chunksize=1)
    else:
        res = [line_job(ln) for ln in lines]

    n_items = n_lines = n_flag = 0
    for r in res:
        p, cf = r["pre_run"], r["censor_flag"]
        say(f"line {r['suite']} {r['condition']} {r['subset']} {r['agent']} ({r['role']}): n={r['n']} pos={r['pos']}")
        say(f"  pre-run  area={fmt(p['area'])} actions={fmt(p['actions'])} colours={fmt(p['colours'])} | "
            f"B in-sample={fmt(p['B_in_sample'])} leave-one-out={fmt(p['B_loo'])}"
            + (f" (constant: {', '.join(p['constant'])})" if p["constant"] else ""))
        say(f"  censoring flag  majority: flagged {cf['majority']['flagged']}, separates {fmt(cf['majority']['separates'])}, "
            f"auroc={fmt(cf['majority']['auroc'])}; any: flagged {cf['any']['flagged']}, "
            f"separates {fmt(cf['any']['separates'])}, auroc={fmt(cf['any']['auroc'])}")
        if not r["saturated"]:
            say("  saturated  (none)")
        for it in r["saturated"]:
            cs, ns = it["complete_summary"], it["not_complete_summary"]
            extra = (f" at budget {it['not_complete_at_budget']}/{ns['n']}" if "not_complete_at_budget" in it else "")
            say(f"  {it['name']} auroc={fmt(it['auroc'])} complete n={cs['n']} [min {fmt(cs['min'])}, med {fmt(cs['median'])}, "
                f"max {fmt(cs['max'])}] not n={ns['n']} [min {fmt(ns['min'])}, med {fmt(ns['median'])}, max {fmt(ns['max'])}] "
                f"overlap {it['pos_in_neg_range']}/{it['neg_in_pos_range']} gap={fmt(it['gap'])}{extra}")
        n_items += len(r["saturated"])
        n_lines += bool(r["saturated"])
        n_flag += bool(r["saturated"]) and cf["majority"]["separates"]
    say(f"saturated items: {n_items} on {n_lines} lines; of them separated by the majority censoring flag alone: {n_flag} lines")
    meta["saturated items"] = f"{n_items} on {n_lines} lines; lines also separated by the majority censoring flag alone: {n_flag}"
    os.makedirs(args.out, exist_ok=True)
    md = os.path.join(args.out, "saturation.md")
    write_md(md, res, meta)
    js = os.path.join(args.out, "saturation.json")
    with open(js, "w", encoding="utf-8") as f:
        json.dump(dict(meta=dict(meta, label="EXPLORATORY", script="scripts/oracle_sat.py"), lines=res), f, indent=1)
    say(f"wrote {O.rel(md)}, {O.rel(js)}")
    return res


if __name__ == "__main__":
    main()
