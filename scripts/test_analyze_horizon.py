"""
test_analyze_horizon.py -- synthetic tests of scripts/analyze_horizon.py.  No confirmatory row exists; every
row here is made up in memory.  The only committed files read are docs/PREREG.md (the ceiling, still open) and
docs/design/dev_reading.json (the supplement), both read-only.

Hand-worked AUROC (part 1).  Four games, scores and outcomes:
    g1 (S_M 3): 3 completed, 1 not        g2 (S_M 3): 2 not, 1 completed
    g3 (S_M 4): 5 completed               g4 (S_M 4): 0 not
  Same S_M, different games: (g1 3, g2 2) = 1; (g2 1, g1 1) = 1/2 (a tie); (g3 5, g4 0) = 1.  3 pairs, U = 2.5,
  AUROC 0.833333.
  All between-game pairs: g1's 3 beats g2's 2 and g4's 0 (2); g2's 1 ties g1's 1 and beats g4's 0 (1.5); g3's 5
  beats g1's 1, g2's 2 and g4's 0 (3).  7 pairs, U = 6.5, AUROC 0.928571.
Censored scores (part 2), C = 1,000:
    complete, R 600, win at seen 100, L 7        L_C -7,   H_C -log10 600
    seen cap 2,000, first win at seen 500, L 9   L_C -9;   with C = 400: beyond C (INF), H_C -log10 400
    time cap at seen 300, no win                 L_C, H_C, b missing (excluded)
    time cap at seen 300, win at seen 100, L 4   L_C -4;   H_C, b missing
    complete, R 50, no win                       L_C beyond C (INF), H_C -log10 50
Part 4 also records, for the author, that under the drafted rules a ceiling beyond which every level lies gives
AUROC_L 0.5, "not shown", not void.  Part 5 checks the refusals: any campaign but the confirmatory one, and any run
before the annotated tag prereg-v1 holds this script.
Run: D:\\Research\\horizon\\.venv\\Scripts\\python.exe -W error scripts\\test_analyze_horizon.py > logs\\test_analyze_horizon.log
"""
import itertools
import json
import math
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import analyze_horizon as A  # noqa: E402

FAILS = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        FAILS.append(what)


def close(a, b, tol=1e-9):
    return a is not None and b is not None and abs(a - b) <= tol


def brute(score, y, game, stratum):
    u = n = 0.0
    for i, j in itertools.product(range(len(score)), repeat=2):
        if y[i] and not y[j] and game[i] != game[j] and stratum[i] == stratum[j] \
                and not math.isnan(score[i]) and not math.isnan(score[j]):
            n += 1
            u += 1.0 if score[i] > score[j] else 0.5 if score[i] == score[j] else 0.0
    return (None, 0) if n == 0 else (u / n, int(n))


def row(complete, seen, first=None, length=None, branching=2.0):
    return dict(complete=complete, counts=dict(states_seen=seen, seen_at_first_win=first, solution_length=length),
                measures=dict(branching=branching))


def part1():
    print("== 1. the AUROC over eligible pairs")
    score = [3, 1, 2, 1, 5, 0]
    y = [1, 0, 0, 1, 1, 0]
    game = [1, 1, 2, 2, 3, 4]
    sm = [3, 3, 3, 3, 4, 4]
    a, n = A.auroc_pairs(score, y, game, sm)
    check(close(a, 2.5 / 3) and n == 3, f"hand-worked same-S_M AUROC 0.833333 on 3 pairs (got {a}, {n})")
    a, n = A.auroc_pairs(score, y, game)
    check(close(a, 6.5 / 7) and n == 7, f"hand-worked all-pairs AUROC 0.928571 on 7 pairs (got {a}, {n})")
    a, n = A.auroc_pairs([1, 2], [1, 0], [1, 1])
    check(a is None and n == 0, "no between-game pair gives None")
    rng = np.random.default_rng(7)
    bad = 0
    for _ in range(300):
        m = int(rng.integers(2, 25))
        s = rng.integers(0, 5, m).astype(float)
        s[rng.random(m) < 0.1] = np.nan
        s[rng.random(m) < 0.1] = A.INF
        yy = rng.integers(0, 2, m).astype(bool)
        gg = rng.integers(0, 6, m)
        st = gg % 3
        if rng.random() < 0.5:
            st = np.zeros(m, int)
        got = A.auroc_pairs(s, yy, gg, st)
        exp = brute(s, yy, gg, st)
        if not ((got[0] is None and exp[0] is None) or (close(got[0], exp[0]) and got[1] == exp[1])):
            bad += 1
    check(bad == 0, f"equals brute-force pair counting on 300 random cases with ties, nan and INF ({bad} differ)")


