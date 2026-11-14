"""
agents_gvgai.py -- the boundary through which study 1's agents meet a GVGAI level (the frame contract,
docs/DESIGN_gvgai_draft.md; docs/PREREG.md, Section 3).

Study 1's files are copied unchanged under third_party/study1 (scripts/ and external/rudakov_just_explore/, each
byte-identical to study 1's tag prereg-v1.1; FROZEN below holds their git blob hashes and check_frozen refuses to
run on any difference).  Nothing in them is edited.  This file adds only what study 1 added for MiniGrid and
Procgen: an adapter with study 1's contract (env_frame.FrameEnv), a key map, and the call of each agent exactly as
study 1's runner made it (study 1, scripts/run_suite.py, function one).

The adapter (GVGAIAdapter):
    state        GVGAI's forward model (sim_gvgai): reset and restart copy the level start; a step is GVGAI's
                 StateObservation.advance on the current state, the same transition the search uses.
    grid         one cell per level cell (HorizonBridge.cellTypes): for every cell, the set of sprite types
                 drawn in it.  A sprite is drawn unless its hidden or invisible flag is set; a sprite counts in
                 the cell that holds its top-left corner.  The index of a cell is given to its set of types in
                 order of first appearance within the run, starting at 1 (0 is the canvas padding); the empty set
                 is a set like any other.  GVGAI gives the avatar one type whatever its facing, so its
                 orientations share one index, as study 1 merged MiniGrid's.  Two types drawn with the same image
                 get different indices (a known limit).  No cap on the number of indices.
    canvas       env_frame.to_canvas: the grid at rows 1.., columns 0.. of the 64 x 64 canvas, padding 0, because
                 the frozen code reads rows 1 to 62 only (study 1, scripts/g_motion.py:30-31).  A level taller
                 than 62 rows or wider than 64 columns cannot be placed and is refused (see the draft).
    actions      the avatar's available actions without ACTION_NIL, in GVGAI's order, as labels left, right,
                 down, up, use.
    key map      ARC id -> label: 1 up, 2 down, 3 left, 4 right, 5 use; id 7 has no GVGAI action and is not
                 offered (as study 1's macro map for MiniGrid: 1 north, 2 south, 3 west, 4 east).  I1 uses ids
                 1 to 5 only (study 1, env_frame.I1_KEYS).
    level_end    the game reports a win; the next episode begins at once on the same level and its first frame
                 is returned (study 1's ARC semantics: a won level is followed by the next).
    game_end     the game reports a loss, or GVGAI's own limit of 2,000 game ticks ends it; the final frame is
                 returned and the next step or restart begins a new episode on the same level.
    seed         seeds the agent only; the games are deterministic (docs/PREREG.md, Section 3).

run_unit(agent, game, level, seed, budget, seconds) plays one unit and returns the row's outcome and the
agent's statistics.  Agents: N (study 1's g_nav.play, mode nav), R (g_agent.play, mode hash_state), I1
(i1_suite_adapter.play through the unchanged e1_rudakov_adapter.py), Rand (uniform random actions over the
adapter's action list, numpy default_rng(seed)).
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import asdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
STUDY1 = os.path.join(REPO, "third_party", "study1")
STUDY1_SCRIPTS = os.path.join(STUDY1, "scripts")
if STUDY1_SCRIPTS not in sys.path:
    sys.path.insert(0, STUDY1_SCRIPTS)
import env_frame as EF  # noqa: E402  -- study 1's contract and shim, unchanged
import sim_gvgai  # noqa: E402

SUITE, CONDITION = "gvgai", "frame"
LABELS = {"ACTION_LEFT": "left", "ACTION_RIGHT": "right", "ACTION_DOWN": "down", "ACTION_UP": "up",
          "ACTION_USE": "use"}
KEY_MAP = {1: "up", 2: "down", 3: "left", 4: "right", 5: "use"}
# study 1's frozen files, their git blob hashes at study 1's tag prereg-v1.1 (study 1, docs/PREREG.md Section 5.4
# and scripts/run_suite.py EXPECTED_BLOBS for the six census files)
FROZEN = {
    "scripts/g_agent.py": "72585a4dbb926d4512ff9596f58118a176bb0646",
    "scripts/g_nav.py": "a8a7eb61e62a658c239b98e0224e3588a662d1a0",
    "scripts/g_motion.py": "14018512a5c6b0efc81aed61c5466654d338be0b",
    "scripts/g_control_probe.py": "d5ff2a4dc77b9e1148929e7db03fe99a9d2b0bf8",
    "scripts/g_nav_run.py": "2cc0146a697e525e5873d4e29cb80f4ae8bd6297",
    "scripts/g_census_table.py": "488feaca9c10985c4d0ff62791ceb4fa6fa6b9a8",
    "scripts/env_frame.py": "bb3ff60acf88c220ec64e287c6c1d6bb899f879b",
    "scripts/e1_rudakov_adapter.py": "39ab52f82f2fef3460ce83cb9db30d892b571d5b",
    "scripts/i1_suite_adapter.py": "9d8a18548b958e70b1365b2eacb25d25f83284ba",
}
AGENT_MODES = {"N": "nav", "R": "hash_state", "I1": "i1", "Rand": "rand"}

# study 1's shim resolves a key map by (suite, condition) from env_frame.KEY_MAPS; the GVGAI entry is added to
# that dictionary at run time, so env_frame.py itself is not edited
EF.KEY_MAPS.setdefault((SUITE, CONDITION), dict(KEY_MAP))


def blob_hash(path):
    import hashlib  # noqa: PLC0415
    with open(path, "rb") as f:
        data = f.read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def check_frozen():
    """{file: (got, expected)} for every frozen file whose bytes differ from study 1's; {} when all agree."""
    bad = {}
    for rel, h in FROZEN.items():
        got = blob_hash(os.path.join(STUDY1, rel))
        if got != h:
            bad[rel] = (got, h)
    return bad


