"""
Synthetic test of scripts/oracle_v2.py.  Reads no study-1 row and no study-1 truth table.

It builds a fake study-1 repository in a temporary folder: the two study-1 analysis files are copied
there unchanged (from --old-repo, read only), and fabricated truth tables, rows and a docs/tables/v2.json
are written beside them.  The fake v2.json is made by study 1's own analyze_v2.v2_rows on the fabricated
rows, so the reproduction check must report every line identical.

Fabricated data, worked by hand:
    minigrid: 12 games MiniGrid-Fake01-v0 .. Fake12-v0.  Truth: A1, A2, A3-macro, A4 hold on all; A3-raw
        fails on all; A5 holds on Fake01-06 and fails on Fake07-12.  Under macro the oracle S is 5 on
        Fake01-06 and 4 on Fake07-12; under raw it is 4 and 3.
        Agent R completes level 1 on every seed of Fake01-06 and on no seed of Fake07-12, so Y = A5 and
        the oracle AUROC is 1.0000 on R's "all games" line in both conditions.  P (A2-A5 hold) is true
        on Fake01-06 under macro, so its balanced accuracy is 1.0000 there; under raw A3 fails
        everywhere, P is false everywhere, and study 1's balanced accuracy is 0.5 * (0/6 + 6/6) = 0.5000.
        N states: 10 * (game index) on every seed, so smaller index = smaller search; with Y = (index
        <= 6) the N-states AUROC is 1.0000.
    procgen: 12 games (all confirmatory names except caveflyer and ninja).  Truth A5 holds on the first
        six in alphabetical order; R completes there.  Oracle AUROC 1.0000 on R's "all" line.
Expected: exit code 0 and "OK" on the last line.

Command (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\test_oracle_v2.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OLD = r"D:\Research\arc3\repo"

MG = [f"MiniGrid-Fake{i:02d}-v0" for i in range(1, 13)]
PG = ["bossfight", "chaser", "climber", "dodgeball", "fruitbot", "heist", "jumper", "leaper", "maze",
      "miner", "plunder", "starpilot"]
SEEDS = range(1000, 1004)


def write_truth(d):
    lines = ["# fake", "", "| id | src | A1 | A2 | A3-raw | A3-macro | A4 | A5 | pred | codes | status |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, g in enumerate(MG):
        a5 = "holds" if i < 6 else "fails"
        lines.append(f"| {g} | x | holds | holds (agent) | fails | holds | holds | {a5} | p | c | confirmatory |")
    with open(os.path.join(d, "GROUND_TRUTH_minigrid.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    lines = ["# fake", "", "| game | A1 | A2 | A3 | A4 | A5 | pred | actions | notes | status |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for i, g in enumerate(sorted(PG)):
        a5 = "holds" if i < 6 else "fails"
        lines.append(f"| {g} | holds | holds | fails | holds | {a5} | p | a | n | confirmatory |")
    with open(os.path.join(d, "GROUND_TRUTH_procgen.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def row(suite, cond, mode, game, seed, won, idx):
    agent = {"hash_state": "R", "nav": "N", "i1": "I1"}[mode]
    r = dict(game=game, mode=mode, seed=seed, suite=suite, condition=cond, agent=agent, actions=20000,
             budget=20000, levels=1 if won else 0, level1_completed=won,
             level1_actions=100 * idx if won else None,
             adapter=dict(grid=[5 + idx % 3, 5 + idx % 3], action_list=["a"] * 6, n_colours=8 + seed % 3),
             level_log=[dict(level=0, actions=100 * idx, states=10 * idx, ended="won" if won else "NOT_FINISHED")])
    if agent == "N":
        r["census"] = {"A1": "holds", "A2": "holds", "A3": "holds" if seed % 2 else "fails",
                       "A4": "holds" if idx % 2 else "fails", "A5": "undetermined"}
    return r


def build(root):
    os.makedirs(os.path.join(root, "scripts"))
    os.makedirs(os.path.join(root, "docs", "tables"))
    for name in ("analyze_common.py", "analyze_v2.py"):
        shutil.copyfile(os.path.join(OLD, "scripts", name), os.path.join(root, "scripts", name))
    write_truth(os.path.join(root, "docs"))
    all_rows = []
    for suite, cond, games in (("minigrid", "raw", MG), ("minigrid", "macro", MG),
                               ("procgen", "center_off", sorted(PG))):
        for mode in ("hash_state", "nav", "i1"):
            d = os.path.join(root, "runs", "suites", suite, cond, mode)
            os.makedirs(d)
            for i, g in enumerate(games, start=1):
                for s in SEEDS:
                    won = (i <= 6) if mode == "hash_state" else ((i + s) % 3 == 0)
                    r = row(suite, cond, mode, g, s, won, i)
                    all_rows.append(r)
                    with open(os.path.join(d, f"{g}__{s}.json"), "w", encoding="utf-8") as f:
                        json.dump([r], f)
    return all_rows


def main():
    import oracle_v2 as O
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "old")
        all_rows = build(root)
        C, V2 = O.load_old(root)
        truth = {"minigrid": C.parse_truth_minigrid(os.path.join(root, "docs", "GROUND_TRUTH_minigrid.md")),
                 "procgen": C.parse_truth_procgen(os.path.join(root, "docs", "GROUND_TRUTH_procgen.md"))}
        table, _ = V2.v2_rows([C.normalise(r) for r in all_rows], truth, 200, 20260927, 1)
        with open(os.path.join(root, "docs", "tables", "v2.json"), "w", encoding="utf-8") as f:
            json.dump(dict(meta={}, header=[], rows=table), f)
        out = os.path.join(tmp, "out")
        res = O.main(["--old-repo", root, "--workers", "2", "--resamples", "200", "--out", out,
                      "--log", os.path.join(tmp, "log.txt")])
        by = {(r["suite"], r["condition"], r["subset"], r["agent"]): r for r in res}
        fails = []

        def check(cond, msg):
            if not cond:
                fails.append(msg)
        check(len(res) == 7 + 7 + 6, f"line count {len(res)} != 20")
        check(all(r["v2json_same"] for r in res), "a census line differs from the fake v2.json")
        check(all(r["loop_reproduces"] for r in res), "the bootstrap loop does not reproduce v2_stats")
        check(all(r["baseline_refit_reproduces"] for r in res), "the logistic refit does not reproduce B")
        for cond in ("macro", "raw"):
            r = by[("minigrid", cond, "all games", "R")]
            check(r["oracle"]["auroc"] == 1.0, f"minigrid {cond} R oracle auroc {r['oracle']['auroc']}")
            check(r["search"]["N_states"]["auroc"] == 1.0, f"minigrid {cond} R N_states {r['search']['N_states']['auroc']}")
        check(by[("minigrid", "macro", "all games", "R")]["oracle"]["ba"] == 1.0, "macro BA")
        check(by[("minigrid", "raw", "all games", "R")]["oracle"]["ba"] == 0.5, "raw BA should be 0.5")
        check(by[("procgen", "center_off", "all", "R")]["oracle"]["auroc"] == 1.0, "procgen R oracle auroc")
        shape = {k: v for k, v in json.load(open(os.path.join(out, "oracle_v2.json")))["meta"]["oracle_shape"].items()}
        check(shape["minigrid macro"]["S"] == {"4": 6, "5": 6}, f"macro shape {shape['minigrid macro']}")
        for name in ("oracle_v2.md", "oracle_v2.json", "fig_oracle_vs_census.png", "fig_search_features.png"):
            check(os.path.exists(os.path.join(out, name)), f"missing {name}")
        md = open(os.path.join(out, "oracle_v2.md"), encoding="utf-8").read()
        check(md.count("*EXPLORATORY.*") >= 6, "an md section lacks its EXPLORATORY label")
        check(not os.path.exists(os.path.join(root, "scripts", "__pycache__")), "bytecode was written")
    for m in fails:
        print("FAIL:", m)
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
