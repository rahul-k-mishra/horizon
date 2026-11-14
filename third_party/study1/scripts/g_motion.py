"""
BRUTUS-G motion detector, version 2: WHAT SHIFT EXPLAINS THE CHANGE, not which colour moved.

Version 1 judged one colour at a time and failed on multi-coloured sprites (tu93: a body plus a
single facing-marker cell that jumps as the player turns) and on pieces sliding across coloured
ground (dc22: the ground seems to move the opposite way).  Here every small offset d is tried,
and for each, the changed cells p with  after[p] == before[p - d]  are counted: the cells the
offset explains.  The best offset is the motion; the cells it explains are the object's new
position.  No colour is chosen at all.

Rows 0 and 63 are left out (bars and counters live there).
"""
from __future__ import annotations

import numpy as np

MAX_STEP = 10


def best_shift(before, after, min_cells=2):
    """(offset (dx, dy), cells of the object at its new position, weight), or (None, set(), 0).

    Every colour whose vanished cells and reappeared cells are the same shape, shifted, casts a
    vote for that shift - weighted by how many of its cells moved AND by what share of all its
    cells on screen changed.  Ground stays put almost everywhere, so its share is tiny and its
    vote nearly vanishes; a sprite's colours change almost entirely.  MEASURED: an unweighted
    count let plain floor match itself under almost any offset and produced impossible diagonal
    moves on dc22 and ls20.  A multi-coloured sprite whose marker cell jumps as it turns still
    works, because its body colour moves cleanly and carries the vote."""
    b = before[1:63].astype(np.int16)
    a = after[1:63].astype(np.int16)
    diff = b != a
    if int(diff.sum()) < min_cells:
        return None, set(), 0.0
    votes, cells_for = {}, {}
    for c in np.unique(np.concatenate([b[diff], a[diff]])):
        gone = np.argwhere((b == c) & (a != c))
        came = np.argwhere((a == c) & (b != c))
        if len(gone) == 0 or len(came) == 0 or len(gone) > 600 or len(came) > 600:
            continue
        # the shift that lines up the most of this colour's cells.  MEASURED on tu93: the
        # player's facing marker moves inside its body when it turns, so the body is never an
        # EXACT shifted copy on a vertical move; demanding exactness threw the body out and let
        # the one-cell marker win with a false step of 8 instead of 6.  Most cells lining up is
        # enough.
        if len(gone) * len(came) <= 4096:
            offs = {}
            for gy, gx in gone:
                for cy, cx in came:
                    k = (int(cx - gx), int(cy - gy))
                    offs[k] = offs.get(k, 0) + 1
            (dx, dy), _n = max(offs.items(), key=lambda kv: kv[1])
        else:
            d = came.mean(0) - gone.mean(0)
            dy, dx = int(round(d[0])), int(round(d[1]))
        if (dx, dy) == (0, 0) or abs(dx) > MAX_STEP or abs(dy) > MAX_STEP:
            continue
        came_set = {(int(y), int(x)) for y, x in came}
        matched = sum(1 for y, x in gone if (int(y) + dy, int(x) + dx) in came_set)
        if matched < max(1, int(0.7 * max(len(gone), len(came)))):
            continue
        share = matched / max(1, int((b == c).sum()))
        w = matched * share
        votes[(dx, dy)] = votes.get((dx, dy), 0.0) + w
        cells_for.setdefault((dx, dy), set()).update((int(y) + 1, int(x)) for y, x in came)
    if not votes:
        return None, set(), 0.0
    d = max(votes, key=votes.get)
    return d, cells_for[d], votes[d]
