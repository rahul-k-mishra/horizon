"""
Shared helpers for the registered analysis scripts (docs/PREREG.md v1, Section 11):
scripts/analyze_v1.py, scripts/analyze_v2.py, scripts/analyze_g.py.  Frozen at the prereg tag;
a crash fix is the only permitted change and is logged in PREREG.md's diff section.

Nothing here plays a game.  Input is run JSON (a list of rows, or {"rows": [...]}) in the schema of
PREREG.md Section 9, and the two ground-truth tables (docs/GROUND_TRUTH_minigrid.md,
docs/GROUND_TRUTH_procgen.md).
"""
from __future__ import annotations

import glob
import json
import os
import re

import numpy as np

HOLDS, FAILS, UNDET = "holds", "fails", "undetermined"
ASSUMPTIONS = ("A1", "A2", "A3", "A4", "A5")

# ---- registered sets (PREREG.md Sections 4 and 8)
PILOTS_B = ("MiniGrid-Empty-5x5-v0", "MiniGrid-FourRooms-v0", "MiniGrid-DoorKey-8x8-v0",
            "MiniGrid-Dynamic-Obstacles-6x6-v0", "MiniGrid-Fetch-5x5-N2-v0", "BabyAI-GoToRedBallGrey-v0")
PILOTS_C = ("coinrun", "bigfish")
IN_RANGE_C = ("bossfight", "chaser", "dodgeball", "heist", "leaper", "maze", "miner", "plunder", "starpilot")
# the confirmatory suite-C games whose frame depends on center_agent (PREREG v1.1 draft D13): the other
# nine (IN_RANGE_C) set center_agent false in their own game_reset, so center_on = center_off there.
# The secondary condition center_on is reported on these five only, never tested.
CAMERA_DISTINCT_C = ("caveflyer", "climber", "fruitbot", "jumper", "ninja")
ARC_TRAIN = ("tu93", "ls20", "vc33", "m0r0", "ft09", "lp85", "lf52", "dc22")

# V2 exclusions (docs/PREREG.md v1.1 draft, D9 and D9b; RKM 27 Sep 2026): confirmatory environments
# where success cannot be reached, on any seed, without an action absent from the agent's key map
# (D1; I1: ids 1-5 only, D7).  "Requires" is read as reachability (RKM, 27 Sep 2026 (f)): the action
# is either the success-triggering action or a precondition of every successful episode (a locked or
# closed door on every path to the target, or a carried key that must be put down before the target
# can be picked up; minigrid_env.py:562-563 picks up only with empty hands).  V2's primary line
# excludes them; the other lines report them included, not tested.
# -- no success exists at all, under any key map (D9 amendment of 27 Sep 2026 (g)): no goal is placed
#    and step() is not overridden (playground.py:16-31; GROUND_TRUTH_minigrid.md note 4)
_NO_SUCCESS = ("MiniGrid-Playground-v0",)
# -- the action is the success predicate itself or a precondition of it (docs/PREREG.md D9, D9b)
_DONE_ABSENT = ("MiniGrid-GoToDoor-5x5-v0", "MiniGrid-GoToDoor-6x6-v0", "MiniGrid-GoToDoor-8x8-v0",
                "MiniGrid-GoToObject-6x6-N2-v0", "MiniGrid-GoToObject-8x8-N2-v0")
_DROP_ABSENT = ("MiniGrid-PutNear-6x6-N2-v0", "MiniGrid-PutNear-8x8-N3-v0", "BabyAI-PutNextLocal-v0",
                "BabyAI-PutNextLocalS5N3-v0", "BabyAI-PutNextLocalS6N4-v0", "BabyAI-PutNextS4N1-v0",
                "BabyAI-PutNextS5N1-v0", "BabyAI-PutNextS5N2-v0", "BabyAI-PutNextS5N2Carrying-v0",
                "BabyAI-PutNextS6N3-v0", "BabyAI-PutNextS6N3Carrying-v0", "BabyAI-PutNextS7N4-v0",
                "BabyAI-PutNextS7N4Carrying-v0", "BabyAI-MoveTwoAcrossS5N2-v0", "BabyAI-MoveTwoAcrossS8N9-v0")