def part2():
    print("== 2. censoring at C")
    r1, r2 = row(True, 600, 100, 7), row(False, 2000, 500, 9)
    r3, r4, r5 = row(False, 300), row(False, 300, 100, 4), row(True, 50)
    check(A.l_c(r1, 1000) == -7 and close(A.h_c(r1, 1000), -math.log10(600)), "complete level with a win")
    check(A.l_c(r2, 1000) == -9 and A.l_c(r2, 400) == A.INF and close(A.h_c(r2, 400), -math.log10(400)),
          "first win after C is beyond C, and H_C sits at the ceiling")
    check(math.isnan(A.l_c(r3, 1000)) and math.isnan(A.h_c(r3, 1000)) and math.isnan(A.b_score(r3, 1000)),
          "time-capped below C without a win is excluded")
    check(A.l_c(r4, 1000) == -4 and math.isnan(A.h_c(r4, 1000)), "time-capped below C with a win enters L_C only")
    check(A.l_c(r5, 1000) == A.INF and close(A.h_c(r5, 1000), -math.log10(50)), "complete without a win is beyond C")
    cc = A.censor_counts({1: r1, 2: r2, 3: r3, 4: r4, 5: r5}, 1000)
    check(cc["L"]["excluded"] == 1 and cc["L"]["beyond_C"] == 1 and cc["H"]["excluded"] == 2
          and cc["H"]["at_ceiling"] == 1 and cc["L"]["complete"] == 2, f"censor counts {cc}")


def part3():
    print("== 3. outcome, verdict and outcome table")
    check(A.majority([1] * 5 + [0] * 5) == 1 and A.majority([1] * 4 + [0] * 6) == 0, "Y needs 5 of 10 seeds")
    try:
        A.majority([1] * 9)
        check(False, "nine seeds raise")
    except ValueError:
        check(True, "nine seeds raise")
    check(A.verdict(0.75, [0.55, 0.9]) == "shown", "lower end above 0.5 and point at 0.75: shown")
    check(A.verdict(0.70, [0.51, 0.9]) == "shown", "point exactly at the floor: shown")
    check(A.verdict(0.69, [0.55, 0.9]) == "not shown", "point below the floor: not shown")
    check(A.verdict(0.80, [0.50, 0.9]) == "not shown", "lower end at 0.5: not shown")
    cases = [({"N": "shown", "R": "shown", "I1": "not shown"}, 26, "Support", "IEEE Transactions on Games"),
             ({"N": "shown", "R": "shown", "I1": "shown"}, 26, "Support", "JAIR"),
             ({"N": "shown", "R": "not shown", "I1": "not shown"}, 26, "Refute", None),
             ({"N": "shown", "R": "shown", "I1": "void"}, 26, "Refute", None),
             ({"N": "not shown", "R": "shown", "I1": "shown"}, 26, "Refute", None),
             ({"N": "void", "R": "shown", "I1": "shown"}, 26, "Void", None),
             ({"N": "shown", "R": "void", "I1": "void"}, 26, "Void", None),
             ({"N": "shown", "R": "shown", "I1": "shown"}, 19, "Void", None)]
    for v, n, exp, venue in cases:
        got = A.outcome(v, n)
        check(got[0] == exp and (venue is None or got[1] == venue), f"{v}, {n} games: {exp} (got {got})")


def synthetic(n_games=26, related=True, seed=3, excl=0, all_complete=False):
    rng = np.random.default_rng(seed)
    sms = [2] * 3 + [3] * 13 + [4] * 7 + [5] * 3
    rows, truth, feats, outc = {}, {}, {}, {}
    for gi in range(n_games):
        g = f"game{gi:02d}"
        sm = sms[gi % len(sms)]
        for lv in A.LEVELS:
            length = int(rng.integers(3, 60))
            seen = int(rng.integers(100, 5000))
            r = row(True, seen, min(seen, 50 + length * 10), length, float(rng.uniform(1, 4)))
            if (gi * 5 + lv) < excl:
                r = row(False, 10)
            rows[(g, lv)] = r
            truth[(g, lv)] = {p: i < sm for i, p in enumerate(A.PRED)}
            feats[(g, lv)] = dict(area=float(rng.integers(20, 400)), actions=float(rng.integers(3, 6)),
                                  colours=float(rng.integers(3, 12)))
            p = 1 / (1 + math.exp((length - 30) / 5)) if related else 0.5
            for agent in A.AGENTS + A.REFERENCE:
                done = rng.random() < p
                for s in A.SEEDS:
                    outc[(agent, g, lv, s)] = True if all_complete else bool(done ^ (rng.random() < 0.05))
    return rows, truth, feats, outc