class GVGAIAdapter(EF.FrameEnv):
    suite = SUITE

    def __init__(self, game, level, cache=None, games_dir=None):
        self.game, self.level = game, int(level)
        self.cache = cache or os.environ.get("HORIZON_GVGAI_CACHE") or \
            os.path.join(os.environ.get("HORIZON_TMP", "/tmp"), "horizon-gvgai")
        self.bridge = sim_gvgai.start_jvm(self.cache)
        gf, lf = sim_gvgai.level_paths(game, level, games_dir)
        self.root = self.bridge.load(gf.replace("\\", "/"), lf.replace("\\", "/"), 0)
        self.jactions = list(self.bridge.actions(self.root))
        self.actions = [LABELS[str(a)] for a in self.jactions]
        self.palette = {}
        self.state = None
        self.need_reset = False
        self.episodes = 0
        self.steps = 0
        g = self._grid_of(self.root, assign=False)
        self.grid_shape = list(g.shape)
        if g.shape[0] + 1 > EF.CANVAS - 1 or g.shape[1] > EF.CANVAS:
            raise ValueError(f"{game} level {level}: grid {g.shape[0]} x {g.shape[1]} does not fit rows 1..62 and "
                             f"columns 0..63 of the canvas")

    def _grid_of(self, so, assign=True):
        flat = list(self.bridge.cellTypes(so))
        w, h = flat[0], flat[1]
        out = np.zeros((h, w), dtype=np.int16)
        k = 2
        for i in range(h):
            for j in range(w):
                n = flat[k]
                key = tuple(flat[k + 1:k + 1 + n])
                k += 1 + n
                if assign:
                    if key not in self.palette:
                        self.palette[key] = len(self.palette) + 1
                    out[i, j] = self.palette[key]
        return out

    def _new_episode(self):
        self.state = self.root.copy()
        self.need_reset = False
        self.episodes += 1

    def reset(self, seed):
        self.seed = int(seed)
        self._new_episode()
        return self._grid_of(self.state)

    def restart(self):
        self._new_episode()
        return self._grid_of(self.state)

    def step(self, i):
        if self.need_reset:
            self._new_episode()
        self.state.advance(self.jactions[i])
        self.steps += 1
        st = int(self.bridge.status(self.state))
        if st == sim_gvgai.STATUS_WIN:
            self._new_episode()
            return self._grid_of(self.state), True, False
        if st in (sim_gvgai.STATUS_LOSS, sim_gvgai.STATUS_TICK_LIMIT):
            g = self._grid_of(self.state)
            self.need_reset = True
            return g, False, True
        return self._grid_of(self.state), False, False

    def record(self):
        return dict(suite=SUITE, game=self.game, level=self.level, condition=CONDITION, palette="cell-type-set",
                    n_colours=len(self.palette), crop=None, grid=self.grid_shape, action_list=list(self.actions),
                    episodes=self.episodes, steps=self.steps, gvgai_commit=sim_gvgai.GVGAI_COMMIT,
                    adapter_blob=blob_hash(os.path.abspath(__file__)), frozen={k: v for k, v in FROZEN.items()})


