"""
The environment contract of docs/PREREG.md v1 Section 3, and the shim that presents any adapter to
the frozen ARC code (scripts/g_agent.py, g_nav.py) without editing it (docs/ADAPTER_FEASIBILITY.md).

Contract (every adapter implements FrameEnv):
    reset(seed) -> grid                      integer colour-index array (h, w), palette indices >= 1
    step(i) -> grid, level_end, game_end     i indexes self.actions
    restart() -> grid                        what the ARC "RESET" does on this suite
    actions                                  the fixed action list (labels)
    record() -> dict                         the adapter record: palette, n_colours, crop, grid,
                                             action_list, suite-specific settings, blob hashes of
                                             the adapter file and the frozen census files
Palette index 0 is reserved for the padding of the 64 x 64 canvas (to_canvas).

The ARC shim (install_arc_shim) puts stand-ins for the modules arc_agi and arcengine into
sys.modules, so that g_agent.play's `from arc_agi import Arcade` and `from arcengine import
GameAction` resolve to an Arcade whose make(game) returns an adapter-backed environment exposing
the fields g_agent.py and g_nav.py read: observation_space / step() results with frame, state.name,
levels_completed, available_actions.  The key map (ARC action id -> adapter action index) and the
canvas placement are parameters that PREREG v1 did not register; the values used by the runners are
the ones registered in PREREG v1.1 (proposed in docs/ADAPTER_FEASIBILITY.md).  The fidelity check
(scripts/fidelity_check.py) drives the adapters directly and does not use the shim.

Needs only numpy and the standard library (runs in .venv, .venv_games and .venv_procgen).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# frozen census files (docs/PREREG.md Section 5.4)
FROZEN_FILES = ("scripts/g_agent.py", "scripts/g_nav.py", "scripts/g_motion.py",
                "scripts/g_control_probe.py", "scripts/g_nav_run.py", "scripts/g_census_table.py")
PAD = 0                     # canvas padding index; adapter palettes start at 1
CANVAS = 64

# Key maps accepted by RKM on 27 Sep 2026 (docs/ADAPTER_FEASIBILITY.md items 9-11; PREREG v1.1 draft):
# ARC action id -> adapter action label.  The frozen code presses only ids 1, 2, 3, 4, 5, 7
# (g_control_probe.py:47); id 6 (click) is never offered.  A label the environment lacks is dropped.
KEY_MAPS = {
    ("minigrid", "raw"): {1: "left", 2: "right", 3: "forward", 4: "pickup", 5: "drop", 7: "toggle"},
    ("minigrid", "macro"): {1: "north", 2: "south", 3: "west", 4: "east", 5: "pickup", 7: "toggle"},
    ("procgen", "center_off"): {1: 5, 2: 3, 3: 1, 4: 7, 5: 9, 7: 10},
    ("procgen", "center_on"): {1: 5, 2: 3, 3: 1, 4: 7, 5: 9, 7: 10},
}
I1_KEYS = (1, 2, 3, 4, 5)          # I1 maps only ACTION1-5 (heuristic_agent.py:54-58); item 18


def resolve_key_map(suite, condition, adapter, ids=None):
    """{ARC id: adapter action index} for the labels this environment offers."""
    out = {}
    for k, label in KEY_MAPS[(suite, condition)].items():
        if ids is not None and k not in ids:
            continue
        if label in adapter.actions:
            out[k] = adapter.actions.index(label)
    return out


def git_blob_hash(path):
    """The git blob id of a file as `git hash-object` computes it (with the repository's filters);
    falls back to hashing the raw bytes if git is unavailable."""
    full = path if os.path.isabs(path) else os.path.join(REPO, path)
    try:
        out = subprocess.run(["git", "hash-object", full], cwd=REPO, capture_output=True, text=True,
                             timeout=30)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    data = open(full, "rb").read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def frozen_hashes():
    return {f: git_blob_hash(f) for f in FROZEN_FILES}


class FrameEnv:
    """Base class of the adapters.  Subclasses set self.actions and implement the methods."""
    suite = "?"
    actions: list = []

    def reset(self, seed):
        raise NotImplementedError

    def step(self, i):
        raise NotImplementedError

    def restart(self):
        raise NotImplementedError

    def record(self):
        raise NotImplementedError

    def close(self):
        pass


def to_canvas(grid, row_offset=1, pad=PAD):
    """Place an adapter grid on the 64 x 64 canvas the frozen code expects (it reads rows 1-62 only,
    scripts/g_motion.py:30-31).  A grid smaller than 62 x 64 goes at rows row_offset.., columns 0..;
    a 64 x 64 grid is returned unchanged (its rows 0 and 63 are then invisible to the frozen code)."""
    g = np.asarray(grid)
    h, w = g.shape
    if (h, w) == (CANVAS, CANVAS):
        return g.astype(np.int16)
    if h + row_offset > CANVAS - 1 or w > CANVAS:
        raise ValueError(f"grid {h}x{w} does not fit rows {row_offset}..62 of the canvas")
    c = np.full((CANVAS, CANVAS), pad, dtype=np.int16)
    c[row_offset:row_offset + h, :w] = g
    return c


# ---------------------------------------------------------------- ARC shim
class _State:
    def __init__(self, name):
        self.name = name


class _Raw:
    """What g_agent.py / g_nav.py read from an observation: frame, state.name, levels_completed,
    available_actions (g_agent.py:324-337, 427, 493-530; g_control_probe.py:50-56)."""

    def __init__(self, frame, state, levels, available):
        self.frame = [frame]
        self.state = _State(state)
        self.levels_completed = levels
        self.available_actions = list(available)
        self.guid = None                  # read by the E1 adapter's to_their_frame (I1)
        self.full_reset = False


class _GameAction:
    """Stand-in for arcengine.GameAction: RESET (0) and ACTION1-ACTION7 (1-7), from_id()."""

    def __init__(self, i, name):
        self.value, self.name = i, name

    def __repr__(self):
        return self.name


class _GameActionNS:
    RESET = _GameAction(0, "RESET")

    @classmethod
    def from_id(cls, i):
        return getattr(cls, "RESET" if int(i) == 0 else f"ACTION{int(i)}")


for _k in range(1, 8):
    setattr(_GameActionNS, f"ACTION{_k}", _GameAction(_k, f"ACTION{_k}"))


class _Info:
    def __init__(self, game_id):
        self.game_id = game_id


class ShimEnv:
    """An adapter presented as an arc_agi environment.  key_map: {ARC action id: adapter action index}.
    RESET calls adapter.restart().  A level end increments levels_completed and keeps the game
    running; a game end sets state GAME_OVER until the next RESET.
    frame_transform and levels_cap exist for I1's boundary (docs/I1_feasibility.md C3, C4).
    steps counts every step (RESET included) and first_level_end the step of the first level end."""

    def __init__(self, adapter, seed, key_map, row_offset=1, frame_transform=None, levels_cap=None,
                 game_id="game"):
        self.adapter, self.key_map, self.row_offset = adapter, dict(key_map), row_offset
        self.frame_transform, self.levels_cap = frame_transform, levels_cap
        self.levels, self.state = 0, "NOT_FINISHED"
        self.steps, self.first_level_end = 0, None
        self.available = sorted(self.key_map)
        self.environment_info = _Info(game_id)
        self.observation_space = self._raw(adapter.reset(seed))

    def _raw(self, grid):
        c = to_canvas(grid, self.row_offset)
        if self.frame_transform is not None:
            c = self.frame_transform(c)
        lv = self.levels if self.levels_cap is None else min(self.levels, self.levels_cap)
        return _Raw(c, self.state, lv, self.available)

    def step(self, action, data=None):
        a = int(getattr(action, "value", action))
        self.steps += 1
        if a == 0:
            self.state = "NOT_FINISHED"
            self.observation_space = self._raw(self.adapter.restart())
            return self.observation_space
        if a not in self.key_map:
            raise ValueError(f"action {a} is not offered on this suite (offered: {self.available})")
        grid, level_end, game_end = self.adapter.step(self.key_map[a])
        if level_end:
            self.levels += 1
            if self.first_level_end is None:
                self.first_level_end = self.steps
        self.state = "GAME_OVER" if game_end else "NOT_FINISHED"
        self.observation_space = self._raw(grid)
        return self.observation_space


class _Card:
    environments: list = []


def install_arc_shim(make_adapter, seed, key_map, row_offset=1, frame_transform=None, levels_cap=None):
    """Register stand-in arc_agi / arcengine modules.  make_adapter(game) -> FrameEnv.  key_map is a
    dict {ARC id: adapter action index} or a callable adapter -> such a dict.  Returns the list of
    ShimEnv objects created (for the runner's adapter records)."""
    made = []

    class Arcade:
        def __init__(self, operation_mode="offline", environments_dir=None, **kw):
            self.environments_dir = environments_dir

        def open_scorecard(self, tags=None, **kw):
            return "shim-card"

        def make(self, game, scorecard_id=None, **kw):
            ad = make_adapter(game)
            km = key_map(ad) if callable(key_map) else key_map
            env = ShimEnv(ad, seed, km, row_offset, frame_transform, levels_cap, game_id=game)
            made.append(env)
            return env

        def close_scorecard(self, card, **kw):
            return _Card()

    arc_agi = types.ModuleType("arc_agi")
    arc_agi.Arcade = Arcade
    arcengine = types.ModuleType("arcengine")
    arcengine.GameAction = _GameActionNS
    sys.modules["arc_agi"] = arc_agi
    sys.modules["arcengine"] = arcengine
    return made
