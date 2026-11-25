"""
rule3_reading.py -- what each way of making docs/PREREG.md Section 7.4, rule 3, and scripts/analyze_horizon.py
agree would have done on the development search rows (docs/registration/REVIEW_2026-11-25.md, item 9).
EXPLORATORY, development data: stage E (campaign dev-minigrid-e, 1,560 units of study 1's MiniGrid/BabyAI
games); stage D (campaign dev-minigrid, the same units, the only development rows with searches stopped by the
time cap; its schema horizon.search.v2 has no first-win counts, so L_C is not read from it and options (a) and
(c) are not computed on it); and the pilot search (campaign gvgai-pilot-search, the 20 extended-key units; the units ending "-v0"
serve a measurement only, PREREG Section 8).  No confirmatory row exists, and none is read.

Rule 3 as registered: "A search quantity is void if more than 10% of the confirmatory levels are excluded under
rule 2."  The search quantities of Section 6 are L_C, H_C and b.  scripts/analyze_horizon.py applies the 10% to
L_C only (void_reasons); for H_C and b it reports the excluded counts and marks nothing void.

For each set of rows and each candidate ceiling C of logs/stage_e_reading.log, the script reads every unit with
analyze_horizon's own functions l_c, h_c and b_score (a missing value is a unit excluded under rule 2), and prints:
    - the units excluded for each of L_C, H_C and b, and whether the share is over 10%;
    - what each option would void:
        (a) the text narrowed to L_C (the script as it is): L_C only;
        (b) the script made to follow the text: L_C, H_C and b, each by its own share, a void H_C or b marking
            its secondary lines void and entering no verdict;
        (c) as (b), with the share of a unit excluded by any of the three quantities.
The comparison is the script's own, excluded / units > 0.10.

Reads committed rows only and plays nothing.  Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\rule3_reading.py > logs\\rule3_reading.log
"""
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import analyze_horizon as A  # noqa: E402

CEILINGS = (10_000, 100_000, 300_000, 1_000_000, 2_000_000)
SETS = (("stage E, dev-minigrid-e (devsearch)", "runs/dev-minigrid-e/devsearch/*.json", lambda r: True),
        ("stage D, dev-minigrid (devsearch; H_C and b only)", "runs/dev-minigrid/devsearch/*.json", lambda r: True),
        ("pilot search, gvgai-pilot-search (gvgaisearch), extended key", "runs/gvgai-pilot-search/gvgaisearch/*.json",
         lambda r: not r["unit_id"].endswith("-v0")))


def load(pattern, keep):
    rows = []
    for f in sorted(glob.glob(os.path.join(REPO, *pattern.split("/")))):
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        if keep(r):
            rows.append(r)
    return rows


def main():
    print("rule 3 of PREREG Section 7.4 against scripts/analyze_horizon.py, on development rows (EXPLORATORY)")
    print(f"void share: excluded / units > {A.EXCLUDED_MAX} (analyze_horizon.EXCLUDED_MAX); ceilings {', '.join(f'{c:,}' for c in CEILINGS)}")
    for name, pattern, keep in SETS:
        rows = load(pattern, keep)
        caps = {}
        for r in rows:
            caps[r.get("cap_hit") or "none"] = caps.get(r.get("cap_hit") or "none", 0) + 1
        print(f"\n== {name}: {len(rows)} rows; stopped by: "
              + ", ".join(f"{k} {v}" for k, v in sorted(caps.items())))
        for c in CEILINGS:
            stage_d = rows and rows[0]["schema"] == "horizon.search.v2"
            qs = (("H_C", A.h_c), ("b", A.b_score)) if stage_d else (("L_C", A.l_c), ("H_C", A.h_c), ("b", A.b_score))
            ex = {q: set() for q, _ in qs}
            for r in rows:
                for q, fn in qs:
                    if math.isnan(fn(r, c)):
                        ex[q].add(r["unit_id"])
            n = len(rows)
            over = {q: len(s) / n > A.EXCLUDED_MAX for q, s in ex.items()}
            anyq = set().union(*ex.values())
            if stage_d:
                void_b = [q for q in ("H_C", "b") if over[q]]
                print(f"  C {c:>9,}: excluded H_C {len(ex['H_C'])}, b {len(ex['b'])} of {n} | void under (b), "
                      f"H_C and b: {', '.join(void_b) or 'none'}")
                continue
            void_a = [q for q in ("L_C",) if over[q]]
            void_b = [q for q in ("L_C", "H_C", "b") if over[q]]
            void_c = ["L_C", "H_C", "b"] if len(anyq) / n > A.EXCLUDED_MAX else []
            print(f"  C {c:>9,}: excluded L_C {len(ex['L_C'])}, H_C {len(ex['H_C'])}, b {len(ex['b'])}, any {len(anyq)} "
                  f"of {n} | void under (a): {', '.join(void_a) or 'none'}; (b): {', '.join(void_b) or 'none'}; "
                  f"(c): {', '.join(void_c) or 'none'}")
        short = [r for r in rows if r.get("cap_hit") in ("time", "memory")]
        seen = sorted(r["counts"]["states_seen"] for r in short)
        print(f"  stopped by time or memory: {len(short)}" + (f"; states seen by them: least {seen[0]:,}, most "
                                                              f"{seen[-1]:,}" if seen else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
