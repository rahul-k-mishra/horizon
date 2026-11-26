"""
test_g2_replay.py -- tests of scripts/g2_replay.py on the synthetic games of scripts/automation/gvgai_testgames
(allwin level 0, corridor levels 0 and 1), with 30 sequences of 40 actions and 2 workers; no pilot level is played.
The script under test runs as a separate process, as the author will run it.

Checks:
    1. the registered values: seed 20261126, 1,000 sequences, 200 actions, the 20 pilot levels of
       logs/draw_pilot.log, two passes; the draw is the same for the same (seed, game index, level), differs
       between levels, and lies in 0 .. A-1;
    2. a full run returns 0, reports every sequence identical, says "not G2" for test values, and writes 6 rows,
       6 done-markers and the manifest; some sequences end the game before 40 actions (allwin and corridor 0 can
       be won), corridor 1 never ends (boxed in);
    3. the two passes ran in different processes: the process tokens of pass 1 and pass 2 are disjoint;
    4. a row's digest equals the one recomputed here in one process: forwardKeys with the tick rule of
       sim_gvgai.with_tick, jobs.h64 of each key, SHA-256 of the list;
    5. resume: a run stopped after 2 units returns 2 with 2 done-markers; the same command again finishes and
       its digests, steps and statuses equal the full run's;
    6. a planted difference in one digest, or in one step count, of a pass-2 row makes the comparison return 1
       and name the level and the sequence;
    7. a run with other options on the same folder is refused (the manifest is checked).
Run: D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\test_g2_replay.py > logs\\test_g2_replay.log
(GVGAI's cache: HORIZON_GVGAI_CACHE if set, else D:\\Research\\horizon\\gvgai-cache if it exists, else a folder
under the temporary directory.)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "automation"))
sys.dont_write_bytecode = True
import g2_replay as G  # noqa: E402

FAILS = []
GAMES = "scripts/automation/gvgai_testgames"
LEVELS = "allwin:0,corridor:0,corridor:1"
SEQ, LEN = 30, 40


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        FAILS.append(what)


def cache():
    env = os.environ.get("HORIZON_GVGAI_CACHE")
    if env:
        return env
    return G.DEFAULT_CACHE if os.path.isdir(G.DEFAULT_CACHE) else os.path.join(tempfile.gettempdir(), "horizon-gvgai")


def run(out, *extra):
    cmd = [sys.executable, os.path.join(HERE, "g2_replay.py"), "--cache", cache(), "--out", out, "--workers", "2",
           "--games-dir", GAMES, "--levels", LEVELS, "--sequences", str(SEQ), "--length", str(LEN), *extra]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    return r.returncode, r.stdout + r.stderr


def rows(out):
    got = {}
    for fn in sorted(os.listdir(os.path.join(out, "rows"))):
        with open(os.path.join(out, "rows", fn), encoding="utf-8") as f:
            got[fn] = json.load(f)
    return got


def core(r):
    return {fn: (x["digests"], x["steps"], x["statuses"], x["actions_sha256"]) for fn, x in r.items()}


def main():
    print("== 1. the registered values and the draw")
    lv = G.registered_levels()
    check(G.SEED == 20261126 and G.SEQUENCES == 1000 and G.LENGTH == 200 and G.PASSES == (1, 2),
          "seed 20261126, 1,000 sequences of 200 actions, two passes")
    check(len(lv) == 20 and [g for g, _ in lv[::5]] == ["bait", "labyrinthdual", "rivers", "watergame"],
          "20 pilot levels: bait, labyrinthdual, rivers, watergame, levels 0 to 4, in the order of logs/draw_pilot.log")
    a, b, c = G.sequences(G.SEED, 2, 1, 5, 50, 200), G.sequences(G.SEED, 2, 1, 5, 50, 200), G.sequences(G.SEED, 2, 2, 5, 50, 200)
    check((a == b).all() and not (a == c).all() and a.min() == 0 and a.max() == 4 and a.shape == (50, 200),
          "the same (seed, game, level) gives the same draw; another level another; values 0 to 4 for 5 actions")

    with tempfile.TemporaryDirectory() as tmp:
        print("== 2. a full run on the synthetic levels")
        full = os.path.join(tmp, "full")
        code, text = run(full)
        r = rows(full)
        check(code == 0 and "result: identical" in text and "not G2: test parameters" in text
              and f"sequences identical {3 * SEQ} of {3 * SEQ}" in text,
              f"exit 0, every sequence identical, marked not G2 (exit {code})")
        if code != 0:
            print(text)
        check(len(r) == 6 and len(os.listdir(os.path.join(full, "done"))) == 6
              and os.path.exists(os.path.join(full, "manifest.json")), "6 rows, 6 done-markers and the manifest")
        ended = {fn: sum(s < LEN for s in x["steps"]) for fn, x in r.items()}
        check(ended["r1-corridor-l1.json"] == 0 and all(s == LEN for s in r["r1-corridor-l1.json"]["steps"])
              and ended["r1-corridor-l0.json"] + ended["r1-allwin-l0.json"] > 0,
              f"some sequences end the game early, and the replay stops there; corridor 1 never ends ({ended})")
        print("== 3. the passes in different processes")
        t1 = {x["process_token"] for x in r.values() if x["replay_pass"] == 1}
        t2 = {x["process_token"] for x in r.values() if x["replay_pass"] == 2}
        check(t1 and t2 and not (t1 & t2) and "shared by both passes 0" in text,
              f"process tokens of pass 1 and pass 2 are disjoint ({len(t1)} and {len(t2)})")

        print("== 4. the digest recomputed in one process")
        import jobs        # noqa: PLC0415
        import sim_gvgai   # noqa: PLC0415
        bridge = sim_gvgai.start_jvm(cache())
        gf, lf = [x.replace("\\", "/") for x in sim_gvgai.level_paths("corridor", 0, GAMES)]
        n = len(bridge.actionNames(bridge.load(gf, lf, 0)))
        acts = G.sequences(G.SEED, 1, 0, n, SEQ, LEN)        # corridor is game index 1 in LEVELS
        keys, _t, status = bridge.forwardKeys(gf, lf, bytes(int(x) for x in acts[7]), bool(sim_gvgai.with_tick("corridor", GAMES)))
        hs = [jobs.h64(bytes(k)) for k in keys]
        row = r["r2-corridor-l0.json"]
        check(row["digests"][7] == G.digest(hs) and row["steps"][7] == len(hs) - 1 and row["statuses"][7] == int(status)
              and row["key_form"] == "EXTENDED" and row["hash"] == "jobs.h64",
              "sequence 7 of corridor 0: digest, steps and status equal a replay here with jobs.h64 of the key")

        print("== 5. resume")
        part = os.path.join(tmp, "part")
        code1, text1 = run(part, "--stop-after", "2")
        check(code1 == 2 and len(os.listdir(os.path.join(part, "done"))) == 2 and "incomplete" in text1,
              f"stopped after 2 units: exit 2, 2 done-markers (exit {code1})")
        code2, text2 = run(part)
        check(code2 == 0 and "2 unit(s) already done" in text2 and core(rows(part)) == core(r),
              f"the same command again finishes, skips the 2 done units, and gives the full run's rows (exit {code2})")

        print("== 6. a planted difference")
        for what in ("digest", "steps"):
            bad = os.path.join(tmp, "bad-" + what)
            shutil.copytree(full, bad)
            fn = os.path.join(bad, "rows", "r2-allwin-l0.json")
            with open(fn, encoding="utf-8") as f:
                x = json.load(f)
            if what == "digest":
                x["digests"][5] = "0" * 64
            else:
                x["steps"][5] += 1
            with open(fn, "w", encoding="utf-8") as f:
                json.dump(x, f)
            code, text = run(bad)
            check(code == 1 and "result: different" in text and "allwin" in text and "first: sequence 5" in text,
                  f"a changed {what} in pass 2 of allwin 0: exit 1, the level and sequence 5 named (exit {code})")

        print("== 7. the manifest")
        code, text = run(full, "--sequences", "31")
        check(code == 3 and "refused" in text, f"other options on the same folder are refused (exit {code})")

    print("OK" if not FAILS else f"{len(FAILS)} failure(s)")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
