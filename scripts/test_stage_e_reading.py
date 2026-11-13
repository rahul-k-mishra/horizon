"""
test_stage_e_reading.py -- synthetic tests of the censored scores of scripts/stage_e_reading.py, on rows written
by hand (no stage E row exists when this is written).  Expected values worked by hand in the comments.
Run with warnings as errors (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe -W error scripts\\test_stage_e_reading.py
Expected last line: OK
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import stage_e_reading as E  # noqa: E402


def row(complete, seen, first_win=None, length=None):
    return dict(complete=complete, counts=dict(states_seen=seen, seen_at_first_win=first_win, solution_length=length))


def main():
    fails = []

    def check(c, msg):
        if not c:
            fails.append(msg)
            print("FAIL:", msg)

    small = row(True, 500, 40, 6)                 # complete, 500 states, win seen at 40, L = 6
    nowin = row(True, 800)                        # complete without a win
    big = row(False, 2_000_150, 1_500_000, 30)    # stopped at the seen cap; win seen at 1.5M states, L = 30
    slow = row(False, 700_000)                    # stopped by the time cap at 700,000 states, no win
    slowwin = row(False, 700_000, 650_000, 25)    # stopped by the time cap at 700,000 states, win at 650,000

    # H_C: -log10 min(R, C) when determined
    check(abs(E.h_c(small, 10_000) - (-math.log10(500))) < 1e-12, "small, C 10,000: -log10 500")
    check(abs(E.h_c(small, 100) - (-2.0)) < 1e-12, "small, C 100: at the ceiling, -2")
    check(abs(E.h_c(big, 1_000_000) - (-6.0)) < 1e-12, "big, C 1,000,000: -6")
    check(abs(E.h_c(slow, 300_000) - (-math.log10(300_000))) < 1e-12, "slow, C 300,000: determined, at the ceiling")
    check(math.isnan(E.h_c(slow, 1_000_000)), "slow, C 1,000,000: stopped before C, excluded")

    # L_C: -L when the first win came among the first C states; beyond C (INF) when determined without that
    check(E.l_c(small, 10_000) == -6.0, "small, C 10,000: L 6")
    check(E.l_c(small, 39) == E.INF, "small, C 39: the win came at state 40, beyond C")
    check(E.l_c(small, 40) == -6.0, "small, C 40: the win at exactly C counts")
    check(E.l_c(nowin, 10_000) == E.INF, "complete without a win: beyond C")
    check(E.l_c(big, 1_000_000) == E.INF, "big, C 1,000,000: win at 1.5M, beyond C")
    check(E.l_c(big, 2_000_000) == -30.0, "big, C 2,000,000: L 30")
    check(E.l_c(slow, 300_000) == E.INF, "slow, C 300,000: determined without a win, beyond C")
    check(math.isnan(E.l_c(slow, 1_000_000)), "slow, C 1,000,000: excluded")
    check(E.l_c(slowwin, 1_000_000) == -25.0, "slowwin, C 1,000,000: the win came before it stopped, L 25")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
