"""
pilot_reading.py -- the reading of the GVGAI pilot search (campaign gvgai-pilot-search; docs/PREREG.md, Section 8,
decision 10).  The pilot games never enter a confirmatory analysis (PREREG Section 4): every line printed here is
labelled EXPLORATORY and is evidence about whether the claim can be tested, never evidence for it.  It decides
nothing and changes no registered file.

Reads only committed files:
    runs/gvgai-pilot-search/gvgaisearch/*.json   the pilot rows (horizon.search.v3): 20 units under the registered
                                                  (extended) key and 20 under the key of v0 (unit ids ending "-v0")
    jobs/manifest.json                            the pilot manifest as run (chunks, sessions, kernel versions)
    logs/engine_speed.log                         the laptop's expansions per second per level (amendment aa)
    logs/design_budget.log                        the registered budget of confirmatory search chunks
    runs/dev-minigrid-e/devsearch/*.json          stage E's development rows, for the void forms on development data
    D:\\Research\\arc3\\repo (read-only)           study 1's macro rows and truth table, through stage_e_diagnosis.load
Writes nothing but its console.

Definitions (those of scripts/stage_e_reading.py and docs/PREREG.md, Sections 6 and 7.4):
    win within C    the first win state was among the first C states seen (seen_at_first_win <= C)
    determined at C the search completed, or saw at least C states
    beyond C        determined at C without a win within C (tied, ranked last, in L_C)
    excluded at C   PREREG 7.4 rule 2: stopped by the time cap or the memory ceiling before seeing C states,
                    without completing and without a win seen
Sections:
  1  the rows; 2  per level (extended key); 3  per C, all 20 levels; 4  per C and game;
  5  speed: Kaggle against the laptop, and what it implies for the confirmatory levels at each C;
  6  the extended key against the key of v0, level by level and per C;
  7  the candidate forms of the L_C void threshold (PREREG 7.4, rule 5) on the pilot;
  8  the same forms on the development data of stage E.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\pilot_reading.py > logs\\pilot_reading.log
"""
from __future__ import annotations

import collections
import glob
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

TAG = "EXPLORATORY"
ROWS = os.path.join(REPO, "runs", "gvgai-pilot-search", "gvgaisearch")
E_ROWS = os.path.join(REPO, "runs", "dev-minigrid-e", "devsearch")
CEILINGS = (10_000, 100_000, 300_000, 1_000_000, 2_000_000)
TIME_CAP = 14_400.0
CHUNK_WORKER_SECONDS = 4 * 28_800          # docs/design/params_v0.json: 4 workers x 28,800 s of work
MIN_SECONDS_FOR_SPEED = 60.0               # levels that ran shorter are listed but not used for the ratio
SHARES_A = (0.10, 0.25, 0.50, 0.75)        # candidate X of form (a), shown, not adopted
GAMES_B = (5, 8, 13)                       # candidate G of form (b) out of 25 confirmatory games, shown, not adopted


def win_within(r, c):
    s = r["counts"]["seen_at_first_win"]
    return s is not None and s <= c


def determined(r, c):
    return r["complete"] or r["counts"]["states_seen"] >= c


def status_at(r, c):
    if win_within(r, c):
        return "win"
    if determined(r, c):
        return "beyond"
    return "excluded"


def stop_word(r):
    if r["complete"]:
        return "complete"
    return {"seen": "seen cap", "time": "time cap", "memory": "memory ceiling"}.get(r["cap_hit"], f"cap {r['cap_hit']}")


def pc(n, d):
    return f"{n} of {d} ({100.0 * n / d:.1f}%)" if d else f"{n} of 0"


def fmt(x):
    return "-" if x is None else f"{x:,}"


def read_pilot():
    ext, v0 = {}, {}
    for p in sorted(glob.glob(os.path.join(ROWS, "*.json"))):
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        k = (r["game"], int(r["level"]))
        (v0 if r["unit_id"].endswith("-v0") else ext)[k] = r
    return ext, v0


