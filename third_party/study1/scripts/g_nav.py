"""
G-NAV: a navigation planner that verifies itself on the game it is playing.

WHY (measured, g_decompose.py on the 4-seed held-out ablation, 1,088 runs): every held-out point
comes from level 1; level 2 was won 14-16 times at 40-1,000x the human action count (worth 0);
level 3 was never won.  The formula pays 100*(human/agent)^2 per level, weighted by level index,
so the score is in winning levels 2+ at near-human counts, which needs a model and a goal.

WHAT IT ASSUMES (each has a counter, so you see it fail):
  T1 a controlled object with fixed step vectors      -> avatar_found, step_mispredict
  T2 blocked moves are static per cell                -> step_bumped, wall_contradicted, replans
  T3 the level ends when the avatar reaches a place   -> goal_recorded (with the colours),
                                                         goal_reached_no_end
  T4 the next level keeps the goal                    -> goal_confirmed vs goal_reached_no_end
  T5 the level is winnable by walking                 -> frontier_exhausted, fallback_<reason>
Click-only games never enter here (no keys); the explorer plays them unchanged.

HOW:
  learn      press each key once (the shift it causes is its step vector; the shifted cells are
             the avatar); keys with no effect are retried from later positions, three times.
  model      a lattice of avatar anchors; an edge (pos, key) is passable unless it bumped before
             (blocked), or its destination shows a colour that has bumped >=2 times and never
             been walked on (wall), or a colour present where the avatar died >=2 times (deadly).
             Unknown edges are OPTIMISTIC, so exploration is a path search, not an enumeration.
  plan       breadth-first over the lattice on the CURRENT frame.  Target order: the nearest cell
             of a goal colour recorded at an earlier level end, else the nearest position never
             stood on (the frontier).  One step is executed, then the frame is checked against
             the prediction; a bump or a surprise marks the edge and replans.
  goal       when a level ends, the colours the avatar had just stepped onto (and the ring around
             them) are recorded, most recent first, and tried on later levels.
  fallback   when there is no avatar, no reachable frontier, too many surprises, or 150 steps
             without a new position, the hook goes quiet for the rest of the level and the
             explorer (hash_state) plays.  It wakes up on the next level.

Nothing here reads a game's source.  Run through g_nav_run.py.

E9 (docs/E9_protocol.md): an optional ColourOracle hands the planner the true goal in its own
language, a colour set, at each level start, for tu93 and dc22 only (source-informed train games).
It replaces goal_hyps for that level in _replan step 1 and lifts the goal_tries cap; nothing else.
With oracle=None (mode nav) every line below behaves exactly as before; scripts/e9_equiv.py checks
this against the pre-E9 file.
"""
from __future__ import annotations

import random
from collections import Counter, deque

import numpy as np

import g_agent as A
import g_control_probe as M1
import g_motion as MV

BFS_NODES = 40000
LEARN_AGREE = 3      # agreeing presses before a key's step vector is trusted
LEARN_MAX = 8        # presses per key in the learning phase
MAX_STEP = 10        # a step vector component beyond this is a throw or a teleport, not a step


def _anchor(cells):
    return (min(y for y, _ in cells), min(x for _, x in cells))


class ColourOracle:
    """E9 goal oracle (docs/E9_protocol.md Sections 1-2; rules from docs/E9_goals.md).

    For a game with a rule, at each level start it finds the sprite that the game's level-end
    predicate names, maps its visible cells into the 64x64 frame with the camera's own scale and
    offset (arcengine Camera.render), and returns those cells; the hook reads their colours from
    the frame.  The rule is stated by tag only; no coordinate, colour or layout is stored here.
    It hands nothing for any other game (ls20: its predicate is not a place; held-out games: never
    given a rule).  off=True keeps every call but always hands nothing (the equivalence check)."""
    RULES = {
        "tu93": ("0015msvpvzxhqf", False),   # every exit sprite (tu93.py 1236-1242)
        "dc22": ("goknoi", True),            # the first 'goknoi' sprite (dc22.py 10869-10870, 9995)
    }

    def __init__(self, game, off=False):
        self.game = str(game)[:4]
        self.off = off
        self.rule = None if off else self.RULES.get(self.game)
        self.env = None

    def bind(self, env):
        self.env = env

    def target_cells(self):
        """frame cells (row, col) of the target sprite(s), or None when the oracle hands nothing"""
        if self.rule is None or self.env is None or getattr(self.env, "_game", None) is None:
            return None
        g = self.env._game
        tag, first_only = self.rule
        sprites = g.current_level.get_sprites_by_tag(tag)
        if first_only:
            sprites = sprites[:1]
        scale, x_off, y_off = g.camera._calculate_scale_and_offset()
        cells = set()
        for sp in sprites:
            if not sp.is_visible:
                continue
            px = np.asarray(sp.render())
            ys, xs = np.nonzero(px >= 0)
            for y, x in zip(ys.tolist(), xs.tolist()):
                gx, gy = sp.x - g.camera.x + x, sp.y - g.camera.y + y
                for dy in range(scale):
                    for dx in range(scale):
                        cells.add((gy * scale + y_off + dy, gx * scale + x_off + dx))
        cells = {(y, x) for y, x in cells if 0 <= y < 64 and 0 <= x < 64}
        return cells or None


