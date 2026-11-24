"""
pilot_margins.py -- two readings asked for before the author fixes C and the L_C void threshold (docs/PREREG.md,
Section 6 and Section 7.4, rule 5; docs/DECISIONS_BEFORE_TAG.md, items 4a and 5a). EXPLORATORY throughout: the
pilot games are excluded from every confirmatory analysis, and nothing here is evidence for the claim or adopts a
value.

1. The margin of form (a). From the pilot's per-game shares of levels with a win within C (extended key, the
   registered state), how often a suite of 25 games drawn with replacement from the four pilot games, each game with
   all five of its levels, would have fewer than X% of its 125 levels with a win within C. Games are the clusters,
   as in the registered bootstrap (PREREG 7.3). Exact (every multinomial draw of 25 games from 4) and by 10,000
   resamples; then two checks of how much the answer rests on the four games: the pool with one game left out, and
   a two-level resample that redraws the pool of four before drawing the 25.

2. The cost of running the three evidence agents N, R and I1 on the 20 pilot levels under the registered
   conditions (PREREG Section 7.1: 20,000 actions per seed, seeds 1000 to 1009), as bounds from the session
   arithmetic of scripts/design_budget.py at each agent unit cap it shows; what the run would show on the pilot
   (which levels are beyond C, and in how many games); and, from the development data of stage E, how often the
   agents completed a unit that was beyond C against one with a win within C.

Reads only committed files: runs/gvgai-pilot-search/gvgaisearch, docs/design/params_v0.json, docs/truth/gvgai.json,
logs/engine_speed.log, runs/dev-minigrid-e/devsearch and, read-only through scripts/stage_e_diagnosis.py, study 1's
rows. Runs nothing. Console: logs/pilot_margins.log.
"""
from __future__ import annotations

import itertools
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import pilot_reading as PR  # noqa: E402 -- the pilot rows and the laptop's speed, unchanged
import stage_e_diagnosis as D  # noqa: E402 -- study 1's agent outcomes, unchanged
import stage_e_reading as SR  # noqa: E402 -- the stage E rows, unchanged
import suite  # noqa: E402

TAG = "EXPLORATORY"
CEILINGS = PR.CEILINGS
SHARES_X = (10, 25, 40, 50, 60)            # candidate X of form (a), per cent; shown, not adopted
N_GAMES = len(suite.confirmatory())        # 25
LEVELS = 5
RESAMPLES = 10_000
SEED = 20261124                            # this reading's seed; not a registered seed
EVIDENCE_AGENTS = ("N", "R", "I1")
TRUTH = os.path.join(REPO, "docs", "truth", "gvgai.json")
PRED = ("A1", "A2", "A3", "A4", "A5")


def below(wins, x):
    """fewer than x per cent of the levels with a win (form (a) voids L_C)."""
    return wins * 100 < x * N_GAMES * LEVELS


def exact_below(per_game, x):
    """P(fewer than x% of 125 levels with a win) when 25 games are drawn with replacement, equally likely, from
    the pool; every composition of 25 over the pool, weighted by its multinomial probability."""
    k = len(per_game)
    p = 0.0
    for comp in itertools.product(range(N_GAMES + 1), repeat=k - 1):
        last = N_GAMES - sum(comp)
        if last < 0:
            continue
        counts = comp + (last,)
        w = math.factorial(N_GAMES)
        for c in counts:
            w //= math.factorial(c)
        if below(sum(c * g for c, g in zip(counts, per_game)), x):
            p += w / k ** N_GAMES
    return p


def resample_below(per_game, rng, n=RESAMPLES, two_level=False):
    pool = np.array(per_game)
    out = {x: 0 for x in SHARES_X}
    for _ in range(n):
        p = pool[rng.integers(0, len(pool), len(pool))] if two_level else pool
        wins = int(p[rng.integers(0, len(p), N_GAMES)].sum())
        for x in SHARES_X:
            out[x] += below(wins, x)
    return {x: out[x] / n for x in SHARES_X}


def row(label, d):
    return f"  {label:<34}" + "".join(f"{100 * d[x]:>9.2f}" for x in SHARES_X)


def head():
    return f"  {'':<34}" + "".join(f"{'X=' + str(x) + '%':>9}" for x in SHARES_X)


def laptop_successors():
    pat = re.compile(r"^(\w+)\s+(\d)\s+\|\s+\d+\s+\|\s+\d+\s+\|\s+[\d.]+\s+\|\s+(\d+)\s+\|\s+(\d+)\s+\|")
    out = {}
    with open(os.path.join(REPO, "logs", "engine_speed.log"), encoding="utf-8") as f:
        for ln in f:
            m = pat.match(ln)
            if m:
                out[(m.group(1), int(m.group(2)))] = (int(m.group(3)), int(m.group(4)))
    return out