def part4():
    print("== 4. the whole analysis on synthetic data (200 resamples)")
    rows, truth, feats, outc = synthetic()
    res = A.analyze(rows, truth, feats, outc, 1000, workers=1, n_boot=200)
    n = res["agents"]["N"]
    check(res["units"] == 130 and res["games"] == 26, "130 levels of 26 games")
    check(all(res["agents"][a]["verdict"] == "shown" for a in A.AGENTS) and res["outcome"] == "Support"
          and res["venue"] == "JAIR", f"strong relation: all shown, Support, JAIR ({res['outcome']}, {res['venue']})")
    keys = sorted(rows)
    y = np.array([A.majority([outc[("N", g, lv, s)] for s in A.SEEDS]) for g, lv in keys], bool)
    L = np.array([A.l_c(rows[k], 1000) for k in keys])
    gm = np.array([int(g[4:]) for g, _ in keys])
    sm = np.array([sum(truth[k].values()) for k in keys])
    direct = A.auroc_pairs(L, y, gm, sm)
    check(close(n["lines"]["L_same"]["point"], direct[0]) and n["pairs_same"] == direct[1],
          "the point of AUROC_L equals a direct computation, and its pair count")
    check(n["pairs_same"] < n["pairs_all"], "same-S_M pairs are a subset of between-game pairs")
    check(n["lines"]["L_same"]["resamples"] + n["skipped"] == 200, "resamples used plus skipped equal 200")
    check(close(n["lines"]["Delta"]["point"], n["lines"]["H_all"]["point"] - n["lines"]["S_M|H_all"]["point"]),
          "Delta is H_all minus S_M|H_all")
    check(close(n["lines"]["L-B_same"]["point"], n["lines"]["L_same"]["point"] - n["lines"]["B_same"]["point"]),
          "L-B_same is L_same minus B_same on the same pairs")
    res2 = A.analyze(rows, truth, feats, outc, 1000, workers=2, n_boot=200)
    check(json.dumps(res, sort_keys=True, default=float) == json.dumps(res2, sort_keys=True, default=float),
          "two workers give the same result as one")
    check(res["agreement"]["N-R"]["units"] == 130, "agreement counted over 130 levels")
    text = A.report(res)
    check("**Outcome: Support**" in text and "| N |" in text and "secondary" in text, "the report states the outcome")

    rows, truth, feats, outc = synthetic(related=False, seed=5)
    res = A.analyze(rows, truth, feats, outc, 1000, workers=1, n_boot=200)
    check(res["agents"]["N"]["verdict"] == "not shown" and res["outcome"] == "Refute",
          f"no relation: N not shown, Refute (got {res['agents']['N']['verdict']}, {res['outcome']})")

    rows, truth, feats, outc = synthetic(all_complete=True)
    res = A.analyze(rows, truth, feats, outc, 1000, workers=1, n_boot=50)
    check(res["agents"]["N"]["verdict"] == "void" and res["outcome"] == "Void"
          and "completed share" in res["agents"]["N"]["void"][0], "every level completed: N void, study Void")

    rows, truth, feats, outc = synthetic(excl=14)
    res = A.analyze(rows, truth, feats, outc, 1000, workers=1, n_boot=50)
    check(any("L_C void" in r for r in res["agents"]["N"]["void"]), "14 of 130 levels excluded (10.8%): L_C void")
    rows, truth, feats, outc = synthetic(excl=13)
    res = A.analyze(rows, truth, feats, outc, 1000, workers=1, n_boot=50)
    check(not any("L_C void" in r for r in res["agents"]["N"]["void"]), "13 of 130 excluded (10.0%): not void")

    # every level beyond C: no win among the first C states on any level.  docs/PREREG.md Section 7.4 as drafted
    # censors such levels (rule 1) and says the share at the ceiling "is not a reason to void" (rule 3); no rule of
    # Section 7.6 voids a score that takes one value.  So L_C ties on every pair: AUROC_L is exactly 0.5, the
    # verdict is "not shown" and the outcome Refute, and nothing is void.  This test records that behaviour; it is
    # a point for the author (docs/DESIGN_gvgai_draft.md), not a rule this script adds.
    rows, truth, feats, outc = synthetic()
    beyond = {k: row(False, 2000) for k in rows}
    res = A.analyze(beyond, truth, feats, outc, 1000, workers=1, n_boot=50)
    nb = res["agents"]["N"]
    check(close(nb["lines"]["L_same"]["point"], 0.5) and nb["verdict"] == "not shown" and not nb["void"]
          and res["outcome"] == "Refute",
          f"every level beyond C: AUROC_L 0.5, not shown, not void, Refute under the drafted rules "
          f"(got {nb['lines']['L_same']['point']}, {nb['verdict']}, void {nb['void']}, {res['outcome']})")
    check(res["counts"]["L"]["beyond_C"] == 130 and res["counts"]["L"]["excluded"] == 0,
          "every level beyond C: 130 counted beyond C, 0 excluded")

    rows, truth, feats, outc = synthetic()
    one = {k: {p: i < 3 for i, p in enumerate(A.PRED)} for k in truth}
    res = A.analyze(rows, one, feats, outc, 1000, workers=1, n_boot=50)
    check(any("fewer than two values" in r for r in res["agents"]["N"]["void"]), "one value of S_M: void")

    blocks, games = A.build_blocks({("a", 0): dict(L=-1, H=-1, b=-1, S_M=3, area=1, actions=1, colours=1,
                                                   **{p: True for p in A.PRED}),
                                    ("a", 1): dict(L=-5, H=-1, b=-1, S_M=3, area=1, actions=1, colours=1,
                                                   **{p: True for p in A.PRED})}, {("a", 0): 1, ("a", 1): 0})
    check(A.line_values(blocks, ["a", "a"])["L_same"] is None, "two draws of one game form no eligible pair")


