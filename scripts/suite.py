"""
suite.py -- the one definition of HORIZON's game lists (docs/PREREG.md, Section 4), read by every script that
needs them, so that no script keeps a copy.

    deterministic()   the 30 eligible games: the single-player grid-physics games of docs/design/vgdl_scan.json
                      (scripts/vgdl_scan.py) marked deterministic, in name order.
    pilot()           the 4 pilot games, drawn by scripts/draw_pilot.py with numpy default_rng(20261024) from the
                      30 deterministic games (logs/draw_pilot.log).  The draw is made on the 30 games, as it was on
                      24 October 2026, before the fit rule existed; the fit rule does not redraw it (see below).
    level_size(g, l)  (rows, columns) of a level as GVGAI reads it (BasicGame.buildStringLevel,
                      third_party/gvgai/src/core/game/BasicGame.java:106-131): rows = the number of lines of the
                      level file (tools/IO.readFile, BufferedReader.readLine); columns = the length of the first
                      line, shorter lines being padded with blanks.  One cell per level cell (PREREG Section 3).
    FRAME_ROWS, FRAME_COLS
                      the largest grid the frame contract can present: the 64 x 64 canvas of study 1's
                      env_frame.py (CANVAS), with the grid at rows 1 onward (row offset 1) and the frozen agent code
                      reading rows 1 to 62 only (study 1, scripts/g_motion.py:30-31; env_frame.to_canvas), so 62
                      rows and 64 columns.
    fits(g)           the fit rule [decided 14 Nov 2026]: every level 0 to 4 of the game has at most FRAME_ROWS
                      rows and at most FRAME_COLS columns.
    confirmatory()    the confirmatory games: deterministic() minus pilot() minus every game that fails fits().

Reads only committed files.  Plays no game.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
SCAN = os.path.join(REPO, "docs", "design", "vgdl_scan.json")
GAMES_DIR = os.path.join(REPO, "third_party", "gvgai", "examples", "gridphysics")
LEVELS = range(5)

# study 1's frame contract (third_party/study1/scripts/env_frame.py: CANVAS = 64; to_canvas puts the grid at
# row_offset 1 and refuses h + row_offset > CANVAS - 1 or w > CANVAS)
CANVAS, ROW_OFFSET = 64, 1
FRAME_ROWS, FRAME_COLS = CANVAS - 1 - ROW_OFFSET, CANVAS


def deterministic():
    with open(SCAN, encoding="utf-8") as f:
        scan = json.load(f)
    return sorted(g["game"] for g in scan["games"] if g["deterministic"])


def pilot():
    import draw_pilot  # noqa: PLC0415 -- the registered draw, not a copy of it
    games = deterministic()
    idx = np.random.default_rng(draw_pilot.SEED).choice(len(games), draw_pilot.N_PILOT, replace=False)
    return sorted(games[i] for i in idx)


def level_lines(game, level):
    with open(os.path.join(GAMES_DIR, f"{game}_lvl{int(level)}.txt"), encoding="utf-8", newline="") as f:
        text = f.read()
    # BufferedReader.readLine ends a line at \n, \r or \r\n and returns no empty last line after a final break
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")[:-1] if text.endswith(("\n", "\r")) else \
        text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def level_size(game, level):
    lines = level_lines(game, level)
    return len(lines), len(lines[0])


def fits(game):
    return all(r <= FRAME_ROWS and c <= FRAME_COLS for r, c in (level_size(game, lv) for lv in LEVELS))


def confirmatory():
    p = set(pilot())
    return [g for g in deterministic() if g not in p and fits(g)]
