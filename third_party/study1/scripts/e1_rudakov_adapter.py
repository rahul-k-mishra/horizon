"""
E1a ADAPTER: Rudakov, Shock & Cowley's graph-exploration agent ("heuristicagent", arXiv 2512.24156,
code in external/rudakov_just_explore at the commit in its PROVENANCE.md) played through our
offline engine with our scorecard accounting.  docs/TOG_PLAN_v2.md Section 3 (admissibility A1-A7,
decision rule 3.3) is the protocol; this script changes none of it.  docs/E1_rudakov_feasibility.md
is the reading of their code that this adapter rests on.

WHAT IS THEIRS AND WHAT IS OURS
    Theirs, unchanged and not copied: HeuristicAgent (choose_action, is_done, main loop with its
    exception handling and level-up detection), FrameProcessor, GraphExplorer.
    Ours, at the I/O boundary only, with no edit to any file of theirs:
      B1 take_action: their REST call to the preview server is replaced by env.step on the offline
         engine.  Their first RESET of a play is answered with the environment's initial
         observation without a step, which is what the 0.9.8 server does for the RESET that creates
         a play; every later RESET is a counted step.
      B2 frame conversion: the engine's FrameDataRaw becomes their FrameData.  The current API
         calls the level counter "levels_completed"; their FrameData reads it as "score".  Without
         this mapping their agent never sees a level end (score stays 0).
      B3 seed: their __init__ seeds Python's global random from the wall clock; we call
         random.seed(seed) once, right after construction.  Nothing else of theirs draws random
         numbers in a different order.
      B4 minimal_step_time = 0: a 0.31 s sleep per action that rate-limited the preview server;
         it changes no decision.  (Kept at 0.31 s in the fidelity check's REST arm, unmodified.)
      B5 budget and time cap: MAX_ACTIONS and TOTAL_TIME_ALLOWED are their own loop limits; we set
         them from --budget and --game-seconds, and take_action stops the loop at the budget.
      B6 imports: their agents/__init__.py imports LLM templates (langgraph, openai, smolagents)
         that heuristicagent never uses and that are not installed here; we load their modules
         without executing that __init__ (a namespace stub for the "agents" package).
      B7 their prints (several per action) go to a counter, not the console.

ACCOUNTING: identical to scripts/g_nav_run.py / g_agent.play: Arcade offline, one scorecard per
run, every env.step (RESET included) counts toward the budget, per-level counts read from the
closed scorecard (card_levels, card_baseline, card_scores).  Rows in the ablate format, mode
"rudakov".

HELD-OUT GUARD: in E1 phase 1 no held-out game may be played.  Held-out games are refused unless
--allow-heldout is given (phase 2, after admissibility A1-A7 is recorded).

FIDELITY (--fidelity; plan A6).  Plays the same game and seed three ways and compares the full
sequence of issued actions (id, x, y) and the scorecard's per-level counts:
    U  their HeuristicAgent with their own REST take_action and 0.31 s sleep, against the
       arc-agi 0.9.8 local Flask server (Arcade offline), with only B2 (added to the server's JSON
       as "score"), B3 and the action cap applied from outside;
    A  this adapter, in this process;
    A1, A2  this adapter in fresh processes with PYTHONHASHSEED=1 and 2 (their graph keeps frame
       hashes in Python sets; this shows whether set order reaches the actions).
Their literal entry point (main.py -> Swarm) cannot be the U arm: it imports the uninstalled LLM
templates, has no seed (wall clock) and no action cap, so no same-seed comparison with it exists.
The plan's A6 asks for 1,000 actions on ft09 and tu93; the defaults here (tu93, 300) are the
phase-1 request and are reported as such, not as A6.

Commands (PowerShell, from D:\\Research\\arc3\\repo):

    $py = "D:\\Research\\arc3\\brutus\\.venv\\Scripts\\python.exe"
    & $py scripts\\e1_rudakov_adapter.py --fidelity                                    (tu93, 300 actions)
    & $py scripts\\e1_rudakov_adapter.py --games tu93,dc22 --seeds 1 --budget 200 --workers 2 --tag phase1_timing
    & $py scripts\\e1_rudakov_adapter.py --fidelity --fidelity-games ft09,tu93 --fidelity-actions 1000   (A6 as registered)
    & $py scripts\\e1_rudakov_adapter.py --fidelity --fidelity-games vc33,lp85 --fidelity-actions 300    (level wins in 300)

RESUMING.  A run stopped part-way leaves <out>.partial.jsonl and is continued by the same command
(the partial file is always read).  --resume (no PATH) also keeps the completed (game, seed) rows
of an existing output file and completes the missing ones; --resume PATH takes completed rows from
another file (read only), e.g. a 4-seed file when the same run is extended to 10 seeds under a new
tag.  Rows are kept only if they were run with the same --budget; any other budget stops the
script.  Kept rows are copied unchanged.

PER-RUN CHECKS printed at the end: time-truncated runs; runs where their choose_action raised
(their own fallback repeats the last action; counted in diag.their_prints.Error); and level wins
not followed by their GraphExplorer.reset, which would mean the levels_completed -> score mapping
(B2) failed.  The reset is observed, not altered.

EXPECTED OUTPUT
    fidelity: per arm, issued actions, steps, card_levels; "U vs A: IDENTICAL" or the first index
    where the sequences differ with both actions; the same for A vs A1 and A vs A2.
    runs: one line per (game, seed) with score, levels, steps, seconds, s/action (and the part
    spent inside env.step); then "seconds per action ... against the 0.28 s threshold (A7)".
    Writes runs/e1_rudakov_<tag>.json (fidelity: runs/e1_rudakov_fidelity_<games>_<n>.json).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import random
import subprocess
import sys
import threading
import time
import types
from collections import Counter
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
THEIRS = os.path.join(REPO, "external", "rudakov_just_explore")
DEFAULT_ENV = r"D:\Research\arc3\brutus\environment_files"
TRAIN = ["tu93", "ls20", "vc33", "m0r0", "ft09", "lp85", "lf52", "dc22"]
HELD_OUT = ["ar25", "bp35", "cd82", "cn04", "g50t", "ka59", "r11l", "re86", "s5i5",
            "sb26", "sc25", "sk48", "sp80", "su15", "tn36", "tr87", "wa30"]
MODE = "rudakov"
A7_LIMIT = 0.28


# ---------------------------------------------------------------- loading their code (B6)

def load_theirs():
    """Their HeuristicAgent and FrameData, without running agents/__init__.py (B6)."""
    if "agents.heuristic_agent" in sys.modules:
        m = sys.modules["agents.heuristic_agent"]
        return m.HeuristicAgent, sys.modules["agents.structs"].FrameData
    if THEIRS not in sys.path:
        sys.path.insert(0, THEIRS)
    pkg = types.ModuleType("agents")
    pkg.__path__ = [os.path.join(THEIRS, "agents")]
    sys.modules["agents"] = pkg
    import importlib
    ha = importlib.import_module("agents.heuristic_agent")
    st = importlib.import_module("agents.structs")
    return ha.HeuristicAgent, st.FrameData


class PrintCounter(io.TextIOBase):
    """B7: their per-action prints are counted by kind, not shown."""
    KINDS = ("Error:", "Suspicious transition", "Lowest dist", "Here we are", "Node ", "Will run")

    def __init__(self):
        self.counts = Counter()
        self._buf = ""

    def write(self, s):
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            for k in self.KINDS:
                if line.startswith(k):
                    self.counts[k.strip(": ")] += 1
                    break
        return len(s)


class BudgetSpent(Exception):
    pass


def to_their_frame(FrameData, raw, game_id):
    """B2: engine FrameDataRaw -> their FrameData; levels_completed is their 'score'."""
    return FrameData(
        game_id=game_id,
        frame=[f.tolist() if hasattr(f, "tolist") else f for f in (raw.frame or [])],
        state=raw.state.name,
        score=int(raw.levels_completed),
        available_actions=[int(a) for a in (raw.available_actions or [])],
        guid=raw.guid,
        full_reset=bool(raw.full_reset),
    )


def make_offline_agent(HeuristicAgent, FrameData, env, game_id, seed, budget, seconds):
    """Their agent with take_action (B1) replaced; nothing else overridden."""
    from arcengine import GameAction as EA

    class OfflineHeuristicAgent(HeuristicAgent):
        def take_action(self, action):                                   # B1
            if action.value == 0 and not self._started:
                # the RESET that creates a play: the server returns the observation, no step
                self._started = True
                self.issued.append((0, None, None))
                return to_their_frame(FrameData, env.observation_space, game_id)
            if self.steps >= self._budget:
                raise BudgetSpent()
            self._started = True
            t = time.perf_counter()
            if action.value == 6:
                x, y = int(action.action_data.x), int(action.action_data.y)
                raw = env.step(EA.ACTION6, data={"x": x, "y": y})
                self.issued.append((6, x, y))
            else:
                raw = env.step(EA.from_id(int(action.value)))
                self.issued.append((int(action.value), None, None))
            self.env_seconds += time.perf_counter() - t
            self.steps += 1
            if int(raw.levels_completed) != self._level:
                self.level_steps.append((self._level, self.steps, raw.state.name))
                self._level = int(raw.levels_completed)
            self.last_raw = raw
            return to_their_frame(FrameData, raw, game_id)

    agent = OfflineHeuristicAgent(card_id="offline", game_id=game_id, agent_name="heuristicagent",
                                  ROOT_URL="offline://", record=False)
    random.seed(seed)                                                    # B3
    agent.minimal_step_time = 0.0                                        # B4
    agent.MAX_ACTIONS = budget + 10                                      # B5 (take_action stops first)
    agent.TOTAL_TIME_ALLOWED = seconds                                   # B5
    agent._budget, agent._started, agent._level = budget, False, 0
    agent.steps, agent.env_seconds, agent.issued, agent.level_steps = 0, 0.0, [], []
    agent.last_raw = None
    # observation only: record the step count at every GraphExplorer.reset (their level-up path
    # resets the graph; B2 is working if every level win is followed by a reset)
    agent.graph_resets = []
    _reset = agent.graph_explorer.reset

    def _observed_reset():
        agent.graph_resets.append(agent.steps)
        return _reset()
    agent.graph_explorer.reset = _observed_reset
    return agent


# ---------------------------------------------------------------- one run, our accounting

def play(game, seed, budget, env_dir, seconds):
    import logging
    logging.disable(logging.CRITICAL)
    from arc_agi import Arcade
    HeuristicAgent, FrameData = load_theirs()
    t0 = time.time()
    arc = Arcade(operation_mode="offline", environments_dir=env_dir)
    card = arc.open_scorecard(tags=["e1-rudakov"])
    env = arc.make(game, scorecard_id=card)
    pc = PrintCounter()
    with contextlib.redirect_stdout(pc):
        agent = make_offline_agent(HeuristicAgent, FrameData, env, env.environment_info.game_id,
                                   seed, budget, seconds)
        tp = time.perf_counter()
        stopped = "budget"
        try:
            agent.main()
            stopped = "win" if agent.frames[-1].state.name == "WIN" else "their_loop_ended"
        except BudgetSpent:
            pass
        play_seconds = time.perf_counter() - tp
    raw = agent.last_raw or env.observation_space
    time_truncated = stopped == "their_loop_ended" and agent.steps < budget
    # level_log in the ablate format, from the engine's level counter
    level_log, prev = [], 0
    for lvl, at, st in agent.level_steps:
        level_log.append(dict(level=lvl, actions=at - prev, ended="won"))
        prev = at
    if raw.state.name != "WIN":
        level_log.append(dict(level=int(raw.levels_completed), actions=agent.steps - prev,
                              ended=raw.state.name))
    ids = Counter(a for a, _x, _y in agent.issued[1:])
    wins_at = [at for _lvl, at, _st in agent.level_steps]
    resets_at = set(agent.graph_resets)
    wins_followed_by_reset = sum(1 for at in wins_at if at in resets_at)
    out = dict(game=game, mode=MODE, seed=seed, budget=budget, game_seconds=seconds,
               actions=agent.steps, levels=int(raw.levels_completed),
               state=raw.state.name, score=0.0, level_log=level_log, stopped=stopped,
               time_truncated=time_truncated, seconds=round(time.time() - t0, 1),
               play_seconds=round(play_seconds, 2),
               sec_per_action=round(play_seconds / max(1, agent.steps), 4),
               env_sec_per_action=round(agent.env_seconds / max(1, agent.steps), 4),
               diag=dict(issued_by_id={str(k): v for k, v in sorted(ids.items())},
                         level_wins_at_step=wins_at, graph_resets=len(agent.graph_resets),
                         level_wins_followed_by_graph_reset=wins_followed_by_reset,
                         resets=ids.get(0, 0), their_prints=dict(pc.counts)),
               adapter=dict(commit=provenance_commit(), boundary=["B1", "B2", "B3", "B4", "B5", "B6", "B7"]))
    sc = arc.close_scorecard(card)
    for e in sc.environments:
        if e.id.startswith(game):
            out["score"] = round(float(e.score), 4)
            for run in (e.runs or [])[:1]:
                out["card_levels"] = [int(x) for x in (run.level_actions or [])]
                out["card_baseline"] = [int(x) for x in (run.level_baseline_actions or [])]
                out["card_scores"] = [round(float(x), 3) for x in (run.level_scores or [])]
    out["_issued"] = agent.issued
    return out


def one(job):
    game, seed, budget, env_dir, seconds = job
    try:
        r = play(game, seed, budget, env_dir, seconds)
        r.pop("_issued", None)
        return r
    except Exception as e:
        import traceback
        return dict(game=game, mode=MODE, seed=seed, levels=0, score=0.0, level_log=[],
                    error=repr(e)[:300], trace=traceback.format_exc()[-2000:])


def provenance_commit():
    p = os.path.join(THEIRS, "PROVENANCE.md")
    try:
        for line in open(p, encoding="utf-8"):
            if line.lower().startswith("commit:"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "unknown"


# ---------------------------------------------------------------- fidelity (A6)

def arm_rest(game, seed, n_steps, env_dir, port):
    """U: their agent class and their REST take_action against the 0.9.8 local server."""
    import logging
    logging.disable(logging.CRITICAL)
    from arc_agi import Arcade
    from arc_agi.server import create_app
    from flask import request
    from werkzeug.serving import make_server
    HeuristicAgent, _FD = load_theirs()
    from agents.swarm import Swarm

    arc = Arcade(operation_mode="offline", environments_dir=env_dir)
    app, _api = create_app(arc)
    issued = []

    @app.before_request
    def _log():
        if request.path.startswith("/api/cmd/"):
            name = request.path.rsplit("/", 1)[1]
            d = request.get_json(silent=True) or {}
            aid = 0 if name == "RESET" else int(name.replace("ACTION", ""))
            issued.append((aid, d.get("x") if aid == 6 else None, d.get("y") if aid == 6 else None))

    server_errors = Counter()

    @app.after_request
    def _preview_score(resp):                                            # B2, on the server side
        if request.path.startswith("/api/cmd/") and resp.status_code != 200:
            server_errors[(resp.get_json(silent=True) or {}).get("message", str(resp.status_code))] += 1
        if request.path.startswith("/api/cmd/") and resp.is_json:
            d = resp.get_json()
            if isinstance(d, dict) and "levels_completed" in d:
                d["score"] = d["levels_completed"]
                resp.set_data(json.dumps(d))
        return resp

    srv = make_server("127.0.0.1", port, app, threaded=True)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    root = f"http://127.0.0.1:{port}"
    pc = PrintCounter()
    try:
        with contextlib.redirect_stdout(pc):
            swarm = Swarm.__new__(Swarm)                  # only its open_scorecard is used
            import requests
            swarm.ROOT_URL, swarm.tags = root, ["e1-fidelity"]
            swarm.headers = {"X-API-Key": "", "Accept": "application/json"}
            swarm._session = requests.Session()
            card_id = swarm.open_scorecard()
            # their main.py plays the ids /api/games returns (versioned, e.g. tu93-0768757b),
            # filtered by prefix; a bare "tu93" is "not found" on the 0.9.8 server
            full_ids = [g["game_id"] for g in swarm._session.get(f"{root}/api/games").json()]
            game_id = [g for g in full_ids if g.startswith(game)][0]
            agent = HeuristicAgent(card_id=card_id, game_id=game_id, agent_name="heuristicagent",
                                   ROOT_URL=root, record=False)
            random.seed(seed)                                            # B3
            agent.MAX_ACTIONS = n_steps          # their loop: n_steps + 1 iterations, first is the creating RESET
            agent.main()
        sc = arc.close_scorecard(card_id)
        card = {}
        for e in sc.environments:
            if e.id.startswith(game):
                for run in (e.runs or [])[:1]:
                    card = dict(card_levels=[int(x) for x in (run.level_actions or [])],
                                levels=int(e.levels_completed or 0))
    finally:
        srv.shutdown()
    if server_errors:
        print(f"  U arm: SERVER ERRORS {dict(server_errors)} - their client turns an error reply into "
              f"a default FrameData (state NOT_PLAYED) and resets; this arm is not valid")
    return dict(issued=issued, steps=len(issued) - 1, prints=dict(pc.counts), game_id=game_id,
                server_errors=dict(server_errors), **card)


def arm_adapter(game, seed, n_steps, env_dir):
    r = play(game, seed, n_steps, env_dir, seconds=10 ** 6)
    return dict(issued=[tuple(x) for x in r["_issued"]], steps=r["actions"],
                card_levels=r.get("card_levels"), levels=r.get("levels"),
                prints=r["diag"]["their_prints"], sec_per_action=r["sec_per_action"])


def arm_subprocess(game, seed, n_steps, env_dir, hashseed):
    env = dict(os.environ, PYTHONHASHSEED=str(hashseed))
    code = (f"import sys, json; sys.path.insert(0, {HERE!r}); import e1_rudakov_adapter as E; "
            f"r = E.arm_adapter({game!r}, {seed}, {n_steps}, {env_dir!r}); "
            f"print('@@' + json.dumps(r))")
    p = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True,
                       timeout=3600)
    line = [l for l in p.stdout.splitlines() if l.startswith("@@")]
    if not line:
        raise RuntimeError(f"subprocess failed: {p.stderr[-1500:]}")
    r = json.loads(line[-1][2:])
    r["issued"] = [tuple(x) for x in r["issued"]]
    return r


def compare(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if tuple(a[i]) != tuple(b[i]):
            return f"DIFFER at issued action {i}: {a[i]} vs {b[i]} (lengths {len(a)}, {len(b)})"
    if len(a) != len(b):
        return f"DIFFER in length only: {len(a)} vs {len(b)} (first {n} identical)"
    return f"IDENTICAL ({n} issued actions)"


def fidelity(games, n_steps, seed, env_dir, port, out_path):
    res = {}
    for g in games:
        if g in HELD_OUT:
            sys.exit(f"STOP: {g} is held-out; fidelity runs on train games only")
        print(f"\n--- fidelity {g}, seed {seed}, {n_steps} steps")
        t = time.time()
        u = arm_rest(g, seed, n_steps, env_dir, port)
        print(f"  U  (their REST loop, local server): {len(u['issued'])} issued, levels "
              f"{u.get('levels')}, card_levels {u.get('card_levels')}  [{time.time() - t:.0f} s]")
        a = arm_adapter(g, seed, n_steps, env_dir)
        print(f"  A  (adapter, this process):         {len(a['issued'])} issued, levels "
              f"{a.get('levels')}, card_levels {a.get('card_levels')}")
        a1 = arm_subprocess(g, seed, n_steps, env_dir, 1)
        a2 = arm_subprocess(g, seed, n_steps, env_dir, 2)
        rows = {
            "U_vs_A": compare(u["issued"], a["issued"]),
            "A_vs_A1(PYTHONHASHSEED=1)": compare(a["issued"], a1["issued"]),
            "A_vs_A2(PYTHONHASHSEED=2)": compare(a["issued"], a2["issued"]),
            "card_levels_U_vs_A": "IDENTICAL" if u.get("card_levels") == a.get("card_levels")
            else f"DIFFER {u.get('card_levels')} vs {a.get('card_levels')}",
        }
        for k, v in rows.items():
            print(f"  {k:28} {v}")
        res[g] = dict(seed=seed, n_steps=n_steps, comparisons=rows,
                      U=dict(u, issued=u["issued"]), A=a, A1=dict(steps=a1["steps"], card_levels=a1.get("card_levels")),
                      A2=dict(steps=a2["steps"], card_levels=a2.get("card_levels")))
    out = dict(script="scripts/e1_rudakov_adapter.py --fidelity", created=time.strftime("%Y-%m-%d %H:%M:%S"),
               commit=provenance_commit(), games=games, n_steps=n_steps, seed=seed,
               note="phase-1 check; plan A6 is 1,000 actions on ft09 and tu93" if
               (sorted(games) != ["ft09", "tu93"] or n_steps < 1000) else "plan A6 settings",
               results=res)
    write(out_path, out)


# ---------------------------------------------------------------- main

def budget_matches(r, budget):
    """A kept row must have been run with this budget (rows before the budget field: it used the
    whole budget, or won)."""
    if "budget" in r:
        return int(r["budget"]) == int(budget)
    return int(r.get("actions", -1)) == int(budget) or r.get("stopped") == "win"


def write(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=list)
    os.replace(tmp, path)
    print(f"\nwrote {path}")


def main():
    ap = argparse.ArgumentParser(description="E1a adapter for the Rudakov et al. agent")
    ap.add_argument("--games", default="tu93,dc22", help="train | heldout | all | comma list")
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--game-seconds", type=float, default=3600)
    ap.add_argument("--env-dir", default=DEFAULT_ENV)
    ap.add_argument("--tag", default="phase1")
    ap.add_argument("--allow-heldout", action="store_true",
                    help="phase 2 only, after A1-A7 are recorded")
    ap.add_argument("--fidelity", action="store_true")
    ap.add_argument("--fidelity-games", default="tu93")
    ap.add_argument("--fidelity-actions", type=int, default=300)
    ap.add_argument("--fidelity-seed", type=int, default=1000)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--out-dir", default=os.path.join(REPO, "runs"))
    ap.add_argument("--resume", nargs="?", const="", default=None, metavar="PATH",
                    help="skip (game, seed) rows already completed with the same budget: in the "
                         "output file itself (no PATH: continue a stopped run), or in PATH (e.g. a "
                         "4-seed file when extending to 10 seeds; PATH is only read)")
    args = ap.parse_args()

    if args.fidelity:
        games = args.fidelity_games.split(",")
        out = os.path.join(args.out_dir, f"e1_rudakov_fidelity_{'-'.join(games)}_{args.fidelity_actions}.json")
        if os.path.exists(out) and not args.force:
            sys.exit(f"{out} exists (use --force)")
        fidelity(games, args.fidelity_actions, args.fidelity_seed, args.env_dir, args.port, out)
        return

    games = (TRAIN if args.games == "train" else HELD_OUT if args.games == "heldout"
             else TRAIN + HELD_OUT if args.games == "all" else args.games.split(","))
    bad = [g for g in games if g in HELD_OUT]
    if bad and not args.allow_heldout:
        sys.exit(f"STOP: held-out games {bad} refused in E1 phase 1 (--allow-heldout is for phase 2)")
    out = os.path.join(args.out_dir, f"e1_rudakov_{args.tag}.json")
    part = out + ".partial.jsonl"
    if os.path.exists(out) and not args.force and args.resume is None:
        sys.exit(f"{out} exists (use --resume to continue it, or --force to overwrite)")
    done = []
    sources = []
    if args.resume is not None:
        src = args.resume or out
        if os.path.exists(src):
            sources.append(src)
        elif args.resume:
            sys.exit(f"--resume {src}: no such file")
    for src in sources:
        prev = json.load(open(src))
        kept = [r for r in prev if not r.get("error") and r.get("mode") == MODE
                and r["game"] in games and r["seed"] < 1000 + args.seeds and budget_matches(r, args.budget)]
        wrong = [r for r in prev if not r.get("error") and not budget_matches(r, args.budget)]
        if wrong:
            sys.exit(f"STOP: {len(wrong)} rows in {src} were run with another budget "
                     f"(e.g. {wrong[0]['game']} seed {wrong[0]['seed']}); not mixed")
        print(f"resume: {len(kept)} completed rows taken from {src}")
        done += kept
    if os.path.exists(part):                                   # crash recovery, always
        from_part = [json.loads(l) for l in open(part) if l.strip()]
        print(f"resuming: {len(from_part)} runs already in {part}")
        done += [r for r in from_part if budget_matches(r, args.budget)]
    uniq = {}
    for r in done:
        if not r.get("error"):
            uniq.setdefault((r["game"], r["seed"]), r)
    done = list(uniq.values())
    have = set(uniq)
    jobs = [(g, 1000 + s, args.budget, args.env_dir, args.game_seconds)
            for s in range(args.seeds) for g in games if (g, 1000 + s) not in have]
    print(f"{len(games)} games x {args.seeds} seeds, {args.budget} actions, {len(jobs)} to run, "
          f"{args.workers} workers, commit {provenance_commit()}\n", flush=True)
    rows = [r for r in done if not r.get("error")]
    t0 = time.time()
    with Pool(max(1, min(args.workers, len(jobs) or 1))) as pool:
        for r in pool.imap_unordered(one, jobs):
            rows.append(r)
            with open(part, "a") as f:
                f.write(json.dumps(r) + "\n")
            if r.get("error"):
                print(f"ERROR {r['game']} seed {r['seed']}: {r['error']}\n{r.get('trace', '')}")
                continue
            print(f"[{(time.time() - t0):.0f} s] {r['game']} seed {r['seed']} score {r['score']:.4f} "
                  f"levels {r['levels']} steps {r['actions']} card_levels {r.get('card_levels')} "
                  f"{r['sec_per_action']:.4f} s/action (env {r['env_sec_per_action']:.4f}) "
                  f"stopped {r['stopped']}", flush=True)
    ok = [r for r in rows if not r.get("error")]
    rows = ok + [r for r in rows if r.get("error")]
    if ok:
        tot_s = sum(r["play_seconds"] for r in ok)
        tot_a = sum(r["actions"] for r in ok)
        spa = tot_s / max(1, tot_a)
        print(f"\nseconds per action over {len(ok)} runs, {tot_a} actions: {spa:.4f} "
              f"(policy + engine; engine alone "
              f"{sum(r['env_sec_per_action'] * r['actions'] for r in ok) / max(1, tot_a):.4f}) "
              f"against the {A7_LIMIT} s threshold (A7): {'below' if spa <= A7_LIMIT else 'ABOVE'}"
              f"   [A7 is registered as 2,000 actions on each of ft09 and tu93; "
              f"{'this is that measurement' if sorted(games) == ['ft09', 'tu93'] and args.budget >= 2000 else 'this run is not it'}]")
    write(out, sorted(rows, key=lambda r: (r["game"], r["seed"])))
    trunc = [f"{r['game']}/{r['seed']}" for r in ok if r.get("time_truncated")]
    if trunc:
        print(f"TIME-TRUNCATED runs (stopped by --game-seconds before the budget): {trunc}")
    errs = [r for r in ok if r.get("diag", {}).get("their_prints", {}).get("Error")]
    if errs:
        print("runs where their choose_action raised (their fallback repeats the last action): "
              + ", ".join(f"{r['game']}/{r['seed']} {r['diag']['their_prints']['Error']}" for r in errs))
    unreset = [f"{r['game']}/{r['seed']}" for r in ok
               if len(r.get("diag", {}).get("level_wins_at_step", []))
               != r.get("diag", {}).get("level_wins_followed_by_graph_reset", 0)]
    print("level wins not followed by their graph reset (would mean the score mapping B2 failed): "
          + (", ".join(unreset) if unreset else "none"))
    missing = [(g, 1000 + s) for s in range(args.seeds) for g in games
               if (g, 1000 + s) not in {(r["game"], r["seed"]) for r in ok}]
    print(f"complete: {len(games) * args.seeds - len(missing)} of {len(games) * args.seeds} (game, seed) runs"
          + (f"; missing {missing[:10]}{' ...' if len(missing) > 10 else ''} - rerun with --resume" if missing else ""))
    if os.path.exists(part) and not missing:
        os.remove(part)


if __name__ == "__main__":
    main()
