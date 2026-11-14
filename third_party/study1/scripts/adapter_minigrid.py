"""
Suite-B adapter (MiniGrid + BabyAI), docs/PREREG.md v1 Section 3.2.  Runs in .venv_games
(Python 3.11.9, minigrid 3.1.0, gymnasium 1.3.0).  Plays no game on import.

    construction   gymnasium.make(id, render_mode="rgb_array", highlight=False, tile_size=8,
                   agent_pov=False)  (minigrid/minigrid_env.py:43-47); frame = env.render(), the full
                   grid (minigrid_env.py:736-742)
    palette        tile-pattern: each distinct 8 x 8 RGB tile gets one index, in order of first
                   appearance within the run, starting at 1 (0 is the canvas padding); the four
                   agent orientations, rendered in advance with Grid.render_tile(None, agent_dir=d,
                   highlight=False, tile_size=8) (minigrid/core/grid.py:145-194), share one index.
                   An agent tile over a non-empty cell (an open door) is a distinct pattern.  No cap.
    grid           frame height / 8 x frame width / 8, per environment; no crop
    conditions     raw: the primitive actions left, right, forward, pickup, drop, toggle, done
                   (0-6, minigrid/core/actions.py:9-20); Dynamic-Obstacles offers 0-2 only
                   (envs/dynamicobstacles.py:104).
                   macro: north, south, east, west = turn to face (fewest turns, at most 2) then
                   forward, the frame after the forward returned; a sub-step that ends the episode
                   stops the macro.  pickup, drop, toggle, done passed through (not on
                   Dynamic-Obstacles).  One macro counts as one adapter action; primitive steps are
                   counted separately in the record.  The macro reads env.unwrapped.agent_dir to
                   choose the turns: it is part of the action's definition, not an observation.
    seeding        episode_seeding "replay" (accepted by RKM 27 Sep 2026, PREREG v1.1 draft; ADAPTER_
                   FEASIBILITY item 14): episode k is reset with seed seed*100000 + k; k advances only
                   on a success; restart() (the ARC RESET) replays episode k's layout.  "unseeded"
                   (PREREG v1 as tagged) is kept for reference.  BABYAI_DONE_ACTIONS must be unset.
    level_end      the episode terminates with reward > 0; the next episode begins at once and its
                   first frame is returned (ARC semantics: a won level is followed by the next)
    game_end       termination with reward <= 0, or truncation; the final frame is returned and the
                   next step or restart() begins a new episode
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import env_frame as EF  # noqa: E402

TILE = 8
MAKE_KW = dict(render_mode="rgb_array", highlight=False, tile_size=TILE, agent_pov=False)
RAW = ["left", "right", "forward", "pickup", "drop", "toggle", "done"]
MACRO_MOVES = ["north", "south", "east", "west"]
PASS = ["pickup", "drop", "toggle", "done"]
DIR = {"east": 0, "south": 1, "west": 2, "north": 3}      # minigrid/core/constants.py:49-58
PRIM = {n: i for i, n in enumerate(RAW)}                     # minigrid/core/actions.py:9-20


class MinigridAdapter(EF.FrameEnv):
    suite = "minigrid"

    def __init__(self, env_id, condition, episode_seeding="replay"):
        if condition not in ("raw", "macro"):
            raise ValueError(condition)
        if episode_seeding not in ("unseeded", "replay"):
            raise ValueError(episode_seeding)
        if os.environ.get("BABYAI_DONE_ACTIONS"):
            raise RuntimeError("BABYAI_DONE_ACTIONS is set; PREREG.md Section 3.2 requires it unset")
        import gymnasium
        import minigrid  # noqa: F401  (registers the ids)
        from minigrid.core.grid import Grid
        self.env_id, self.condition, self.episode_seeding = env_id, condition, episode_seeding
        self.env = gymnasium.make(env_id, **MAKE_KW)
        n = int(self.env.action_space.n)
        if condition == "raw":
            self.actions = RAW[:n]
        else:
            self.actions = MACRO_MOVES + (PASS if n > 3 else [])
        self._agent_tiles = {Grid.render_tile(None, agent_dir=d, highlight=False, tile_size=TILE).tobytes()
                             for d in range(4)}
        self.palette = {}                   # tile bytes (or "AGENT") -> index >= 1
        self.seed = None
        self.episode = 0
        self.need_reset = False
        self.prim_steps = 0
        self.grid_shape = None

    # ---- frame -> grid
    def _grid(self):
        f = np.asarray(self.env.render())
        h, w = f.shape[0] // TILE, f.shape[1] // TILE
        tiles = f[:h * TILE, :w * TILE].reshape(h, TILE, w, TILE, 3).transpose(0, 2, 1, 3, 4)
        out = np.zeros((h, w), dtype=np.int16)
        for i in range(h):
            for j in range(w):
                b = tiles[i, j].tobytes()
                key = "AGENT" if b in self._agent_tiles else b
                if key not in self.palette:
                    self.palette[key] = len(self.palette) + 1
                out[i, j] = self.palette[key]
        self.grid_shape = [h, w]
        return out

    # ---- episodes
    def _episode_seed(self):
        return self.seed * 100000 + self.episode

    def _new_episode(self, advance):
        if advance:
            self.episode += 1
        if self.episode == 0 or self.episode_seeding == "replay":
            self.env.reset(seed=self._episode_seed() if self.episode_seeding == "replay" else self.seed)
        else:
            self.env.reset()
        self.need_reset = False

    def reset(self, seed):
        self.seed = int(seed)
        self.episode = 0
        self.env.reset(seed=self._episode_seed() if self.episode_seeding == "replay" else self.seed)
        self.need_reset = False
        return self._grid()

    def restart(self):
        """ARC RESET.  unseeded: a new episode (the environment RNG continues).  replay: the current
        episode's layout again (its registered episode seed)."""
        self._new_episode(advance=self.episode_seeding == "unseeded")
        return self._grid()

    def _prim(self, a):
        self.prim_steps += 1
        _obs, rew, term, trunc, _info = self.env.step(a)
        return float(rew), bool(term), bool(trunc)

    def step(self, i):
        if self.need_reset:
            # after a failure: replay keeps episode k (k advances only on success); unseeded moves on
            self._new_episode(advance=self.episode_seeding == "unseeded")
        label = self.actions[i]
        seq = []
        if self.condition == "macro" and label in DIR:
            d = (DIR[label] - int(self.env.unwrapped.agent_dir)) % 4
            seq = {0: [], 1: [PRIM["right"]], 2: [PRIM["right"], PRIM["right"]], 3: [PRIM["left"]]}[d]
            seq = seq + [PRIM["forward"]]
        else:
            seq = [PRIM[label]]
        rew, term, trunc = 0.0, False, False
        for a in seq:
            rew, term, trunc = self._prim(a)
            if term or trunc:
                break
        if term and rew > 0:
            self._new_episode(advance=True)
            return self._grid(), True, False
        if term or trunc:
            g = self._grid()
            self.need_reset = True
            return g, False, True
        return self._grid(), False, False

    def record(self):
        return dict(suite="minigrid", game=self.env_id, condition=self.condition, palette="tile8",
                    n_colours=len(self.palette), crop=None, grid=self.grid_shape, action_list=list(self.actions),
                    episode_seeding=self.episode_seeding, primitive_steps=self.prim_steps,
                    make_kwargs=MAKE_KW, adapter_blob=EF.git_blob_hash("scripts/adapter_minigrid.py"),
                    env_frame_blob=EF.git_blob_hash("scripts/env_frame.py"), frozen=EF.frozen_hashes())

    def close(self):
        try:
            self.env.close()
        except Exception:
            pass