def main():
    print(f"pilot_margins -- {TAG}: the margin of form (a) and the cost of agents on the pilot levels; the pilot games "
          f"are excluded from every confirmatory analysis, so nothing here is evidence for the claim, and no value is "
          f"adopted")
    ext, _ = PR.read_pilot()
    games = sorted({g for g, _ in ext})
    assert len(ext) == len(games) * LEVELS == 20, len(ext)

    # ---- 1. per-game wins
    print(f"\n== 1. the pilot's levels with a win within C, per game, of {LEVELS} (extended key; {TAG}) ==")
    wins = {c: [sum(PR.win_within(ext[(g, lv)], c) for lv in range(LEVELS)) for g in games] for c in CEILINGS}
    print(f"  {'C':>10} | " + " | ".join(f"{g:>13}" for g in games) + " | pilot share")
    for c in CEILINGS:
        print(f"  {c:>10,} | " + " | ".join(f"{w:>13}" for w in wins[c]) + f" | {100 * sum(wins[c]) / 20:.1f}%")
    excl = sum(PR.status_at(r, c) == "excluded" for r in ext.values() for c in CEILINGS)
    print(f"  excluded under PREREG 7.4 rule 2 at any C: {excl}")

    # ---- 2. the margin of form (a)
    print(f"\n== 2. form (a): the share of suites of {N_GAMES} games drawn from the pilot's four that would have fewer "
          f"than X% of their {N_GAMES * LEVELS} levels with a win within C, per cent ({TAG}) ==")
    print(f"  games drawn with replacement, equally likely, each with all {LEVELS} of its levels (clusters as in PREREG "
          f"7.3); 'fewer than X%' is the wording of form (a); exact = every multinomial draw; resampled = {RESAMPLES:,} "
          f"draws, numpy default_rng([{SEED}, C])")
    for c in CEILINGS:
        print(f"\n  C = {c:,}; per-game wins {dict(zip(games, wins[c]))}; expected share {100 * sum(wins[c]) / 20:.1f}%")
        print(head())
        print(row("exact, pool of 4", {x: exact_below(wins[c], x) for x in SHARES_X}))
        rng = np.random.default_rng([SEED, c])
        print(row("resampled, pool of 4", resample_below(wins[c], rng)))
        for i, g in enumerate(games):
            pool = wins[c][:i] + wins[c][i + 1:]
            print(row(f"exact, {g} left out", {x: exact_below(pool, x) for x in SHARES_X}))
        rng = np.random.default_rng([SEED, c, 2])
        print(row("two-level: pool of 4 redrawn first", resample_below(wins[c], rng, two_level=True)))
    print(f"\n  the pool holds four games, so a suite drawn from it can only be made of copies of those four; the "
          f"resampling treats them as the whole population of GVGAI games and carries no uncertainty about what the "
          f"other {N_GAMES} games are like, except in the two checks above, which are themselves drawn from the four")

    # ---- 3. the pilot agents: cost
    p = json.load(open(os.path.join(REPO, "docs", "design", "params_v0.json"), encoding="utf-8"))
    s = p["session"]
    capacity = p["machine"]["workers"] * s["work_seconds"]
    per_session = s["startup_allowance_seconds"] + s["work_seconds"] + s["search_batch_seconds_max"] + \
        s["checkpoint_reserve_seconds"] + s["loop_gap_seconds_max"]
    seeds, actions = p["seeds"], p["actions_per_unit"]
    units = len(EVIDENCE_AGENTS) * len(ext) * seeds
    print(f"\n== 3. the three evidence agents on the 20 pilot levels under the registered conditions: cost, as bounds "
          f"({TAG}) ==")
    print(f"  units: {len(EVIDENCE_AGENTS)} agents ({', '.join(EVIDENCE_AGENTS)}) x {len(ext)} levels x {seeds} seeds = "
          f"{units}, {actions:,} actions each; a chunk holds {capacity} worker-seconds; one session with the loop's "
          f"largest gap at most {per_session} s")
    for cap in p["agent_unit_cap_seconds_shown"]:
        per = capacity // cap
        ch = math.ceil(units / per)
        print(f"  unit cap {cap:>5} s: {per:>4} units per chunk, {ch:>2} chunks (Kaggle sessions) at most, "
              f"{ch * per_session / 86400:.1f} days at most")
    reg = len(p["agents"]) * len(ext) * p["pilot"]["seeds"]
    per = capacity // p["agent_unit_cap_seconds_max"]
    print(f"  for comparison, the registered pilot agents of gate G1 (after the tag): {len(p['agents'])} agents x "
          f"{len(ext)} levels x {p['pilot']['seeds']} seeds = {reg} units, {math.ceil(reg / per)} chunks at most at "
          f"{p['agent_unit_cap_seconds_max']} s")
    lap = laptop_successors()
    ratios = []
    for (g, lv), r in ext.items():
        if r["seconds_spent"] >= PR.MIN_SECONDS_FOR_SPEED and (g, lv) in lap:
            ratios.append(r["counts"]["states_expanded"] / r["seconds_spent"] / lap[(g, lv)][0])
    ratios.sort()
    med, low = ratios[len(ratios) // 2] if len(ratios) % 2 else sum(ratios[len(ratios) // 2 - 1:len(ratios) // 2 + 1]) / 2, ratios[0]
    floor = {k: actions / (lap[k][1] * med) for k in ext if k in lap}
    floor_low = {k: actions / (lap[k][1] * low) for k in ext if k in lap}
    print(f"  engine time alone for {actions:,} actions (laptop successors/s of logs/engine_speed.log x Kaggle/laptop "
          f"ratio over {len(ratios)} pilot levels; the agents' own computation is not measured on GVGAI and is not in "
          f"this): at the median ratio {med:.3f}, {min(floor.values()):.0f} to {max(floor.values()):.0f} s per unit; at "
          f"the lowest ratio {low:.3f}, {min(floor_low.values()):.0f} to {max(floor_low.values()):.0f} s per unit")
    print(f"  not runnable now: the kind gvgaiagent has no pins, image probe or dry run (rule R8; docs/STATE.md, "
          f"amendment (ad), item 4), and no agent unit cap is fixed (gate G3 sets it from the pilot's times)")

    # ---- 4. what the run would show on the pilot
    with open(TRUTH, encoding="utf-8") as f:
        t = json.load(f)["games"]
    sm = {g: sum(t[g]["levels"]["0"][q]["verdict"] == "holds" for q in PRED) for g in games}
    print(f"\n== 4. what such a run could show on the pilot ({TAG}) ==")
    print(f"  S_M of the pilot games (docs/truth/gvgai.json, level 0): {sm}")
    shared = sorted(g for g in games if sum(sm[h] == sm[g] for h in games) > 1)
    print(f"  games that share S_M with another pilot game, so that their levels can enter a same-S_M between-game "
          f"pair of PREREG 7.2: {', '.join(shared) or 'none'}")
    for c in CEILINGS:
        beyond = sorted(k for k, r in ext.items() if PR.status_at(r, c) == "beyond")
        bg = sorted({g for g, _ in beyond})
        bs = [k for k in beyond if k[0] in shared]
        print(f"  C {c:>9,}: beyond C {len(beyond)} levels in {len(bg)} game(s) ({', '.join(f'{g} {lv}' for g, lv in beyond)}); "
              f"of them in a game that shares S_M: {len(bs)}")

    # ---- 5. the development data: are units beyond C the units the agents fail?
    print(f"\n== 5. development data of stage E (MiniGrid/BabyAI macro, one unit per (game, seed)): agents' completion "
          f"on units beyond C against units with a win within C ({TAG}) ==")
    rows = SR.read_rows(SR.E_ROWS)
    _, _, data = D.load(r"D:\Research\arc3\repo")
    for c in CEILINGS:
        parts = []
        for ag in EVIDENCE_AGENTS:
            recs = data[ag]
            bey = [k for k in recs if k in rows and PR.status_at(rows[k], c) == "beyond"]
            win = [k for k in recs if k in rows and PR.status_at(rows[k], c) == "win"]
            yb = sum(recs[k]["y"] for k in bey)
            yw = sum(recs[k]["y"] for k in win)
            gb = len({k[0] for k in bey})
            gyb = len({k[0] for k in bey if recs[k]["y"]})
            parts.append(f"{ag}: beyond C completed {PR.pc(yb, len(bey))} [{gyb} of {gb} games], win within C "
                         f"completed {PR.pc(yw, len(win))}")
        print(f"  C {c:>9,}: " + "; ".join(parts))
    print("  a unit beyond C that an agent completes ties, under L_C, with every uncompleted unit beyond C; a unit "
          "beyond C that the agent fails is ranked last, which is where a failed unit belongs, and costs nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