def laptop_speed():
    path = os.path.join(REPO, "logs", "engine_speed.log")
    out = {}
    pat = re.compile(r"^(\w+)\s+(\d)\s+\|\s+\d+\s+\|\s+\d+\s+\|\s+[\d.]+\s+\|\s+(\d+)\s+\|")
    with open(path, encoding="utf-8") as f:
        for ln in f:
            m = pat.match(ln)
            if m:
                out[(m.group(1), int(m.group(2)))] = int(m.group(3))
    return out


def budget_chunks():
    with open(os.path.join(REPO, "logs", "design_budget.log"), encoding="utf-8") as f:
        for ln in f:
            m = re.match(r"^confirmatory search: (\d+) units, .*?, (\d+) chunks at most", ln)
            if m:
                return int(m.group(1)), int(m.group(2))
    raise SystemExit("logs/design_budget.log: no confirmatory search line")


def main():
    import suite  # noqa: PLC0415
    print(f"pilot_reading -- {TAG}: the GVGAI pilot search (campaign gvgai-pilot-search); the pilot games are "
          f"excluded from every confirmatory analysis, so nothing here is evidence for the claim")
    ext, v0 = read_pilot()
    pilot_games = suite.pilot()
    want = {(g, l) for g in pilot_games for l in range(5)}

    # ---- 1. rows
    print(f"\n== 1. the rows ({TAG}) ==")
    allr = list(ext.values()) + list(v0.values())
    with open(os.path.join(REPO, "jobs", "manifest.json"), encoding="utf-8") as f:
        man = json.load(f)
    print(f"manifest campaign {man['campaign']}, code tag {man['code_tag']}, key form of the kind "
          f"{man['kinds']['gvgaisearch']['key_form']}, seen cap {man['kinds']['gvgaisearch']['seen_cap']:,}, time cap "
          f"{man['kinds']['gvgaisearch']['time_cap_seconds']:,} s, memory cap "
          f"{man['kinds']['gvgaisearch']['memory_cap_bytes']:,} bytes per worker, {man['kinds']['gvgaisearch']['workers']} workers")
    for ch in man["chunks"]:
        for s in ch["sessions"]:
            print(f"chunk {ch['chunk_id']}: status {ch['status']}, kernel version {s['kernel_version']}, outcome "
                  f"{s['outcome']}, ended {s['ended_at']}, units done {len(s['units_done_this_session'])}")
    print(f"rows {len(allr)}: extended key {len(ext)}, key of v0 {len(v0)}; schemas "
          f"{dict(collections.Counter(r['schema'] for r in allr))}; campaigns {sorted({r['campaign'] for r in allr})}")
    print(f"pilot games (scripts/suite.py): {', '.join(pilot_games)}; extended-key levels missing "
          f"{sorted(want - set(ext))}; v0 levels missing {sorted(want - set(v0))}")
    print(f"stopped by (extended): {dict(collections.Counter(stop_word(r) for r in ext.values()))}; "
          f"(v0): {dict(collections.Counter(stop_word(r) for r in v0.values()))}")
    print(f"sessions per row: {dict(collections.Counter(len(r['sessions']) for r in allr))}; images "
          f"{sorted({s['kaggle_env'].get('KAGGLE_DOCKER_IMAGE', '') for r in allr for s in r['sessions']})}")
    keys = sorted(want)

    # ---- 2. per level
    print(f"\n== 2. per level, registered (extended) key ({TAG}) ==")
    print("game          level | states seen | states expanded | stopped by | seen at first win | expanded at "
          "first win | solution length | seconds | deepest layer")
    for k in keys:
        r = ext[k]
        c = r["counts"]
        print(f"{k[0]:<13} {k[1]:>5} | {c['states_seen']:>11,} | {c['states_expanded']:>15,} | {stop_word(r):<10} | "
              f"{fmt(c['seen_at_first_win']):>17} | {fmt(c['expanded_at_first_win']):>21} | "
              f"{fmt(c['solution_length']):>15} | {r['seconds_spent']:>7.0f} | {c['depth_max']}")
    secs = [ext[k]["seconds_spent"] for k in keys]
    print(f"seconds: sum {sum(secs):,.0f}, largest {max(secs):,.0f}; levels with a win at any count: "
          f"{sum(ext[k]['counts']['seen_at_first_win'] is not None for k in keys)} of {len(keys)}")

    # ---- 3. per C
    print(f"\n== 3. per candidate ceiling, the 20 pilot levels, extended key ({TAG}) ==")
    print("C          | win within C | beyond C (of which: complete without a win / at or past C without a win) | "
          "excluded (PREREG 7.4 rule 2)")
    for c in CEILINGS:
        st = {k: status_at(ext[k], c) for k in keys}
        n_win = sum(v == "win" for v in st.values())
        bey = [k for k in keys if st[k] == "beyond"]
        n_comp = sum(ext[k]["complete"] for k in bey)
        n_exc = sum(v == "excluded" for v in st.values())
        print(f"{c:>10,} | {pc(n_win, 20):>14} | {pc(len(bey), 20)} ({n_comp} / {len(bey) - n_comp}) | {pc(n_exc, 20)}")

    # ---- 4. per C and game
    print(f"\n== 4. per candidate ceiling and game, extended key ({TAG}) ==")
    for g in pilot_games:
        parts = []
        for c in CEILINGS:
            st = [status_at(ext[(g, l)], c) for l in range(5)]
            parts.append(f"C {c:,}: win {st.count('win')}, beyond {st.count('beyond')}, excluded {st.count('excluded')}")
        print(f"{g:<13} " + "; ".join(parts))
    for c in CEILINGS:
        with_win = [g for g in pilot_games if any(win_within(ext[(g, l)], c) for l in range(5))]
        print(f"C {c:>9,}: games with at least one level with a win within C: {len(with_win)} of {len(pilot_games)} "
              f"({', '.join(with_win)})")

    # ---- 5. speed
    print(f"\n== 5. speed: Kaggle against the laptop ({TAG}) ==")
    lap = laptop_speed()
    print(f"laptop figures read from logs/engine_speed.log: {len(lap)} levels (a timed random walk of 1,500 "
          f"expansions per level, one process; restarts at 300 actions)")
    print("Kaggle: expansions per second = states expanded / seconds spent, over the whole search of the level, "
          "4 workers in one session")
    print("game          level | Kaggle expanded/s | Kaggle seen/s | laptop expanded/s | Kaggle / laptop | deepest layer | used")
    ratios = []
    for k in keys:
        r = ext[k]
        s = r["seconds_spent"]
        ke = r["counts"]["states_expanded"] / s if s > 0 else math.nan
        ks = r["counts"]["states_seen"] / s if s > 0 else math.nan
        ratio = ke / lap[k]
        used = s >= MIN_SECONDS_FOR_SPEED
        if used:
            ratios.append((ratio, k))
        print(f"{k[0]:<13} {k[1]:>5} | {ke:>17,.0f} | {ks:>13,.0f} | {lap[k]:>17,} | {ratio:>15.3f} | "
              f"{r['counts']['depth_max']:>13} | {'yes' if used else f'no, under {MIN_SECONDS_FOR_SPEED:.0f} s'}")
    rs = sorted(x for x, _ in ratios)
    med = statistics.median(rs)
    lo, lo_k = min(ratios)
    hi, hi_k = max(ratios)
    print(f"ratio Kaggle / laptop over the {len(rs)} levels that ran at least {MIN_SECONDS_FOR_SPEED:.0f} s: median "
          f"{med:.3f}, lowest {lo:.3f} ({lo_k[0]} {lo_k[1]}), highest {hi:.3f} ({hi_k[0]} {hi_k[1]})")
    for g in pilot_games:
        gr = [x for x, k in ratios if k[0] == g]
        if gr:
            print(f"  {g}: median {statistics.median(gr):.3f} over {len(gr)} levels")
    conf = [g for g in suite.confirmatory()]
    units, chunks = budget_chunks()
    print(f"registered budget (logs/design_budget.log): confirmatory search {units} units, {chunks} chunks at most "
          f"(each chunk {CHUNK_WORKER_SECONDS:,} worker-seconds, every unit charged at the time cap of {TIME_CAP:,.0f} s)")
    print("projection, per confirmatory level: Kaggle expansions/s taken as the laptop's times the ratio; time to see "
          "C states bounded above by C / (expansions/s), since a search expands at most as many states as it sees "
          "(the method of logs/engine_speed.log); a bound at or over the time cap means the search may stop by "
          "time before C and, without completing or a win, be excluded (PREREG 7.4 rule 2)")
    for label, games in (("confirmatory, 25 games after the fit rule", conf),
                         ("the 26 games of v0 (garbagecollector included), as in logs/engine_speed.log", sorted(conf + ["garbagecollector"]))):
        lv = [(g, l) for g in games for l in range(5)]
        print(f"  {label}: {len(lv)} levels")
        for rname, rv in (("median ratio", med), ("lowest ratio", lo)):
            for c in CEILINGS:
                b = [min(TIME_CAP, c / (lap[k] * rv)) for k in lv]
                at_cap = [k for k, x in zip(lv, b) if x >= TIME_CAP]
                tot = sum(b)
                lim = math.ceil(0.10 * len(lv))
                print(f"    {rname} {rv:.3f}, C {c:>9,}: bound reaches the time cap on {pc(len(at_cap), len(lv))}"
                      f" (more than 10% is more than {0.10 * len(lv):.1f}); sum {tot:,.0f} worker-seconds = "
                      f"{tot / CHUNK_WORKER_SECONDS:.2f} chunks of work against {chunks} budgeted"
                      + (f"; games at the cap: {', '.join(sorted({k[0] for k in at_cap}))}" if at_cap else "")
                      + ("" if len(at_cap) <= 0.10 * len(lv) else f"; at least {lim} would void every search quantity if all were excluded"))
        lim = math.floor(0.10 * len(lv)) + 1
        for c in CEILINGS:
            # a level's bound reaches the cap when ratio <= C / (time cap x laptop speed); the lim-th largest such
            # ratio is the speed at or below which more than 10% of the levels' bounds reach the cap
            thr = sorted((c / (TIME_CAP * lap[k]) for k in lv), reverse=True)[lim - 1]
            below = sum(x <= thr for x in rs)
            print(f"    C {c:>9,}: the bounds of more than 10% of the levels ({lim} or more) reach the time cap when Kaggle "
                  f"runs at a ratio of {thr:.3f} or less; pilot levels (of {len(rs)}) at or below that ratio: {below}")

    # ---- 6. extended key against v0
    print(f"\n== 6. the extended key against the key of v0, measured ({TAG}) ==")
    print("game          level | seen ext / v0 | expanded ext / v0 | stopped ext / v0 | first win seen ext / v0 | "
          "solution ext / v0 | seconds ext / v0 | counts equal")
    n_equal = 0
    for k in keys:
        a, b = ext[k], v0[k]
        ca, cb = a["counts"], b["counts"]
        same = all(ca[x] == cb[x] for x in ("states_seen", "states_expanded", "seen_at_first_win",
                                             "expanded_at_first_win", "solution_length")) and a["complete"] == b["complete"]
        n_equal += same
        print(f"{k[0]:<13} {k[1]:>5} | {ca['states_seen']:,} / {cb['states_seen']:,} | {ca['states_expanded']:,} / "
              f"{cb['states_expanded']:,} | {stop_word(a)} / {stop_word(b)} | {fmt(ca['seen_at_first_win'])} / "
              f"{fmt(cb['seen_at_first_win'])} | {fmt(ca['solution_length'])} / {fmt(cb['solution_length'])} | "
              f"{a['seconds_spent']:.0f} / {b['seconds_spent']:.0f} | {'yes' if same else 'no'}")
    print(f"levels with every count equal under both keys: {n_equal} of {len(keys)}")
    diff = [k for k in keys if not all(ext[k]["counts"][x] == v0[k]["counts"][x] for x in ("states_seen", "states_expanded"))]
    for k in diff:
        a, b = ext[k]["counts"], v0[k]["counts"]
        both_cap = not ext[k]["complete"] and not v0[k]["complete"]
        print(f"  {k[0]} {k[1]}: expanded {a['states_expanded']:,} against {b['states_expanded']:,} "
              f"({100.0 * (a['states_expanded'] - b['states_expanded']) / b['states_expanded']:+.2f}%), seen "
              f"{a['states_seen']:,} against {b['states_seen']:,}; "
              + ("both stopped at the seen cap, so R under either key is only known to be at least the cap"
                 if both_cap else "not both at the seen cap"))
    print("per C, levels with a win within C / beyond C / excluded, extended key against key of v0:")
    for c in CEILINGS:
        se = collections.Counter(status_at(ext[k], c) for k in keys)
        sv = collections.Counter(status_at(v0[k], c) for k in keys)
        print(f"  C {c:>9,}: extended {se['win']} / {se['beyond']} / {se['excluded']}; v0 {sv['win']} / "
              f"{sv['beyond']} / {sv['excluded']}")
    ts_e = sum(ext[k]["seconds_spent"] for k in keys)
    ts_v = sum(v0[k]["seconds_spent"] for k in keys)
    print(f"seconds over the 20 levels: extended {ts_e:,.0f}, v0 {ts_v:,.0f}, ratio {ts_e / ts_v:.3f}")

    # ---- 7. void forms on the pilot
    print(f"\n== 7. candidate forms of the L_C void threshold (PREREG 7.4 rule 5) on the pilot, extended key ({TAG}; "
          f"none adopted) ==")
    for c in CEILINGS:
        n_win = sum(win_within(ext[k], c) for k in keys)
        share = n_win / len(keys)
        a_txt = ", ".join(f"X {int(x * 100)}%: {'void' if share < x else 'not void'}" for x in SHARES_A)
        n_g = sum(any(win_within(ext[(g, l)], c) for l in range(5)) for g in pilot_games)
        gshare = n_g / len(pilot_games)
        b_txt = ", ".join(f"G {gg} of 25 ({100 * gg / 25:.0f}%): {'void' if gshare < gg / 25 else 'not void'}" for gg in GAMES_B)
        print(f"C {c:>9,}: (a) levels with a win {pc(n_win, len(keys))}; {a_txt}")
        print(f"             (b) games with a win {n_g} of {len(pilot_games)} ({100 * gshare:.0f}%); scaled to 25 games, {b_txt}")
    print("(c) pairs the score can order: needs the agents' outcomes on the pilot levels; no pilot agent row exists, "
          "so it cannot be computed here")

    # ---- 8. void forms on the development data
    print(f"\n== 8. the same forms on the development data of stage E ({TAG}; MiniGrid/BabyAI, one unit per (game, seed)) ==")
    import stage_e_diagnosis as D  # noqa: PLC0415
    erows = {}
    for p in sorted(glob.glob(os.path.join(E_ROWS, "*.json"))):
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        erows[(r["game"], int(r["level"]))] = r
    _, dgames, data = D.load(r"D:\Research\arc3\repo")
    egames = sorted({g for g, _ in erows})
    print(f"stage E rows {len(erows)}, games {len(egames)}")
    for c in CEILINGS:
        n_win = sum(win_within(r, c) for r in erows.values())
        n_exc = sum(status_at(r, c) == "excluded" for r in erows.values())
        share = n_win / len(erows)
        a_txt = ", ".join(f"X {int(x * 100)}%: {'void' if share < x else 'not void'}" for x in SHARES_A)
        gw = collections.defaultdict(bool)
        for (g, _), r in erows.items():
            gw[g] |= win_within(r, c)
        n_g = sum(gw.values())
        print(f"C {c:>9,}: (a) units with a win {pc(n_win, len(erows))}, excluded {n_exc}; {a_txt}")
        print(f"             (b) games with at least one unit with a win {pc(n_g, len(egames))}")
        for ag in D.AGENTS:
            rec = {k: v for k, v in data[ag].items() if k in erows}
            tot, tied = 0, 0
            bys = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0]))
            for k, v in rec.items():
                w = win_within(erows[k], c)
                cell = bys[v["S_M"]][k[0]]
                if v["y"]:
                    cell[0] += 1
                    cell[2] += not w
                else:
                    cell[1] += 1
                    cell[3] += not w
            for sm, per in bys.items():
                yc = sum(x[0] for x in per.values())
                nc = sum(x[1] for x in per.values())
                yb = sum(x[2] for x in per.values())
                nb = sum(x[3] for x in per.values())
                tot += yc * nc - sum(x[0] * x[1] for x in per.values())
                tied += yb * nb - sum(x[2] * x[3] for x in per.values())
            print(f"             (c) {ag}: eligible same-S_M between-game pairs {tot:,}; with at least one unit with a "
                  f"win, so not tied by censoring, {pc(tot - tied, tot)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