# drop as a precondition: the key used on the door is still carried when the target must be picked up
_DROP_PRECOND = ("MiniGrid-KeyCorridorS3R1-v0", "MiniGrid-KeyCorridorS3R2-v0", "MiniGrid-KeyCorridorS3R3-v0",
                 "MiniGrid-KeyCorridorS4R3-v0", "MiniGrid-KeyCorridorS5R3-v0", "MiniGrid-KeyCorridorS6R3-v0",
                 "MiniGrid-UnlockPickup-v0", "MiniGrid-BlockedUnlockPickup-v0",
                 "MiniGrid-ObstructedMaze-1Dl-v0", "MiniGrid-ObstructedMaze-1Dlh-v0", "MiniGrid-ObstructedMaze-1Dlhb-v0",
                 "MiniGrid-ObstructedMaze-1Q-v1", "MiniGrid-ObstructedMaze-2Dl-v0", "MiniGrid-ObstructedMaze-2Dlh-v0",
                 "MiniGrid-ObstructedMaze-2Dlhb-v1", "MiniGrid-ObstructedMaze-2Q-v1", "MiniGrid-ObstructedMaze-Full-v1",
                 "BabyAI-KeyCorridor-v0", "BabyAI-KeyCorridorS3R1-v0", "BabyAI-KeyCorridorS3R2-v0",
                 "BabyAI-KeyCorridorS3R3-v0", "BabyAI-KeyCorridorS4R3-v0", "BabyAI-KeyCorridorS5R3-v0",
                 "BabyAI-KeyCorridorS6R3-v0", "BabyAI-UnlockPickup-v0", "BabyAI-UnlockPickupDist-v0",
                 "BabyAI-BlockedUnlockPickup-v0", "BabyAI-UnlockToUnlock-v0")
# toggle required (D9b): toggle is the success action, or a locked/closed door stands on every path
_TOGGLE_PRED = ("MiniGrid-Unlock-v0", "MiniGrid-RedBlueDoors-6x6-v0", "MiniGrid-RedBlueDoors-8x8-v0",
                "BabyAI-Open-v0", "BabyAI-OpenDoor-v0", "BabyAI-OpenDoorColor-v0", "BabyAI-OpenDoorDebug-v0",
                "BabyAI-OpenDoorLoc-v0", "BabyAI-OpenDoorsOrderN2-v0", "BabyAI-OpenDoorsOrderN2Debug-v0",
                "BabyAI-OpenDoorsOrderN4-v0", "BabyAI-OpenDoorsOrderN4Debug-v0", "BabyAI-OpenRedBlueDoors-v0",
                "BabyAI-OpenRedBlueDoorsDebug-v0", "BabyAI-OpenRedDoor-v0", "BabyAI-OpenTwoDoors-v0",
                "BabyAI-Unlock-v0", "BabyAI-UnlockLocal-v0", "BabyAI-UnlockLocalDist-v0", "BabyAI-KeyInBox-v0")
_TOGGLE_PRECOND = ("MiniGrid-DoorKey-5x5-v0", "MiniGrid-DoorKey-6x6-v0", "MiniGrid-DoorKey-16x16-v0",
                   "MiniGrid-LockedRoom-v0", "MiniGrid-MultiRoom-N2-S4-v0", "MiniGrid-MultiRoom-N4-S5-v1",
                   "MiniGrid-MultiRoom-N6-v0", "BabyAI-GoToImpUnlock-v0", "BabyAI-PickupAbove-v0") + _DROP_PRECOND
