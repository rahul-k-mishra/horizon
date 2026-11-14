"""
THE v2 ASSUMPTION CENSUS AS ONE TABLE: 25 games, one row each.  No game is run.

Reads the G-NAV v2 A/B runs already under runs/:
    runs/navrun_v2_heldout.json      17 held-out games, hash_state + nav, seeds 1000-1003, 20,000 actions
    runs/navrun_v2_train_quick.json   8 train games,    hash_state + nav, seeds 1000-1001,  3,000 actions
The train rows are 2 seeds at 3,000 actions: below the 4-seed minimum, labelled so in every output,
and replaced by E6 (10 seeds, 20,000 actions).  Source-informed games (tu93, dc22, ls20; sources
read 24 Sep 2026) are marked.

Writes runs/census_v2.json and docs/census_v2.md (the markdown is generated from the same numbers;
never edit it by hand).

COLUMNS (per game; "per seed" lists are in seed order)
    split, source-informed, seeds x actions
    keys tried        keyboard actions the planner's learn phase pressed (from nav.learn)
    keys accepted     per accepted key: step vector [dx, dy] and agreeing presses / presses; if a key
                      decided differently across seeds, every variant is listed
    category          by the rule below
    L1 nav / L1 hash  first-level outcome per seed: scorecard actions on level 1 if it was won
                      (card_levels[0], counted by the scorecard including resets), "-" if not
    L1 fallback       the planner's level-1 fallback per seed (why it stopped planning)
    goal recorded     nav counter goal_recorded per seed (a place recorded at a level end)
    goal_reached_no_end  per seed, summed over levels (the recorded place reached, no level end)
    goal_confirmed    per seed (the recorded place reached AND the level ended); a counter that
                      never fired is absent from the JSON and counted 0

CATEGORY RULE (from the nav arm's counters; applied in this order, first match wins)
    1 no keys                     the learn phase pressed no keyboard action in any seed
    2 no controllable object      keys tried, no key accepted in any seed
    3 key-controlled non-walker   a key accepted, and the level-1 fallback is "mispredicted" or
                                  "localise_failed" in at least half the seeds (the movement model
                                  fails during play)
    4 2-D lattice walker          the final effect model (nav.eff) has step vectors spanning two
                                  dimensions in at least half the seeds
    5 1-D walker                  otherwise
This rule was written on 25 Sep 2026 to codify the census already recorded in CLAUDE.md, after
that census had been read; it is not a pre-registered classifier.  The script prints every game
where the rule and CLAUDE.md disagree (sc25 was in no CLAUDE.md category).  E6 freezes the rule
(code hash) before its runs.  Rows 1-2 depend on the game as the planner sees it; rows 3-5 also
depend on the planner (its step learning and localisation).

No --workers: 168 rows are read and tabulated; there is no unit of work to parallelise.
Deterministic; outputs are written atomically and never overwritten without --force.

Command (PowerShell, from D:\\Research\\arc3\\repo):

    D:\\Research\\arc3\\brutus\\.venv\\Scripts\\python.exe scripts\\g_census_table.py

EXPECTED OUTPUT (shape):
    loaded 136 rows from runs\\navrun_v2_heldout.json, 32 from runs\\navrun_v2_train_quick.json
    per game: category, keys accepted, L1 nav / hash per seed, goal counters
    category counts, held-out: no keys 3, no controllable object 3, 2-D lattice walker 5,
        1-D walker 3, key-controlled non-walker 3            (sc25 lands in 1-D walker)
    CLAUDE.md agreement: 16 of 16 assigned games agree; sc25 not in CLAUDE.md
    held-out games with keyboard input 14, with an object the keys move 11,
        with goal_confirmed > 0 in any seed 0
    wrote runs\\census_v2.json, docs\\census_v2.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TRAIN = ["tu93", "ls20", "vc33", "m0r0", "ft09", "lp85", "lf52", "dc22"]
HELD_OUT = ["ar25", "bp35", "cd82", "cn04", "g50t", "ka59", "r11l", "re86", "s5i5",
            "sb26", "sc25", "sk48", "sp80", "su15", "tn36", "tr87", "wa30"]
SOURCE_INFORMED = ["tu93", "dc22", "ls20"]
CATEGORIES = ["no keys", "no controllable object", "2-D lattice walker", "1-D walker",
              "key-controlled non-walker"]
MODEL_FAILS = ("mispredicted", "localise_failed")
# the census as CLAUDE.md records it (held-out only), for the agreement check
CLAUDE_MD = {
    "no keys": ["r11l", "s5i5", "tn36"],
    "no controllable object": ["cd82", "sb26", "su15"],
    "2-D lattice walker": ["cn04", "ka59", "re86", "sp80", "g50t"],
    "1-D walker": ["bp35", "sk48"],
    "key-controlled non-walker": ["ar25", "wa30", "tr87"],
}


def rank2(vectors):
    """True if the step vectors span two dimensions."""
    vs = [v for v in vectors if v and (v[0] or v[1])]
    for i in range(len(vs)):
        for j in range(i + 1, len(vs)):
            if vs[i][0] * vs[j][1] - vs[i][1] * vs[j][0] != 0:
                return True
    return False


def l1_won(r):
    """Level 1 won, and the scorecard's action count for it.  Uses levels completed; stops if
    the card counts disagree with it."""
    won = int(r.get("levels", 0)) >= 1
    cl = r.get("card_levels") or []
    card_won = r.get("state") == "WIN" or (len(cl) > 1 and cl[1] > 0) or (
        len(cl) > 0 and cl[0] < int(r.get("actions", 0)))
    if won != card_won:
        sys.exit(f"STOP: {r['game']} {r['mode']} {r['seed']}: levels={r.get('levels')} but "
                 f"card_levels={cl[:3]} - the two counts disagree")
    return won, (cl[0] if won and cl else None)


def census_row(game, runs):
    nav = sorted([r for r in runs if r["mode"] == "nav"], key=lambda r: r["seed"])
    hs = sorted([r for r in runs if r["mode"] == "hash_state"], key=lambda r: r["seed"])
    seeds = [r["seed"] for r in nav]
    if [r["seed"] for r in hs] != seeds:
        sys.exit(f"STOP: {game}: nav seeds {seeds} and hash_state seeds "
                 f"{[r['seed'] for r in hs]} differ")
    budgets = sorted({int(r["actions"]) for r in nav + hs if r.get("state") != "WIN"})
    n = len(nav)

    learns = [(r.get("nav") or {}).get("learn") or {} for r in nav]
    keys_tried = sorted({k for L in learns for k in L}, key=int)
    per_key = defaultdict(list)
    for L in learns:
        for k, v in L.items():
            per_key[k].append((v.get("decided"), v.get("shift"), v.get("agree"), v.get("presses")))
    keys_accepted = {}
    keys_other = {}
    for k in keys_tried:
        variants = []
        for d in per_key[k]:
            if d not in variants:
                variants.append(d)
        entry = [dict(decided=d, shift=s, agree=a, presses=p, seeds=per_key[k].count((d, s, a, p)))
                 for d, s, a, p in variants]
        (keys_accepted if any(v["decided"] == "accepted" for v in entry) else keys_other)[k] = entry

    fallbacks = [((r.get("nav") or {}).get("levels") or [{}])[0].get("fallback") for r in nav]
    effs = [(r.get("nav") or {}).get("eff") or {} for r in nav]
    counters = [(r.get("nav") or {}).get("counters") or {} for r in nav]

    if not keys_tried:
        cat = "no keys"
    elif not keys_accepted:
        cat = "no controllable object"
    elif sum(f in MODEL_FAILS for f in fallbacks) * 2 >= n:
        cat = "key-controlled non-walker"
    elif sum(rank2(list(e.values())) for e in effs) * 2 >= n:
        cat = "2-D lattice walker"
    else:
        cat = "1-D walker"

    l1n = [l1_won(r) for r in nav]
    l1h = [l1_won(r) for r in hs]
    return dict(
        game=game, split="train" if game in TRAIN else "held-out",
        source_informed=game in SOURCE_INFORMED, seeds=seeds, actions=budgets,
        below_minimum_seeds=n < 4,
        keys_tried=keys_tried, keys_accepted=keys_accepted, keys_not_accepted=keys_other,
        category=cat,
        eff_per_seed=effs,
        l1_fallback=fallbacks,
        l1_nav=[a if w else None for w, a in l1n],
        l1_hash_state=[a if w else None for w, a in l1h],
        l1_nav_won=sum(w for w, _ in l1n), l1_hash_state_won=sum(w for w, _ in l1h),
        goal_recorded=[c.get("goal_recorded", 0) for c in counters],
        goal_reached_no_end=[sum(L.get("goal_reached_no_end", 0)
                                 for L in ((r.get("nav") or {}).get("levels") or [])) for r in nav],
        goal_confirmed=[c.get("goal_confirmed", 0) for c in counters],
        avatar_found=[c.get("avatar_found", 0) for c in counters],
    )


def fmt_keys(acc):
    parts = []
    for k, entry in acc.items():
        for v in entry:
            s = f"{k}: {v['shift']} {v['agree']}/{v['presses']}"
            if v["decided"] != "accepted":
                s += f" {v['decided']}"
            if len(entry) > 1:
                s += f" ({v['seeds']} seeds)"
            parts.append(s)
    return "; ".join(parts) or "-"


def fmt_l1(xs):
    return " ".join("-" if x is None else str(x) for x in xs)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--heldout", default=os.path.join(REPO, "runs", "navrun_v2_heldout.json"))
    ap.add_argument("--train", default=os.path.join(REPO, "runs", "navrun_v2_train_quick.json"))
    ap.add_argument("--out", default=os.path.join(REPO, "runs", "census_v2.json"))
    ap.add_argument("--md", default=os.path.join(REPO, "docs", "census_v2.md"))
    ap.add_argument("--force", action="store_true", help="overwrite existing outputs")
    args = ap.parse_args()
    for p in (args.out, args.md):
        if os.path.exists(p) and not args.force:
            sys.exit(f"{p} exists; not overwritten without --force")

    ho, tr = json.load(open(args.heldout)), json.load(open(args.train))
    print(f"loaded {len(ho)} rows from {args.heldout}, {len(tr)} from {args.train}")
    by = defaultdict(list)
    for r in ho + tr:
        by[r["game"]].append(r)
    if sorted(by) != sorted(TRAIN + HELD_OUT):
        sys.exit(f"STOP: games {sorted(by)} are not the 25 public games")
    for g in HELD_OUT:
        if any(r not in ho for r in by[g]):
            sys.exit(f"STOP: held-out game {g} has rows in the train file")

    rows = [census_row(g, by[g]) for g in HELD_OUT + TRAIN]

    print(f"\n{'game':5} {'split':8} {'category':26} {'L1 nav':>22} {'L1 hash':>22} {'goal rec':>9} "
          f"{'grne':>9} {'conf':>8}  keys accepted")
    for r in rows:
        tag = ("*" if r["source_informed"] else " ")
        print(f"{r['game']:4}{tag} {r['split']:8} {r['category']:26} {fmt_l1(r['l1_nav']):>22} "
              f"{fmt_l1(r['l1_hash_state']):>22} {' '.join(map(str, r['goal_recorded'])):>9} "
              f"{' '.join(map(str, r['goal_reached_no_end'])):>9} "
              f"{' '.join(map(str, r['goal_confirmed'])):>8}  {fmt_keys(r['keys_accepted'])}")

    hrows = [r for r in rows if r["split"] == "held-out"]
    counts = Counter(r["category"] for r in hrows)
    print("\ncategory counts, held-out: " + ", ".join(f"{c} {counts[c]}" for c in CATEGORIES))
    tcounts = Counter(r["category"] for r in rows if r["split"] == "train")
    print("category counts, train (2 seeds x 3,000 actions): "
          + ", ".join(f"{c} {tcounts[c]}" for c in CATEGORIES))

    claude = {g: c for c, gs in CLAUDE_MD.items() for g in gs}
    agree = [r["game"] for r in hrows if claude.get(r["game"]) == r["category"]]
    differ = [(r["game"], claude[r["game"]], r["category"]) for r in hrows
              if r["game"] in claude and claude[r["game"]] != r["category"]]
    unassigned = [(r["game"], r["category"]) for r in hrows if r["game"] not in claude]
    print(f"CLAUDE.md agreement: {len(agree)} of {len(claude)} assigned games agree"
          + ("".join(f"; DIFFERS {g}: CLAUDE.md {a}, rule {b}" for g, a, b in differ))
          + "".join(f"; {g} not in CLAUDE.md, rule gives {c}" for g, c in unassigned))

    keyboard = [r for r in hrows if r["category"] != "no keys"]
    moved = [r for r in keyboard if r["category"] != "no controllable object"]
    confirmed = [r["game"] for r in hrows if any(r["goal_confirmed"])]
    grne = [r["game"] for r in hrows if any(r["goal_reached_no_end"])]
    recorded = [r["game"] for r in hrows if any(r["goal_recorded"])]
    summary = dict(heldout_category_counts={c: counts[c] for c in CATEGORIES},
                   train_category_counts={c: tcounts[c] for c in CATEGORIES},
                   heldout_keyboard=len(keyboard), heldout_object_moved_by_keys=len(moved),
                   heldout_goal_confirmed_any_seed=confirmed,
                   heldout_goal_recorded_any_seed=recorded,
                   heldout_goal_reached_no_end_any_seed=grne,
                   heldout_l1_won_by_nav_any_seed=[r["game"] for r in moved if r["l1_nav_won"]],
                   claude_md_agree=agree, claude_md_differ=differ, claude_md_unassigned=unassigned)
    print(f"held-out games with keyboard input {len(keyboard)}, with an object the keys move "
          f"{len(moved)}, with goal_confirmed > 0 in any seed {len(confirmed)}")
    print(f"  of the {len(moved)}: goal recorded in some seed {recorded}; recorded place reached "
          f"without a level end {grne}; level 1 won by nav in some seed "
          f"{summary['heldout_l1_won_by_nav_any_seed']}")

    out = dict(script="scripts/g_census_table.py", created=time.strftime("%Y-%m-%d %H:%M:%S"),
               inputs=[os.path.basename(args.heldout), os.path.basename(args.train)],
               rule=__doc__.split("CATEGORY RULE")[1].split("No --workers")[0].strip(),
               summary=summary, rows=rows)
    for path, text in ((args.out, json.dumps(out, indent=1)), (args.md, markdown(rows, summary))):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    print(f"\nwrote {args.out}, {args.md}")


def markdown(rows, s):
    L = ["# Census v2: 25 public games, one row per game",
         "",
         "Generated by scripts/g_census_table.py from runs/navrun_v2_heldout.json (17 held-out "
         "games, 4 seeds, 20,000 actions) and runs/navrun_v2_train_quick.json (8 train games, "
         "**2 seeds, 3,000 actions: below the 4-seed minimum, not a result; E6 replaces them**). "
         "Do not edit by hand; rerun the script.",
         "",
         "\\* source-informed (sources of tu93, dc22, ls20 read on 24 Sep 2026). "
         "L1 columns: scorecard actions on level 1 per seed when it was won, - when not. "
         "Goal columns are nav counters per seed. Keys accepted: key: [dx, dy] agreeing presses/"
         "presses.",
         "",
         "Category rule (first match): no keys (learn phase pressed no key); no controllable "
         "object (no key accepted); key-controlled non-walker (a key accepted and the level-1 "
         "fallback is mispredicted/localise_failed in at least half the seeds); 2-D lattice "
         "walker (final effect model spans two dimensions in at least half the seeds); 1-D walker "
         "(otherwise). The rule codifies the census already in CLAUDE.md and was written after "
         "reading it; it is not pre-registered. The first two categories depend on the game as "
         "the planner sees it; the last three also depend on the planner.",
         "",
         "| game | split | source-informed | seeds x actions | keys tried | keys accepted | category "
         "| L1 fallback | L1 nav | L1 hash_state | goal recorded | goal_reached_no_end "
         "| goal_confirmed |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append("| " + " | ".join([
            r["game"] + ("\\*" if r["source_informed"] else ""),
            r["split"], "yes" if r["source_informed"] else "no",
            f"{len(r['seeds'])} x {'/'.join(map(str, r['actions']))}",
            " ".join(r["keys_tried"]) or "-",
            fmt_keys(r["keys_accepted"]).replace("|", "/"),
            r["category"],
            " ".join(str(f) for f in r["l1_fallback"]),
            fmt_l1(r["l1_nav"]), fmt_l1(r["l1_hash_state"]),
            " ".join(map(str, r["goal_recorded"])),
            " ".join(map(str, r["goal_reached_no_end"])),
            " ".join(map(str, r["goal_confirmed"]))]) + " |")
    c = s["heldout_category_counts"]
    L += ["",
          "## Held-out summary (17 games, 4 seeds)",
          "",
          "- Categories: " + ", ".join(f"{k} {v}" for k, v in c.items()) + ".",
          f"- {s['heldout_keyboard']} of 17 have keyboard input; {s['heldout_object_moved_by_keys']} "
          f"have an object the keys move.",
          f"- goal_confirmed (recorded place reached and the level ended) is 0 in every seed of "
          f"every held-out game." if not s["heldout_goal_confirmed_any_seed"] else
          f"- goal_confirmed > 0 in some seed: {', '.join(s['heldout_goal_confirmed_any_seed'])}.",
          f"- A goal place was recorded in some seed on: "
          f"{', '.join(s['heldout_goal_recorded_any_seed']) or 'none'}; the recorded place was reached "
          f"again without a level end on: {', '.join(s['heldout_goal_reached_no_end_any_seed']) or 'none'}.",
          f"- Level 1 was won by nav in some seed on: "
          f"{', '.join(s['heldout_l1_won_by_nav_any_seed']) or 'none'} (among games with a moved "
          f"object). These counters do not say how those first levels ended; they say only that no "
          f"recorded place was later confirmed as a goal.",
          "- CLAUDE.md agreement: " + (f"{len(s['claude_md_agree'])} of "
                                       f"{len(s['claude_md_agree']) + len(s['claude_md_differ'])} "
                                       f"assigned games agree")
          + "".join(f"; differs on {g} (CLAUDE.md {a}, rule {b})" for g, a, b in s["claude_md_differ"])
          + "".join(f"; {g} was in no CLAUDE.md category, the rule gives {cat}"
                    for g, cat in s["claude_md_unassigned"]) + ".",
          ""]
    sc = next(r for r in rows if r["game"] == "sc25")
    L += [f"sc25 note: only key(s) {', '.join(k for k, e in sc['keys_accepted'].items() if any(v['decided'] == 'accepted' for v in e))} "
          f"passed the agreeing-presses test; its category comes from the final effect model "
          f"(seed {sc['seeds'][0]}: {sc['eff_per_seed'][0]}), which the planner filled during play. "
          f"Treat the row as weak.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