class NavHook:
    def __init__(self, seed=0, avoid_death=True, wall_min=2, deadly_min=2, goal_tries=6,
                 stall_steps=150, mispredict_max=8, learn_tries=12, block_steps=40, wait_max=12,
                 oracle=None):
        self.oracle = oracle         # E9 ColourOracle, or None (mode nav)
        self.rng = random.Random(seed)
        self.avoid_death = avoid_death
        self.wall_min, self.deadly_min = wall_min, deadly_min
        self.goal_tries, self.stall_steps = goal_tries, stall_steps
        self.mispredict_max, self.learn_tries = mispredict_max, learn_tries
        self.block_steps, self.wait_max = block_steps, wait_max
        self.total_steps = 0
        # learned once per game
        self.keys = None
        self.eff_votes = {}          # key -> Counter of (dx, dy)
        self.eff = {}                # key -> (dx, dy)
        self.no_effect = Counter()   # key -> presses that shifted nothing while learning
        # the learning phase.  MEASURED (lenovo, held-out 4 seeds): one press per key accepted
        # whatever moved - ar25 key 5 = [21,-14], tr87 key 1 = [1,1], m0r0 key 3 = [28,4] - and
        # those games were handed over within two steps.  The milestone-1 probe demanded four
        # agreeing presses; this phase demands LEARN_AGREE with a 2:1 margin over any rival.
        self.learning = True
        self.learn_presses = Counter()      # key -> presses in the phase
        self.learn_cells = {}               # (key, vector) -> cells of the last agreeing press
        self.learn_decided = {}             # key -> "accepted" | "no_move"
        self.learn_snapshot = {}            # votes as they stood when the phase ended
        self.avatar_colours = set()
        self.wall, self.walked = Counter(), Counter()   # bump votes; times walked onto
        self.deadly = Counter()                          # death-step votes
        self.near_death, self.near_safe = Counter(), Counter()   # colours around the avatar
        # DIAGNOSTIC, costs no action: which other colours shift when a key is pressed.
        # MEASURED (sandbox): tu93's sentinel and m0r0's second robot move WITH the key; a
        # planner over my own position alone cannot pass them.  This counter says how many
        # held-out games have such co-movers, before anything is built for them.
        self.co_movers = Counter()
        self.key_presses = 0
        self.issued = None                               # the action act() just chose
        self.goal_hyps = []          # colours, most recent first
        self.c = Counter()
        self.levels = []             # per-level report dicts
        # per level
        self._new_level(0)

    # ------------------------------------------------------------------ per-level state
    def _new_level(self, level):
        self.level = level
        self.pos, self.shape = None, None
        self.visited, self.blocked = set(), {}      # blocked: (pos, key) -> (colours, step)
        self.plan, self.plan_target, self.target_kind = [], None, None
        self.goal_tried, self.goal_attempts = set(), 0
        self.active = True
        self.localise_tried = []
        self.nav_steps, self.steps_since_new, self.mispredicts = 0, 0, 0
        self.waits = 0
        self.lv_presses = 0
        self.lv = dict(level=level, nav_steps=0, ok=0, bumped=0, mispredict=0, goal_targets=0,
                       goal_reached_no_end=0, frontier_targets=0, fallback=None, localise=0)
        self.levels.append(self.lv)
        # E9: set at the level's first act() when an oracle is attached; None = nothing handed
        self.oracle_cols, self._oracle_ready, self.target_oracle = None, False, False

    def steering(self):
        return self.active and self.pos is not None

    def on_reset(self):
        """any RESET (stuck rule, burst): the avatar is back at the level start, position unknown"""
        self.pos = None
        self.localise_tried = []
        self.plan = []

    def _fallback(self, reason):
        self.active = False
        self.lv["fallback"] = reason
        self.c["fallback_" + reason] += 1

    # ------------------------------------------------------------------ geometry
    def _footprint(self, p):
        return {(p[0] + oy, p[1] + ox) for oy, ox in self.shape}

    def _inside(self, p):
        return all(1 <= y < 63 and 0 <= x < 64 for y, x in self._footprint(p))

    def _new_cells(self, p, d):
        """cells the avatar would newly cover moving from p by d=(dx, dy)."""
        q = (p[0] + d[1], p[1] + d[0])
        return self._footprint(q) - self._footprint(p), q

    def _swept_cells(self, p, d):
        """every cell the avatar passes through or lands on moving from p by d.  MEASURED
        (sandbox, tu93): landing spots are 6 apart and the 3-pixel connector between them is
        the wall; a landing-only model cannot see it and voted the floor as the wall."""
        sx, sy = (d[0] > 0) - (d[0] < 0), (d[1] > 0) - (d[1] < 0)
        n = max(abs(d[0]), abs(d[1]))
        out = set()
        for t in range(1, n + 1):
            out |= self._footprint((p[0] + sy * t, p[1] + sx * t))
        return out - self._footprint(p)

    def _colours_at(self, g, cells):
        return {int(g[y, x]) for y, x in cells if 1 <= y < 63 and 0 <= x < 64}

    def _is_avoid_near(self, col):
        """a colour that is next to the avatar when it dies, and seldom otherwise (tu93's
        sentinel kills without being stepped on)."""
        d = self.near_death[col]
        return self.avoid_death and d >= self.deadly_min and 10 * d >= 3 * (d + self.near_safe[col])

    def _ring(self, cells, r):
        out = set()
        for y, x in cells:
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    out.add((y + dy, x + dx))
        return out - set(cells)

    def _is_wall(self, col):
        # MEASURED (sandbox, tu93/ls20): voting for every colour ahead made the FLOOR a wall
        # (982 and 1112 contradictions), because a 6-pixel step past a thin wall covers floor
        # too.  A wall is a colour that has been bumped into and NEVER walked onto.
        # one walk onto it (a pusher landing, a displacement) must not un-wall a colour that
        # has been bumped into many times: ls20's wall lost its status to one contradiction
        return self.wall[col] >= self.wall_min and self.walked[col] * 8 <= self.wall[col]

    def _is_deadly(self, col):
        # deadly = stepping onto it kills at least 30% of the time (floor is present at every
        # death step too, but is walked onto hundreds of times)
        d = self.deadly[col]
        return self.avoid_death and d >= self.deadly_min and 10 * d >= 3 * (d + self.walked[col])

    def _passable(self, g, p, key):
        d = self.eff[key]
        cells, q = self._new_cells(p, d)
        if not self._inside(q):
            return False, None
        cols = self._colours_at(g, self._swept_cells(p, d))
        for col in cols:
            if self._is_wall(col):
                return False, None
        for col in self._colours_at(g, cells):
            if self._is_deadly(col):
                return False, None
        if self.near_death:
            step = max(1, abs(d[0]) + abs(d[1]))
            for col in self._colours_at(g, self._ring(self._footprint(q), step)):
                if self._is_avoid_near(col):
                    return False, None
        b = self.blocked.get((p, key))
        if b is not None:
            # MEASURED (sandbox, tu93): a bump against the moving sentinel made the edge to the
            # exit permanently "blocked" and the level fell back.  A bump is tied to what was
            # there: when those colours change the edge is free again; and with no wall colour
            # in it, a bump expires after block_steps so a transient block cannot seal a level.
            cols_then, at, fatal = b
            if cols != cols_then:
                del self.blocked[(p, key)]
                self.c["unblocked_changed"] += 1
            elif not fatal and self.total_steps - at >= self.block_steps and not any(self.wall[c] for c in cols):
                del self.blocked[(p, key)]
                self.c["unblocked_expired"] += 1
            else:
                return False, None
        return True, q

    def _block(self, p, key, before, fatal=False):
        """fatal: the step killed us - it stays closed until the colours on that path change,
        never by time (MEASURED, tu93 level 2: a death edge that expired was walked into again)."""
        self.blocked[(p, key)] = (self._colours_at(before, self._swept_cells(p, self.eff[key])),
                                  self.total_steps, fatal)

    # ------------------------------------------------------------------ planning
    def _bfs(self, g):
        """parents for every lattice position reachable from pos on the current frame."""
        prev = {self.pos: None}
        q = deque([self.pos])
        order = []
        while q and len(prev) < BFS_NODES:
            u = q.popleft()
            order.append(u)
            for k in self.eff:
                ok, v = self._passable(g, u, k)
                if ok and v not in prev:
                    prev[v] = (u, k)
                    q.append(v)
        return prev, order

    def _path(self, prev, target):
        path, node = [], target
        while prev[node] is not None:
            node, k = prev[node]
            path.append(k)
        path.reverse()
        return path

    def _goal_cells(self, g, p, col):
        return col in self._colours_at(g, self._footprint(p))

    def _oracle_level_start(self, g):
        """E9: the level's oracle colours, read from this (the level's first planner) frame at the
        target's cells; background removed as _record_goal does.  V5: cells of those colours
        outside the target, and their 4-connected components.  Nothing is recorded when the oracle
        hands nothing, so such a level's report is identical to mode nav's."""
        self._oracle_ready = True
        cells = self.oracle.target_cells()
        if not cells:
            return
        body = g[1:63]
        vals, cnts = np.unique(body, return_counts=True)
        bg = int(vals[int(cnts.argmax())])
        cols = sorted(self._colours_at(g, cells) - {bg})
        self.lv["oracle_colours"] = cols
        if not cols:
            return
        self.oracle_cols = cols
        others = {(y, x) for y in range(1, 63) for x in range(64)
                  if int(g[y, x]) in cols and (y, x) not in cells}
        comps, seen = 0, set()
        for c0 in others:
            if c0 in seen:
                continue
            comps += 1
            stack = [c0]
            seen.add(c0)
            while stack:
                y, x = stack.pop()
                for n in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if n in others and n not in seen:
                        seen.add(n)
                        stack.append(n)
        self.lv["oracle_ambiguity"] = dict(cells=len(others), components=comps)

    def _replan(self, g):
        prev, order = self._bfs(g)
        self.c["replans"] += 1
        # 1. a recorded goal colour, nearest cell of it first.  E9: the oracle's colours replace
        # the recorded ones for this level and are never written off (no goal_tries cap).
        oracle_on = self.oracle_cols is not None
        hyps = [c for c in self.oracle_cols if c not in self.avatar_colours] if oracle_on else self.goal_hyps
        if oracle_on or self.goal_attempts < self.goal_tries:
            for col in hyps:
                for p in order:
                    if p == self.pos or p in self.goal_tried:
                        continue
                    if self._goal_cells(g, p, col):
                        self.plan, self.plan_target, self.target_kind = self._path(prev, p), p, col
                        self.goal_attempts += 1
                        self.lv["goal_targets"] += 1
                        self.c["goal_targets"] += 1
                        if oracle_on:
                            self.target_oracle = True
                            self.lv["oracle_targets"] = self.lv.get("oracle_targets", 0) + 1
                            self.c["oracle_targets"] += 1
                        return True
        # 2. the frontier: nearest position never stood on
        for p in order:
            if p != self.pos and p not in self.visited:
                self.plan, self.plan_target, self.target_kind = self._path(prev, p), p, "frontier"
                self.lv["frontier_targets"] += 1
                return True
        self.c["frontier_exhausted"] += 1
        return False

    # ------------------------------------------------------------------ the policy
    def act(self, g, raw, level):
        if self.oracle is not None and not self._oracle_ready:
            self._oracle_level_start(g)
        if self.keys is None:
            avail = [int(a) for a in (raw.available_actions or [])]
            self.keys = [a for a in avail if a in M1.KEYS]
            if not self.keys:
                self._fallback("no_keys")
                self.c["avatar_found"] = 0
        if not self.active:
            return None
        if self.learning:
            k = self._next_learn_key()
            if k is not None:
                self.issued = k
                self.lv["nav_steps"] += 1
                self.lv["learn"] = self.lv.get("learn", 0) + 1
                self.total_steps += 1
                return k
            self._finish_learning()
            if not self.active:
                return None
        if self.pos is None and self.eff and self.shape and self.avatar_colours:
            # the avatar's colours are known: find it without a press (verified on the first step)
            p = self._find_avatar(g)
            if p is not None:
                self.pos = p
                self.visited.add(p)
                self.c["located_by_colour"] += 1
        elif self.pos is not None and self.avatar_colours:
            p = self._find_avatar(g)
            if p is not None and p != self.pos:
                self.c["pos_corrected"] += 1
                self.pos = p
                self.visited.add(p)
                self.plan = []
        if self.pos is None:
            # learn (level 1) or localise (later levels, after a death): press a key
            if not self.eff:
                self._fallback("no_avatar")
                return None
            else:
                cands = [k for k in self.eff if k not in self.localise_tried]
                if not cands:
                    self._fallback("localise_failed")
                    return None
                k = self.rng.choice(cands)
            self.localise_tried.append(k)
            self.lv["localise"] += 1
            self.lv["nav_steps"] += 1
            return k
        if self.steps_since_new >= self.stall_steps:
            self._fallback("stalled")
            return None
        if self.mispredicts >= self.mispredict_max:
            self._fallback("mispredicted")
            return None
        if not self.plan:
            if not self._replan(g):
                w = self._wait_action(g)
                if w is not None:
                    return w
                self._fallback("frontier_exhausted")
                return None
        # re-check the next step on the current frame (things move)
        k = self.plan[0]
        ok, _q = self._passable(g, self.pos, k)
        if not ok:
            self.c["step_revalidated"] += 1
            if not self._replan(g):
                self._fallback("frontier_exhausted")
                return None
            k = self.plan[0]
        self.plan.pop(0)
        self.lv["nav_steps"] += 1
        self.nav_steps += 1
        self.total_steps += 1
        self.issued = k
        return k

    # ------------------------------------------------------------------ learning from outcomes
    def observe(self, act, before, after, raw, level_changed=False, died=False):
        if act not in (self.keys or []):
            self.issued = None
            return
        mine, self.issued = (self.issued == act and self.active), None
        tag = "step" if mine else "obs"       # nav-issued steps vs the explorer's own presses
        d, cells, _w = MV.best_shift(before, after)
        if self.learning:
            self._learn_observe(act, d, cells, before, after, level_changed, died)
            return
        if not self.eff:
            return          # the phase found no avatar: that is final for the game, nothing to track
        cells = self._own_cells(after, cells)
        if self.pos is not None and self.shape and self.avatar_colours:
            # the avatar's OWN displacement, from its own cells - not the strongest shift on
            # screen.  MEASURED (sandbox, tu93): with the avatar blocked and the sentinel moving,
            # the global vote reported the sentinel's shift as a misprediction of the avatar.
            if cells:
                anc = _anchor(cells)
                d = (anc[1] - self.pos[1], anc[0] - self.pos[0])
                if d == (0, 0):
                    d = None
                elif max(abs(d[0]), abs(d[1])) > MAX_STEP:
                    # a throw or a teleport, not a step: relocate, vote nothing
                    self.c["displaced"] += 1
                    self.pos = anc
                    self.visited.add(anc)
                    self.plan = []
                    if died:
                        self._on_death_step(before, act)
                    return
            else:
                found = self._find_avatar(after)
                if found is None or found == self.pos:
                    d = None
                else:
                    d = (found[1] - self.pos[1], found[0] - self.pos[0])
                    cells = self._footprint(found)
        if mine or self.lv_presses < 150:      # the first 150 presses of EVERY level, plus nav's
            self.key_presses += 1
            self.lv_presses += 1
            for col in self._co_moving_colours(before, after):
                self.co_movers[col] += 1
        if d is not None and cells and max(abs(d[0]), abs(d[1])) <= MAX_STEP:
            self.eff_votes.setdefault(act, Counter())[d] += 1
            top = self._agreed(act)
            if top is not None and self.eff.get(act) != top:
                if act in self.eff:
                    self.c["eff_updated"] += 1
                self.eff[act] = top
            # the union over time: tu93's facing marker is in the moved cells on some presses and
            # not others, and a flickering colour set made the marker an "avoid" colour.  Only
            # from a cell set of the avatar's own size, so a second sprite moving by the same
            # offset (tu93's sentinel) cannot pour its colours into the set.
            if not self.shape or len(cells) == len(self.shape):
                self.avatar_colours |= self._colours_at(after, cells)
        if level_changed:
            # `after` is the next level's first frame, so cells found in it are meaningless:
            # the goal is read at the predicted destination in the old level's last frame
            self._record_goal(before, after, act, d, None)
            return                      # per-level state is reset by on_level()
        if self.pos is None:
            if d is not None and cells:
                self.pos, self.shape = _anchor(cells), frozenset(
                    (y - min(yy for yy, _ in cells), x - min(xx for _, xx in cells)) for y, x in cells)
                self.visited.add(self.pos)
                self.c["avatar_found"] = 1
            else:
                self.no_effect[act] += 1
            if died:
                self._on_death_step(before, act)
            return
        # a learning press from a known position
        if act not in self.eff and d is None:
            self.no_effect[act] += 1
            if died:
                self._on_death_step(before, act)
            return
        expected = self.eff.get(act)
        if d is None:
            # MEASURED (sandbox, ls20): a pusher threw the avatar 12 cells, beyond best_shift's
            # reach, so "no shift" was recorded as a bump while the position was 12 cells wrong.
            # A bump is only a bump if the avatar is still where we think it is.
            found = self._find_avatar(after)
            if found is not None and found != self.pos:
                self.c["displaced"] += 1
                self.pos = found
                self.visited.add(found)
                self.plan = []
                if died:
                    self._on_death_step(before, act)
                return
            # a bump: the edge is blocked, and the colours it would have covered vote for wall
            self._block(self.pos, act, before)
            self.lv["bumped"] += 1
            self.c[tag + "_bumped"] += 1
            if expected is not None:
                for col in self._colours_at(before, self._swept_cells(self.pos, expected)) - self.avatar_colours:
                    self.wall[col] += 1
            self.plan = []
            self.steps_since_new += 1
        elif d == expected:
            new_cells, q = self._new_cells(self.pos, d)
            for col in self._colours_at(before, self._swept_cells(self.pos, d)) - self.avatar_colours:
                if self._is_wall(col):
                    self.c["wall_contradicted"] += 1     # was a "wall" until walked on now
                self.walked[col] += 1
            step = max(1, abs(d[0]) + abs(d[1]))
            if not died:
                for col in self._colours_at(after, self._ring(self._footprint(q), step)) - self.avatar_colours:
                    self.near_safe[col] += 1
            self.pos = q
            if cells:
                anc = _anchor(cells)
                if anc != self.pos:
                    self.c["anchor_drift"] += 1
                    self.pos = anc
            if self.pos in self.visited:
                self.steps_since_new += 1
            else:
                self.visited.add(self.pos)
                self.steps_since_new = 0
            self.lv["ok"] += 1
            self.c[tag + "_ok"] += 1
        else:
            self.lv["mispredict"] += 1
            self.c[tag + "_mispredict"] += 1
            if mine:
                self.mispredicts += 1
            if cells:
                self.pos = _anchor(cells)
                self.visited.add(self.pos)
            else:
                self.pos = None            # ambiguous: relocate by colour, or by a press
                self.localise_tried = []
            self.plan = []
        # arrived at a goal target and nothing happened
        if not self.plan and self.target_kind not in (None, "frontier") and self.pos == self.plan_target:
            self.goal_tried.add(self.plan_target)
            self.lv["goal_reached_no_end"] += 1
            self.c["goal_reached_no_end"] += 1
            if self.target_oracle:
                self.lv["oracle_reached_no_end"] = self.lv.get("oracle_reached_no_end", 0) + 1
                self.c["oracle_reached_no_end"] += 1
            self.plan_target, self.target_kind = None, None
        if died:
            self._on_death_step(before, act)

    def _sealed_dynamically(self, g):
        """is some edge from a reachable position closed only by a deadly colour or by a block
        whose landing cells hold no wall colour?  Those can open again."""
        prev, order = self._bfs(g)
        for u in order:
            for k in self.eff:
                cells, q = self._new_cells(u, self.eff[k])
                if not self._inside(q):
                    continue
                if any(self._is_wall(c) for c in self._colours_at(g, self._swept_cells(u, self.eff[k]))):
                    continue
                if any(self._is_deadly(c) for c in self._colours_at(g, cells)) or (u, k) in self.blocked:
                    return True
        return False

    def _wait_action(self, g):
        """MEASURED (sandbox, tu93 level 2): the sentinel stood in the only corridor to the exit,
        the frontier 'exhausted' and the level fell back.  Waiting must be a REAL move: in tu93
        the sentinel only advances after a successful player move, so a bump into a wall is not
        a tick (measured: 12 bump-waits never reopened the corridor).  A step to a visited
        neighbour is the wait; a bump only when no neighbour is passable.  At most wait_max per
        level."""
        if self.waits >= self.wait_max or not self._sealed_dynamically(g):
            return None
        self.waits += 1
        self.c["waits"] += 1
        self.lv["waits"] = self.waits
        opts = []
        for k in self.eff:
            ok, q = self._passable(g, self.pos, k)
            if ok and q in self.visited:
                opts.append((self.rng.random(), k))
        if opts:
            k = min(opts)[1]
        else:
            k = None
            for kk in self.eff:
                cells, q = self._new_cells(self.pos, self.eff[kk])
                if self._inside(q) and any(self._is_wall(c) for c in self._colours_at(g, self._swept_cells(self.pos, self.eff[kk]))):
                    k = kk
                    break
            if k is None:
                return None
        self.issued = k
        self.lv["nav_steps"] += 1
        self.total_steps += 1
        return k

    def _own_cells(self, after, cells):
        """MEASURED (sandbox, tu93 level 2): the sentinel mirrors the player's moves, so
        best_shift returned BOTH sprites as 'the object that moved' and the avatar's colour set
        became {4, 8, 9}.  Keep only cells of the avatar's colours, and if that is still bigger
        than the avatar, the one connected piece of the avatar's size."""
        if not cells or not self.avatar_colours or not self.shape:
            return cells
        own = {(y, x) for y, x in cells if int(after[y, x]) in self.avatar_colours}
        if len(own) <= len(self.shape):
            return own
        pieces, left = [], set(own)
        while left:
            start = left.pop()
            comp, stack = {start}, [start]
            while stack:
                cy, cx = stack.pop()
                for ny in (cy - 1, cy, cy + 1):
                    for nx in (cx - 1, cx, cx + 1):
                        if (ny, nx) in left:
                            left.discard((ny, nx))
                            comp.add((ny, nx))
                            stack.append((ny, nx))
            pieces.append(comp)
        fit = [p for p in pieces if len(p) == len(self.shape)]
        if len(fit) == 1:
            return fit[0]
        self.c["avatar_ambiguous"] += 1
        return set()

    def _co_moving_colours(self, before, after):
        """colours, other than the avatar's, at least half of whose cells shifted as one block.
        Floor being uncovered is never half of the floor; a sprite is all of itself."""
        b, a = before[1:63], after[1:63]
        diff = b != a
        out = []
        if not diff.any():
            return out
        for c in np.unique(np.concatenate([b[diff], a[diff]])):
            c = int(c)
            if c in self.avatar_colours:
                continue
            gone = np.argwhere((b == c) & (a != c))
            came = np.argwhere((a == c) & (b != c))
            n_all = int((b == c).sum())
            if len(gone) == 0 or len(gone) != len(came) or len(gone) > 400 or 2 * len(gone) < n_all:
                continue
            # the offset that lines up most of the colour's cells (a turning marker inside a
            # sprite, as on tu93's sentinel, breaks an exact-copy test)
            if len(gone) * len(came) > 4096:
                continue
            offs = Counter()
            for gy, gx in gone:
                for cy, cx in came:
                    offs[(int(cx - gx), int(cy - gy))] += 1
            (dx, dy), _n = offs.most_common(1)[0]
            if (dx, dy) == (0, 0):
                continue
            came_set = {(int(y), int(x)) for y, x in came}
            matched = sum(1 for y, x in gone if (int(y) + dy, int(x) + dx) in came_set)
            if 10 * matched >= 7 * len(gone):
                out.append(c)
        return out

    def _find_avatar(self, g):
        """the one connected patch of the avatar's colours that has exactly the avatar's shape.
        MEASURED (sandbox, ls20): a plain cell count failed because the avatar's colours also
        appear in the key panel; components do not."""
        if not self.shape or not self.avatar_colours:
            return None
        body = g[1:63]
        m = np.isin(body, list(self.avatar_colours))
        if not m.any() or int(m.sum()) > 40 * len(self.shape):
            return None
        seen = np.zeros_like(m)
        hits = []
        for y, x in zip(*np.nonzero(m)):
            if seen[y, x]:
                continue
            comp, stack = [], [(int(y), int(x))]
            seen[y, x] = True
            while stack:
                cy, cx = stack.pop()
                comp.append((cy, cx))
                for ny in (cy - 1, cy, cy + 1):
                    for nx in (cx - 1, cx, cx + 1):
                        if 0 <= ny < 62 and 0 <= nx < 64 and m[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
            if len(comp) == len(self.shape):
                cells = {(cy + 1, cx) for cy, cx in comp}
                p = _anchor(cells)
                if cells == self._footprint(p):
                    hits.append(p)
                    if len(hits) > 1:
                        return None
        return hits[0] if hits else None

    def _agreed(self, key):
        """the step vector for a key if LEARN_AGREE presses agree with a 2:1 margin, else None."""
        v = self.eff_votes.get(key)
        if not v:
            return None
        top = v.most_common(2)
        if top[0][1] < LEARN_AGREE:
            return None
        if len(top) > 1 and top[0][1] < 2 * top[1][1]:
            return None
        return top[0][0]

    def _next_learn_key(self):
        """round-robin over the keys not yet decided; None when every key is decided."""
        undecided = []
        for k in self.keys:
            if k in self.learn_decided:
                continue
            if self._agreed(k) is not None:
                self.learn_decided[k] = "accepted"
                continue
            n = self.learn_presses[k]
            best = self.eff_votes[k].most_common(1)[0][1] if self.eff_votes.get(k) else 0
            if n >= LEARN_MAX or (LEARN_MAX - n) < (LEARN_AGREE - best):
                self.learn_decided[k] = "no_move"
                continue
            undecided.append((n, k))
        if not undecided:
            return None
        return min(undecided)[1]

    def _learn_observe(self, act, d, cells, before, after, level_changed, died):
        self.learn_presses[act] += 1
        if self.avatar_colours and cells:
            own = {(y, x) for y, x in cells if int(after[y, x]) in self.avatar_colours}
            cells = own if own else set()
        if d is not None and cells and max(abs(d[0]), abs(d[1])) <= MAX_STEP:
            self.eff_votes.setdefault(act, Counter())[d] += 1
            self.learn_cells[(act, d)] = set(cells)
            top = self._agreed(act)
            if top is not None:
                if act not in self.eff:
                    self.c["avatar_found"] = 1
                self.eff[act] = top
                cells = self.learn_cells.get((act, top), cells)
                if not self.shape:
                    self.shape = frozenset((y - min(yy for yy, _ in cells), x - min(xx for _, xx in cells))
                                           for y, x in cells)
                if not self.shape or len(cells) == len(self.shape):
                    self.avatar_colours |= self._colours_at(after, cells)
        else:
            self.no_effect[act] += 1
        if level_changed:
            self.c["goal_unreadable"] += 1
            self.lv["goal"] = "unreadable (still learning)"
        if died:
            self.c["deaths"] += 1

    def _finish_learning(self):
        self.learning = False
        self.c["learn_presses"] = sum(self.learn_presses.values())
        self.learn_snapshot = {k: Counter(v) for k, v in self.eff_votes.items()}
        if not self.eff:
            self.c["avatar_found"] = 0
            self._fallback("no_avatar")
            return
        self._hypothesise_missing()
        self.pos = None
        self.localise_tried = []

    def _hypothesise_missing(self):
        """three of the four arrow keys learned as (0,-s),(0,s),(s,0): the fourth is (-s,0) until
        a press says otherwise.  Only for keys 1-4; verified on first use like any edge."""
        arrows = [k for k in (1, 2, 3, 4) if k in self.keys]
        missing = [k for k in arrows if k not in self.eff]
        if len(arrows) != 4 or len(missing) != 1:
            return
        vs = [self.eff[k] for k in arrows if k in self.eff]
        if len({abs(v[0]) + abs(v[1]) for v in vs}) != 1:
            return
        want = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        s0 = abs(vs[0][0]) + abs(vs[0][1])
        dirs = {(v[0] // s0, v[1] // s0) for v in vs}
        left = [w for w in want if w not in dirs]
        if len(left) == 1:
            k = missing[0]
            self.eff[k] = (left[0][0] * s0, left[0][1] * s0)
            self.c["eff_hypothesised"] += 1

    def _on_death_step(self, before, act):
        # the step that killed us: never take that edge again, and the colours it stepped onto vote
        if self.pos is not None and act in self.eff:
            self._block(self.pos, act, before, fatal=True)
            new_cells, q = self._new_cells(self.pos, self.eff[act])
            for col in self._colours_at(before, new_cells) - self.avatar_colours:
                self.deadly[col] += 1
            d = self.eff[act]
            step = max(1, abs(d[0]) + abs(d[1]))
            for col in self._colours_at(before, self._ring(self._footprint(q), step)) - self.avatar_colours:
                self.near_death[col] += 1
        self.c["deaths"] += 1
        self.plan = []

    def on_death(self, prev_frame):
        # the explorer is about to RESET; the avatar is back at the level start, position unknown
        self.pos = None
        self.localise_tried = []
        self.plan = []

    def _record_goal(self, before, after, act, d, cells):
        """what did the avatar reach when the level ended?  The colours it stepped onto, then
        the ring around its new cells; the level's own frame is `before`."""
        if not cells and self.pos is not None and act in self.eff:
            cells = self._footprint((self.pos[0] + self.eff[act][1], self.pos[1] + self.eff[act][0]))
        elif not cells and self.pos is not None:
            cells = self._footprint(self.pos)
        if not cells:
            self.c["goal_unreadable"] += 1
            self.lv["goal"] = "unreadable"
            if self.oracle_cols is not None:
                self.lv["oracle_confirmed"] = None          # E9 V2: ending position not readable
            return
        body = before[1:63]
        vals, cnts = np.unique(body, return_counts=True)
        bg = int(vals[int(cnts.argmax())])
        stepped = self._colours_at(before, cells) - self.avatar_colours - {bg}
        ring = set()
        for y, x in cells:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ring.add((y + dy, x + dx))
        ring = self._colours_at(before, ring - set(cells)) - self.avatar_colours - {bg}
        found = sorted(stepped) + sorted(ring - stepped)
        if self.target_kind not in (None, "frontier") and self.target_kind in stepped | ring:
            self.c["goal_confirmed"] += 1
            self.lv["goal_confirmed"] = self.target_kind
        for col in reversed(found):
            if col in self.goal_hyps:
                self.goal_hyps.remove(col)
            self.goal_hyps.insert(0, col)
        self.goal_hyps = self.goal_hyps[:6]
        self.c["goal_recorded"] += 1
        self.lv["goal"] = found
        if self.oracle_cols is not None:
            # E9 V2: did the position the level ended on show an oracle colour?
            ok = bool(set(self.oracle_cols) & (stepped | ring))
            self.lv["oracle_confirmed"] = ok
            self.c["oracle_confirmed" if ok else "oracle_not_confirmed"] += 1

    def on_level(self, level, frame):
        self._new_level(level)

    def report(self):
        learn = {}
        for k in (self.keys or []):
            v = (self.learn_snapshot if self.learn_snapshot else self.eff_votes).get(k)
            top = v.most_common(1)[0] if v else (None, 0)
            learn[str(k)] = dict(presses=int(self.learn_presses[k]), shift=list(top[0]) if top[0] else None,
                                 agree=int(top[1]), decided=self.learn_decided.get(k, "-"))
        return dict(counters=dict(self.c), eff={str(k): list(v) for k, v in self.eff.items()},
                    learn=learn,
                    goal_hyps=list(self.goal_hyps), walls=sorted(c for c in self.wall if self._is_wall(c)),
                    deadly=sorted(c for c in self.deadly if self._is_deadly(c)),
                    avoid_near=sorted(c for c in self.near_death if self._is_avoid_near(c)),
                    co_movers={str(c): n for c, n in self.co_movers.most_common(4)},
                    key_presses_sampled=self.key_presses, levels=self.levels)


def play(game, cfg, env_dir, seconds=600.0, nav_kwargs=None, oracle=None):
    hook = NavHook(seed=cfg.seed, avoid_death=cfg.avoid_death, oracle=oracle, **(nav_kwargs or {}))
    if oracle is None:
        return A.play(game, cfg, env_dir, seconds=seconds, hook=hook)
    # E9: the oracle needs the running game.  g_agent.play creates the environment itself, so the
    # environment is handed over by wrapping Arcade.make for this call only; g_agent.py is untouched.
    import arc_agi
    orig = arc_agi.Arcade.make

    def make(self, *a, **k):
        env = orig(self, *a, **k)
        oracle.bind(env)
        return env
    arc_agi.Arcade.make = make
    try:
        return A.play(game, cfg, env_dir, seconds=seconds, hook=hook)
    finally:
        arc_agi.Arcade.make = orig