V2_EXCLUDE = {
    ("minigrid", "raw"): _NO_SUCCESS + _DONE_ABSENT,                                  # 6
    ("minigrid", "macro"): _NO_SUCCESS + _DONE_ABSENT + _DROP_ABSENT + _DROP_PRECOND,  # 49
    # procgen: none
}
# I1 presses ids 1-5 only (D7, D9b): toggle absent in both suite-B conditions, special 2 absent on
# suite C.  No suite-C level end requires special 2 (D9b), so procgen has no I1 list.
V2_EXCLUDE_I1 = {
    ("minigrid", "raw"): V2_EXCLUDE[("minigrid", "raw")] + _TOGGLE_PRED + _TOGGLE_PRECOND,       # 63
    ("minigrid", "macro"): V2_EXCLUDE[("minigrid", "macro")] + _TOGGLE_PRED + tuple(
        g for g in _TOGGLE_PRECOND if g not in _DROP_PRECOND),                                     # 78
}


def v2_exclusions(suite, condition, agent):
    """The registered V2 exclusion list for one agent (D9 for R and N, D9 + D9b for I1)."""
    if agent == "I1" and (suite, condition) in V2_EXCLUDE_I1:
        return V2_EXCLUDE_I1[(suite, condition)]
    return V2_EXCLUDE.get((suite, condition), ())


# ---------------------------------------------------------------- input
def load_rows(patterns):
    rows = []
    for pat in patterns:
        for path in sorted(glob.glob(pat)):
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            rows.extend(d["rows"] if isinstance(d, dict) else d)
    return [normalise(r) for r in rows]


def _word(cell):
    """First verdict word in a markdown cell ("**holds (flagged)**" -> "holds")."""
    m = re.search(r"\b(holds|fails)\b", cell)
    return m.group(1) if m else None


def parse_truth_minigrid(path):
    """{env_id: {"A1","A2","A3-raw","A3-macro","A4","A5","status"}} from the suite-B table."""
    out = {}
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for line in lines:
        if not line.startswith("| MiniGrid-") and not line.startswith("| BabyAI-"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 11:
            continue                                   # the pilot-candidate table, not the truth table
        out[c[0]] = {"A1": _word(c[2]), "A2": _word(c[3]), "A3-raw": _word(c[4]), "A3-macro": _word(c[5]),
                     "A4": _word(c[6]), "A5": _word(c[7]), "status": c[10]}
    return out


def parse_truth_procgen(path):
    """{game: {"A1".."A5", "status"}} from the suite-C table."""
    out = {}
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for line in lines:
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) != 10 or not re.fullmatch(r"[a-z]+", c[0]) or c[0] == "game":
            continue
        out[c[0]] = {"A1": _word(c[1]), "A2": _word(c[2]), "A3": _word(c[3]), "A4": _word(c[4]),
                     "A5": _word(c[5]), "status": c[9]}
    return out


def truth_for(suite, condition, truth_row, assumption):
    if suite == "minigrid" and assumption == "A3":
        return truth_row["A3-raw" if condition == "raw" else "A3-macro"]
    return truth_row[assumption]


def confirmatory(suite, truth):
    """Registered confirmatory set: not excluded, not a chosen pilot (PREREG.md Section 8)."""
    pilots = PILOTS_B if suite == "minigrid" else PILOTS_C
    return sorted(g for g, t in truth.items() if not t["status"].startswith("excluded") and g not in pilots)


# ---------------------------------------------------------------- aggregation over seeds
def majority(verdicts):
    """holds if at least half the seeds say holds; else fails if at least half say fails; else
    undetermined (PREREG.md Section 5)."""
    n = len(verdicts)
    if n == 0:
        return UNDET
    if 2 * sum(v == HOLDS for v in verdicts) >= n:
        return HOLDS
    if 2 * sum(v == FAILS for v in verdicts) >= n:
        return FAILS
    return UNDET


MODEL_FAILS = ("mispredicted", "localise_failed")      # scripts/g_census_table.py:77


