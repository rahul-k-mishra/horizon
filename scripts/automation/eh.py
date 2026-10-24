"""
eh.py -- the effective-horizon bound of a level (docs/DESIGN.md, Section 5): Laidlaw, Russell and Dragan,
"Bridging RL Theory and Practice with the Effective Horizon", NeurIPS 2023 (arXiv:2304.09853),
Definition 5.1 (k-QVI-solvable) and Theorem 5.4 (the bound), on the deterministic MDP of a completed
search.  numpy only.

The MDP: states are the search's distinct states; the actions are the action list, all A of them in
every non-terminal state; a transition into a win state gives reward 1, every other transition 0; win and
loss states are absorbing with value 0 after entry; horizon T; the exploration policy is uniform random.
With time steps t = 1..T and V_{T+1} = 0:
    Q1_t(s, a)   = r(s, a) + Vrand_{t+1}(s'),   Vrand_t(s) = mean_a Q1_t(s, a)      (the random policy)
    Qk+1_t(s, a) = r(s, a) + max_a' Qk_{t+1}(s', a')                                 (one step of QVI)
    Q*_t(s, a)   = r(s, a) + V*_{t+1}(s'),       V*_t(s) = max_a Q*_t(s, a)
k-QVI-solvable: every policy greedy on Qk is optimal, checked exactly: at every (t, s) that some greedy
policy reaches from the start, every action in the argmax of Qk_t(s, .) has Q*_t(s, a) = V*_t(s).
Bound (Theorem 5.4):
    EH_k = k + max over t, s in S_t^opt, a of log_A( Qk_t(s,a) V*_t(s) / Delta_k_t(s)^2 ) + log_A( 6 ln(2 T A^k) )
where S_t^opt is the set of states some optimal policy visits at step t, Delta_k_t(s) = max_a Qk_t(s,a)
minus the largest Qk_t(s,a') over a' outside the argmax; terms with Qk_t(s,a) V*_t(s) = 0 and states
whose every action is in the argmax do not enter.  EH = min over the solvable k in KS of EH_k.
Statuses: "ok"; "goal beyond horizon" (V*_1(start) = 0: no win within T actions, EH infinite);
"not solvable" (no k in KS solvable, EH infinite); "underflow" (a random-policy value the bound needs
underflowed to 0 in double precision, EH not computed).  Ties use a relative tolerance of 1e-9.
"""
from __future__ import annotations

import math

import numpy as np

TOL = 1e-9
KS = (1, 2, 3)


def _ge(a, b):
    """a >= b up to a relative tolerance (values are probabilities in [0, 1])."""
    return a >= b - TOL * np.maximum(np.abs(a), np.abs(b))


def effective_horizon(nxt, rows, win, loss, start, T, A=None, ks=KS):
    """nxt: (m, A) int array, the successor state of each expanded state under each action; rows: (m,)
    the state id of each expanded state; win, loss: (n,) bool masks over state ids; start: the start's
    state id; T: horizon.  Returns dict(eh, k, status, per_k)."""
    nxt = np.asarray(nxt, dtype=np.int64)
    rows = np.asarray(rows, dtype=np.int64)
    win, loss = np.asarray(win, bool), np.asarray(loss, bool)
    n = len(win)
    A = A or nxt.shape[1]
    rowof = np.full(n, -1, dtype=np.int64)
    rowof[rows] = np.arange(len(rows))
    r = win[nxt].astype(np.float64)                         # reward of each (row, action)
    shape = (T + 2, n)
    Vrand, Vstar, W1, W2 = (np.zeros(shape) for _ in range(4))
    for t in range(T, 0, -1):
        Qr = r + Vrand[t + 1][nxt]
        Vrand[t][rows] = Qr.mean(axis=1)
        W1[t][rows] = Qr.max(axis=1)
        Vstar[t][rows] = (r + Vstar[t + 1][nxt]).max(axis=1)
        W2[t][rows] = (r + W1[t + 1][nxt]).max(axis=1)
    if Vstar[1][start] <= 0:
        return dict(eh=None, k=None, status="goal beyond horizon", per_k={})
    nonterm = ~(win | loss)
    X = {1: Vrand, 2: W1, 3: W2}

    def q(k, t, s_ids):
        rr = rowof[s_ids]
        return r[rr] + X[k][t + 1][nxt[rr]], r[rr] + Vstar[t + 1][nxt[rr]], nxt[rr]

    per_k = {}
    for k in ks:
        # solvability: follow every greedy action from the start
        G = np.array([start])
        solvable, underflow = True, False
        for t in range(1, T + 1):
            G = G[nonterm[G]]
            if not len(G):
                break
            qk, qs, nx = q(k, t, G)
            qmax = qk.max(axis=1, keepdims=True)
            amax = _ge(qk, qmax)
            vs = Vstar[t][G][:, None]
            if (vs[:, 0] > 0).any() and (qmax[:, 0][vs[:, 0] > 0] == 0).any():
                underflow = True
            if not np.all(_ge(qs, vs)[amax]):
                solvable = False
                break
            G = np.unique(nx[amax])
        if underflow:
            per_k[k] = dict(solvable=None, eh=None, status="underflow")
            continue
        if not solvable:
            per_k[k] = dict(solvable=False, eh=None, status="not solvable")
            continue
        # the bound: over states some optimal policy visits
        O = np.array([start])
        best = -math.inf
        for t in range(1, T + 1):
            O = O[nonterm[O]]
            if not len(O):
                break
            qk, qs, nx = q(k, t, O)
            vs = Vstar[t][O]
            qmax = qk.max(axis=1, keepdims=True)
            amax = _ge(qk, qmax)
            has_gap = ~amax.all(axis=1)
            if has_gap.any():
                rest = np.where(amax, -np.inf, qk)
                gap = qmax[:, 0] - rest.max(axis=1)
                sel = has_gap & (vs > 0)
                prod = qk[sel] * vs[sel][:, None]
                g2 = (gap[sel] ** 2)[:, None]
                ok = prod > 0
                if ok.any():
                    vals = np.log(prod[ok] / np.broadcast_to(g2, prod.shape)[ok]) / math.log(A)
                    best = max(best, float(vals.max()))
            opt = _ge(qs, vs[:, None])
            O = np.unique(nx[opt])
        if best == -math.inf:
            # every action is greedy-optimal wherever an optimal policy goes: one rollout suffices, H_k = k
            per_k[k] = dict(solvable=True, eh=float(k), status="ok, no gap on the optimal states")
            continue
        per_k[k] = dict(solvable=True, eh=k + best + math.log(6 * math.log(2 * T * A ** k)) / math.log(A), status="ok")
    ok = {k: v["eh"] for k, v in per_k.items() if v["eh"] is not None}
    if ok:
        k = min(ok, key=ok.get)
        return dict(eh=ok[k], k=k, status="ok", per_k=per_k)
    if any(v["status"] == "underflow" for v in per_k.values()):
        return dict(eh=None, k=None, status="underflow", per_k=per_k)
    return dict(eh=None, k=None, status="not solvable", per_k=per_k)
