"""
test_sdd.py -- synthetic tests of scripts/sdd.py: its AUROC against values worked out by hand, and its
simulation on fabricated clusters.  Reads no study-1 file and no row.
Run with warnings as errors (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe -W error scripts\\test_sdd.py
Expected last line: OK

Hand values:
    scores (1, 2, 3, 4), labels (F, F, T, T): every positive above every negative, AUROC 1.
    scores (1, 2, 2, 3), labels (F, T, F, T): pairs (pos, neg) = (2,1) 1, (2,2) 1/2, (3,1) 1, (3,2) 1, so 3.5/4 = 0.875.
    one class only: None.
Simulation: 60 fabricated clusters of 5 units where the search score separates the classes perfectly and
the mechanics score is constant, so Delta is 0.5 in every draw with both classes and its SE is 0; with
noisy scores the MDD at 104 clusters is smaller than at 26.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import sdd  # noqa: E402


def main():
    fails = []

    def check(c, msg):
        if not c:
            fails.append(msg)
            print("FAIL:", msg)

    check(abs(sdd.auroc([1, 2, 3, 4], [0, 0, 1, 1]) - 1.0) < 1e-12, "auroc perfect")
    check(abs(sdd.auroc([1, 2, 2, 3], [0, 1, 0, 1]) - 0.875) < 1e-12, "auroc with a tie")
    check(sdd.auroc([1, 2], [1, 1]) is None, "auroc one class")
    rng = np.random.default_rng(1)
    clean = []
    for _ in range(60):
        y = rng.random(5) < 0.5
        clean.append((y.astype(float), np.zeros(5), y))
    d, skipped = sdd.simulate(clean, n=26, sims=200, seed=3, workers=1)
    check(len(d) + skipped == 200 and all(abs(x - 0.5) < 1e-12 for x in d), "constant Delta of 0.5")
    se, mdd = sdd.mdd_from(d)
    check(se < 1e-12 and mdd < 1e-12, "zero SE gives zero MDD")
    noisy = []
    for _ in range(200):
        y = rng.random(5) < 0.5
        noisy.append((y + rng.normal(0, 1.5, 5), (y + rng.normal(0, 3.0, 5)).round(), y))
    d26, _ = sdd.simulate(noisy, n=26, sims=400, seed=4, workers=2)
    d104, _ = sdd.simulate(noisy, n=104, sims=400, seed=4, workers=2)
    m26, m104 = sdd.mdd_from(d26)[1], sdd.mdd_from(d104)[1]
    check(0 < m104 < m26, f"more clusters, smaller MDD ({m104:.4f} < {m26:.4f})")
    a, b = sdd.simulate(noisy, n=26, sims=100, seed=9, workers=1), sdd.simulate(noisy, n=26, sims=100, seed=9, workers=2)
    check(a == b, "the same seed gives the same draws with 1 or 2 workers")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