def census_from_report(nav):
    """The registered per-seed census (PREREG.md Section 5.3) from the G-NAV report of one run
    (scripts/g_nav.py NavHook.report): fields learn, counters, eff, walls, levels.
        A1 holds iff some key's learned shift is not None and the tried keys' shifts are not all equal
        A2 holds iff some key was decided "accepted" and counters.avatar_found == 1
        A3 holds iff A2 holds and the level-1 fallback is not in MODEL_FAILS
        A4 holds iff A3 holds and counters.wall_contradicted == 0 (corrected before the v1 tag: no
           learned-wall requirement, because a game whose only blocker is the world boundary has no
           wall colour to learn and its truth is A4 holds)
        A5 holds iff counters.goal_confirmed >= 1; fails iff counters.goal_reached_no_end >= 1 and
           goal_confirmed == 0; undetermined otherwise"""
    nav = nav or {}
    learn = nav.get("learn") or {}
    c = nav.get("counters") or {}
    levels = nav.get("levels") or [{}]
    shifts = [tuple(v["shift"]) if v.get("shift") else None for v in learn.values()]
    a1 = any(s is not None for s in shifts) and len(set(shifts)) >= 2
    a2 = any(v.get("decided") == "accepted" for v in learn.values()) and c.get("avatar_found", 0) == 1
    a3 = a2 and (levels[0] or {}).get("fallback") not in MODEL_FAILS
    a4 = a3 and c.get("wall_contradicted", 0) == 0
    gc, grne = c.get("goal_confirmed", 0), c.get("goal_reached_no_end", 0)
    a5 = HOLDS if gc >= 1 else (FAILS if grne >= 1 else UNDET)
    v = lambda b: HOLDS if b else FAILS  # noqa: E731
    return {"A1": v(a1), "A2": v(a2), "A3": v(a3), "A4": v(a4), "A5": a5}


def normalise(r):
    """ARC rows written by scripts/g_nav_run.py carry mode and nav but no suite/agent/census fields:
    suite "arc", condition "native", agent from mode (nav -> N, hash_state -> R), level1_completed from
    levels >= 1, census from the nav report.  Rows that already carry the fields are unchanged."""
    if "suite" not in r:
        r = dict(r, suite="arc", condition="native",
                 agent={"nav": "N", "hash_state": "R"}.get(r.get("mode"), r.get("mode")),
                 level1_completed=int(r.get("levels", 0) or 0) >= 1)
    if r.get("agent") == "N" and not r.get("census") and r.get("nav"):
        r = dict(r, census=census_from_report(r["nav"]))
    return r


def census_by_game(rows, suite, condition):
    """{game: {A1..A5: majority verdict}} from the N rows of one suite and condition."""
    per = {}
    for r in map(normalise, rows):
        if r.get("suite") != suite or r.get("condition") != condition or r.get("agent") != "N":
            continue
        if not r.get("census"):
            continue
        per.setdefault(r["game"], []).append(r["census"])
    return {g: {a: majority([c.get(a, UNDET) for c in cs]) for a in ASSUMPTIONS} for g, cs in per.items()}


# ---------------------------------------------------------------- V1 statistics
def agreement_kappa(truth, pred):
    """truth: list of holds/fails; pred: list of holds/fails/undetermined (same order).
    Agreement = share equal (undetermined never equals).  Cohen's kappa on the 2x2 table after
    mapping undetermined to the value opposite to the truth (the conservative reading), computed
    only if both truth values have at least 3 members (the constant-column rule); else None."""
    n = len(truth)
    if n == 0:
        return None, None
    agree = sum(t == p for t, p in zip(truth, pred)) / n
    n_h = sum(t == HOLDS for t in truth)
    if n_h < 3 or (n - n_h) < 3:
        return agree, None
    p2 = [p if p in (HOLDS, FAILS) else (FAILS if t == HOLDS else HOLDS) for t, p in zip(truth, pred)]
    po = sum(t == p for t, p in zip(truth, p2)) / n
    pt = n_h / n
    pp = sum(p == HOLDS for p in p2) / n
    pe = pt * pp + (1 - pt) * (1 - pp)
    if pe >= 1:
        return agree, None
    return agree, (po - pe) / (1 - pe)


def v1_verdict(agree, kappa):
    if agree is None:
        return "no data"
    if agree < 0.75:
        return "FAIL"
    if agree >= 0.90 and (kappa is None or kappa >= 0.70):
        return "PASS"
    return "neither"