def key_map_for(adapter, ids=None):
    """{ARC id: adapter action index} for the labels this level offers."""
    return {k: adapter.actions.index(lab) for k, lab in KEY_MAP.items()
            if lab in adapter.actions and (ids is None or k in ids)}


def run_unit(agent, game, level, seed, budget, seconds, cache=None, games_dir=None):
    """One (agent, game, level, seed).  Returns dict(level1_completed, levels, actions, first_level_end,
    cut_by_cap, seconds, agent_stats); agent_stats is for the record only (docs/AUTOMATION.md, Section 5)."""
    bad = check_frozen()
    if bad:
        raise RuntimeError(f"study 1's frozen files differ from their registered blobs: {bad}")
    import logging  # noqa: PLC0415
    logging.disable(logging.CRITICAL)
    unit_name = f"{game}:{int(level)}"

    def make(_name):
        return GVGAIAdapter(game, level, cache, games_dir)
    t0 = time.time()
    env = None
    stats = {}
    if agent == "Rand":
        ad = make(unit_name)
        ad.reset(seed)
        rng = np.random.default_rng(int(seed))
        levels, first = 0, None
        n = 0
        while n < budget and time.time() - t0 < seconds:
            _g, le, _ge = ad.step(int(rng.integers(len(ad.actions))))
            n += 1
            if le:
                levels += 1
                first = first if first is not None else n
        actions = n
        stats = dict(adapter=ad.record())
    elif agent == "I1":
        import i1_suite_adapter as I  # noqa: PLC0415
        r, env = I.play(unit_name, seed, budget, seconds, SUITE, CONDITION, make)
        actions, levels = int(r.get("actions", 0) or 0), int(r.get("levels", 0) or 0)
        first = env.first_level_end if env is not None else None
        stats = {k: r[k] for k in ("stopped", "time_truncated", "play_seconds", "sec_per_action", "diag") if k in r}
    else:
        made = EF.install_arc_shim(make, seed, key_map=lambda ad: key_map_for(ad), row_offset=1)
        import g_agent as A  # noqa: PLC0415
        from g_nav_run import MODES  # noqa: PLC0415
        mode = AGENT_MODES[agent]
        cfg_d = asdict(A.Config(max_actions=budget, seed=seed, **MODES[mode]))
        if mode == "nav":
            import g_nav  # noqa: PLC0415
            r = g_nav.play(unit_name, A.Config(**cfg_d), STUDY1, seconds=seconds)
        else:
            r = A.play(unit_name, A.Config(**cfg_d), STUDY1, seconds=seconds)
        env = made[-1] if made else None
        actions, levels = int(r.get("actions", 0) or 0), int(r.get("levels", 0) or 0)
        first = env.first_level_end if env is not None else None
        if "error" in r:
            raise RuntimeError(f"{agent} on {unit_name}: {r['error']}")
        stats = {k: r[k] for k in ("diag",) if k in r}
    if env is not None:
        rec = env.adapter.record()
        rec["key_map"] = {str(k): env.adapter.actions[i] for k, i in env.key_map.items()}
        rec["canvas"] = dict(size=EF.CANVAS, row_offset=env.row_offset, padding=EF.PAD)
        stats["adapter"] = rec
    return dict(level1_completed=levels >= 1, levels=levels, actions=actions, first_level_end=first,
                cut_by_cap=actions < budget, seconds=round(time.time() - t0, 3), agent_stats=stats)
