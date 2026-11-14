"""
I1 (Rudakov, Shock & Cowley; external/rudakov_just_explore) on suites B and C: the boundary changes
C1-C5 of docs/I1_feasibility.md, applied around scripts/e1_rudakov_adapter.py.  Nothing inside
external/ is edited, and e1_rudakov_adapter.py is used unchanged.

    C1  the ARC shim (scripts/env_frame.py) is installed before e1_rudakov_adapter.play imports
        arc_agi, so their adapter's own Arcade/make/step calls reach the suite adapter
    C2  key map: I1 presses ACTION1-5 only (heuristic_agent.py:54-58), so the suite's accepted key map
        restricted to ids 1-5 (env_frame.I1_KEYS)
    C3  palette index k >= 16 is presented as k + 1: 16 is their status-bar marker
        (heuristic_agent.py:216, 248, 503)
    C4  the level count they see is min(levels_completed, 254): their FrameData.score is bounded
        at 254 (agents/structs.py:210); the true count is kept by the shim and written to the row
    C5  B1-B7 of scripts/e1_rudakov_adapter.py unchanged (docs/E1_rudakov_feasibility.md Section 5)

Their code needs requests and pydantic at import (agents/agent.py:9-11); install them in the suite
venv as in docs/W2_COMMANDS.md.  Called by scripts/run_suite.py (--modes i1).
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import env_frame as EF  # noqa: E402

LEVELS_CAP = 254
MARKER = 16


def shift_palette(canvas):
    """C3: indices >= 16 move up by one, so no game colour equals their marker 16."""
    c = np.asarray(canvas).astype(np.int16)
    return np.where(c >= MARKER, c + 1, c)


def install(suite, condition, seed, make_adapter):
    """C1-C4: the shim for one I1 run.  Returns the shim's list of created environments."""
    return EF.install_arc_shim(
        make_adapter, seed,
        key_map=lambda ad: EF.resolve_key_map(suite, condition, ad, ids=EF.I1_KEYS),
        row_offset=1, frame_transform=shift_palette, levels_cap=LEVELS_CAP)


def play(game, seed, budget, seconds, suite, condition, make_adapter):
    """One I1 run through the unchanged E1 adapter (C5).  Returns (row, shim env)."""
    made = install(suite, condition, seed, make_adapter)
    import e1_rudakov_adapter as E
    r = E.play(game, seed, budget, REPO, seconds)
    r.pop("_issued", None)
    env = made[-1] if made else None
    if env is not None:
        r["levels_true"] = env.levels              # C4: the count before the cap
        r["levels"] = env.levels
    r["i1_boundary"] = ["C1", "C2", "C3", "C4", "C5"]
    return r, env