# ---------------------------------------------------------------- V2 statistics
def auroc(scores, labels):
    """Mann-Whitney AUROC: P(score_pos > score_neg) + 0.5 P(equal).  None if one class is empty."""
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return None
    tot = 0.0
    for a in pos:
        for b in neg:
            tot += 1.0 if a > b else (0.5 if a == b else 0.0)
    return tot / (len(pos) * len(neg))


def balanced_accuracy(pred, labels):
    tp = sum(p and y for p, y in zip(pred, labels))
    fn = sum((not p) and y for p, y in zip(pred, labels))
    tn = sum((not p) and (not y) for p, y in zip(pred, labels))
    fp = sum(p and (not y) for p, y in zip(pred, labels))
    if tp + fn == 0 or tn + fp == 0:
        return None
    return 0.5 * (tp / (tp + fn) + tn / (tn + fp))


def logistic_fit_predict(X, y, ridge=1e-6, iters=100):
    """Nuisance baseline B (PREREG.md Section 10): logistic regression by Newton/IRLS with an L2 ridge
    of 1e-6 on the coefficients (not the intercept), on standardised features; constant features are
    dropped; with no feature left the prediction is the constant base rate.  In-sample predicted
    probabilities are returned."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = X.std(axis=0) > 0 if X.size else np.array([], dtype=bool)
    if X.size == 0 or not keep.any():
        return np.full(len(y), y.mean())
    Z = (X[:, keep] - X[:, keep].mean(0)) / X[:, keep].std(0)
    A = np.hstack([np.ones((len(y), 1)), Z])
    w = np.zeros(A.shape[1])
    R = ridge * np.eye(A.shape[1])
    R[0, 0] = 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-A @ w))
        g = A.T @ (p - y) + R @ w
        H = A.T @ (A * (p * (1 - p))[:, None]) + R
        step = np.linalg.solve(H + 1e-12 * np.eye(len(w)), g)
        w -= step
        if np.max(np.abs(step)) < 1e-10:
            break
    return 1 / (1 + np.exp(-A @ w))


def _boot_chunk(args):
    scores, labels, seed, n = args
    rng = np.random.default_rng(seed)
    m = len(scores)
    out = []
    for _ in range(n):
        idx = rng.integers(0, m, size=m)
        a = auroc([scores[i] for i in idx], [labels[i] for i in idx])
        if a is not None:
            out.append(a)
    return out


def bootstrap_auroc_ci(scores, labels, n_resamples=2000, seed=20260927, workers=8, chunks=8):
    """Percentile 95% CI of AUROC over games resampled with replacement.  Resamples with one class
    only are skipped and counted.  Deterministic: chunk k uses default_rng([seed, k])."""
    per = [n_resamples // chunks + (1 if k < n_resamples % chunks else 0) for k in range(chunks)]
    jobs = [(list(scores), list(labels), [seed, k], per[k]) for k in range(chunks)]
    if workers and workers > 1:
        from multiprocessing import Pool
        with Pool(min(workers, chunks)) as pool:
            parts = pool.map(_boot_chunk, jobs)
    else:
        parts = [_boot_chunk(j) for j in jobs]
    vals = sorted(v for p in parts for v in p)
    if not vals:
        return None, None, n_resamples
    lo = float(np.percentile(vals, 2.5))
    hi = float(np.percentile(vals, 97.5))
    return lo, hi, n_resamples - len(vals)


# ---------------------------------------------------------------- output
def lower_median(values):
    """Element at index floor((n-1)/2) of the sorted list; float('inf') sorts last."""
    if not values:
        return None
    s = sorted(values)
    return s[(len(s) - 1) // 2]


def write_table(out_dir, name, header, rows, meta):
    os.makedirs(out_dir, exist_ok=True)
    md = [f"# {name}", "", meta.get("note", ""), "",
          "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        md.append("| " + " | ".join("" if v is None else (f"{v:.4f}" if isinstance(v, float) else str(v)) for v in r) + " |")
    with open(os.path.join(out_dir, name + ".md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    with open(os.path.join(out_dir, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(dict(meta=meta, header=header, rows=rows), f, indent=1, default=str)