def part5():
    print("== 5. the ceiling in docs/PREREG.md and the supplement")
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "p.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write("x\n- **C = 1,000,000** fixed on ...\n")
        check(A.prereg_c(p) == 1_000_000, "a fixed C is read")
        with open(p, "w", encoding="utf-8") as f:
            f.write("x\n- **C = [open; fixed before the tag by the rule below].**\n")
        check(A.prereg_c(p) is None, "an open C reads as None")
    check(A.prereg_c() is None and A.C is None, "C is open in docs/PREREG.md and in the script")
    for camp in ("none", "gvgai-pilot-search", "dev-minigrid-e"):
        try:
            A.main(["--campaign", camp])
            check(False, f"campaign {camp} is refused")
        except SystemExit as e:
            check("not the confirmatory campaign" in str(e), f"campaign {camp} is refused")
    check(A.tag_refusal() is not None and "does not exist" in A.tag_refusal(),
          "this repository has no tag prereg-v1 yet: refused")
    try:
        A.main(["--campaign", A.CONFIRMATORY_CAMPAIGN])
        check(False, "the confirmatory campaign is refused before the tag")
    except SystemExit as e:
        check("does not exist" in str(e), "the confirmatory campaign is refused before the tag")
    check(A.L_C_VOID_RULE is None, "the void rule of L_C is open in the script (docs/PREREG.md, Section 7.4, rule 5)")
    saved = (A.tag_refusal, A.prereg_c, A.C)
    try:                       # past the tag and with C fixed, an open void rule still stops the analysis
        A.tag_refusal, A.prereg_c, A.C = (lambda *_a, **_k: None), (lambda *_a, **_k: 1000), 1000
        A.main(["--campaign", A.CONFIRMATORY_CAMPAIGN])
        check(False, "an open void rule of L_C stops the analysis")
    except SystemExit as e:
        check("void rule of L_C is not fixed" in str(e), "an open void rule of L_C stops the analysis")
    finally:
        A.tag_refusal, A.prereg_c, A.C = saved
    import shutil  # noqa: PLC0415
    import subprocess  # noqa: PLC0415
    with tempfile.TemporaryDirectory() as tmp:
        def git(*args):
            subprocess.run(["git", *args], cwd=tmp, capture_output=True, check=True)
        script = os.path.join(tmp, "scripts", "analyze_horizon.py")
        os.makedirs(os.path.dirname(script))
        shutil.copyfile(os.path.join(HERE, "analyze_horizon.py"), script)
        git("init", "-q")
        git("-c", "user.name=t", "-c", "user.email=t@t", "add", ".")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x")
        check("does not exist" in (A.tag_refusal(tmp, "prereg-v1", script) or ""), "no tag: refused")
        git("-c", "user.name=t", "-c", "user.email=t@t", "tag", "prereg-v1")
        check("does not exist" in (A.tag_refusal(tmp, "prereg-v1", script) or ""), "a lightweight tag is not enough")
        git("tag", "-d", "prereg-v1")
        git("-c", "user.name=t", "-c", "user.email=t@t", "tag", "-a", "prereg-v1", "-m", "v1")
        check(A.tag_refusal(tmp, "prereg-v1", script) is None, "an annotated tag holding the same script: allowed")
        with open(script, "a", encoding="utf-8") as f:
            f.write("# changed\n")
        check("differs" in (A.tag_refusal(tmp, "prereg-v1", script) or ""), "a script changed after the tag: refused")
    with open(os.path.join(REPO, "docs", "design", "dev_reading.json"), encoding="utf-8") as f:
        sup = A.supplement(json.load(f))
    check("AUROC 0.5164" in sup and "667 of 1560" in sup and "(42.8%)" in sup and "EXPLORATORY" in sup,
          "the supplement gives the development EH AUROC and the share not computed, labelled exploratory")


def main():
    part1()
    part2()
    part3()
    part4()
    part5()
    print("OK" if not FAILS else f"{len(FAILS)} failure(s)")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
