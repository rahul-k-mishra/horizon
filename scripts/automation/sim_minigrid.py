"""
sim_minigrid.py -- the MiniGrid/BabyAI simulator of stage D's search (kind devsearch; docs/DESIGN.md, Section 2.1).

A level is the layout that gymnasium.make(game).reset(seed=seed) produces, as in study 1 (study 1,
docs/PREREG.md v1, Section 3.2).  The action list is study 1's macro condition: north, south, east, west
(each the fewest left/right turns to face that way, then forward; it stops at a sub-step that ends the
episode), then pickup, drop, toggle and done passed through, eight in all.  A win is an episode that ends
with reward > 0; a loss is one that ends otherwise; both are terminal.  The environment's own step limit
is lifted (max_steps set out of reach), because the search counts states, not time; the step count is not
part of the state.  Observations are not computed (gen_obs is replaced by a function returning None),
since the search reads the state, not the frame.

State and its key.  At reset every object in the grid, in the carried slot and inside boxes gets a stable
index, in a fixed walk order; the walk is the same in every session because the layout is fixed by the seed.
The key of a state is: the agent's cell and facing; the index of the carried object; for every cell the
index of the object in it; for every object that can change (doors, keys, balls, boxes) its open and locked
flags, position and the index of what it contains; and, on BabyAI levels, the progress flags of the
instruction (a_done, b_done, lastStepMatch) and the index of the object carried at the previous step.
Two objects are therefore told apart by identity, not by looks.

Speed.  A deep copy of an environment costs far more than a step, so states are restored from snapshots of
what a step can change: the environment's attributes, the grid's cell list, the attributes of the objects
that can change, and the attributes of the instruction objects (with their lists copied).  Breadth first
with actions in a fixed order visits each layer in lexicographic order of the action sequences, so a stack
of snapshots along the current sequence lets each expansion start from its nearest shared ancestor.
scripts/automation/test_devsearch.py checks the counts against a plain search that deep-copies every state.
"""
from __future__ import annotations

import copy

MACROS = ("north", "south", "east", "west", "pickup", "drop", "toggle", "done")
FACING = {"north": 3, "south": 1, "east": 0, "west": 2}           # MiniGrid agent_dir: 0 east, 1 south, 2 west, 3 north
PRIM = dict(left=0, right=1, forward=2, pickup=3, drop=4, toggle=5, done=6)
MUTABLE = {"door", "key", "ball", "box"}
EXCLUDED = ("Dynamic-Obstacles",)    # obstacles move at random: a search over them is not defined


def make_env(game, seed):
    import gymnasium as gym  # noqa: PLC0415 -- only on machines that run stage D
    import minigrid  # noqa: F401,PLC0415 -- registers the environments
    if any(x in game for x in EXCLUDED):
        raise ValueError(f"{game}: excluded from stage D (sprites move at random)")
    env = gym.make(game)
    env.reset(seed=int(seed))
    u = env.unwrapped
    u.max_steps = 10 ** 12
    u.gen_obs = lambda: None
    return env, u


def _instr_objects(u):
    out, todo = [], [getattr(u, "instrs", None)]
    while todo:
        x = todo.pop()
        if x is None or any(x is y for y in out):
            continue
        out.append(x)
        for name in ("instr_a", "instr_b", "desc", "desc_move", "desc_fixed"):
            todo.append(getattr(x, name, None))
    return out


def tag_objects(u):
    """Give every object of the level a stable index _hz_id, in a fixed walk order (cells in order, then
    the carried object, each followed by what it contains); returns the objects in that order."""
    objs, seen = [], set()

    def add(o):
        if o is not None and id(o) not in seen:
            seen.add(id(o))
            o._hz_id = len(objs)
            objs.append(o)
            add(getattr(o, "contains", None))
    for o in u.grid.grid:
        add(o)
    add(u.carrying)
    return objs


def _idx(o):
    return -1 if o is None else getattr(o, "_hz_id", -2)


def state_key(u, mutable, instr):
    """The key of the current state; mutable: the changeable objects in _hz_id order; instr: the
    instruction objects in walk order."""
    parts = [tuple(int(x) for x in u.agent_pos), int(u.agent_dir), _idx(u.carrying),
             tuple(_idx(o) for o in u.grid.grid)]
    for o in mutable:
        cp = getattr(o, "cur_pos", None)
        parts.append((bool(getattr(o, "is_open", False)), bool(getattr(o, "is_locked", False)),
                      None if cp is None else tuple(int(x) for x in cp), _idx(getattr(o, "contains", None))))
    for o in instr:
        parts.append((getattr(o, "a_done", None), getattr(o, "b_done", None), getattr(o, "lastStepMatch", None),
                      _idx(getattr(o, "preCarrying", None)) if hasattr(o, "preCarrying") else None))
    return repr(parts).encode()


def apply_macro(u, a):
    """Apply macro action a to the unwrapped environment u; returns (terminated, reward)."""
    name = MACROS[a]
    if name in FACING:
        diff = (FACING[name] - u.agent_dir) % 4
        prims = {0: [], 1: ["right"], 2: ["right", "right"], 3: ["left"]}[diff] + ["forward"]
    else:
        prims = [name]
    for p in prims:
        _o, reward, terminated, _tr, _i = u.step(PRIM[p])
        if terminated:
            return True, float(reward)
    return False, 0.0


def _copy_dict(o):
    return {k: (list(v) if isinstance(v, list) else v) for k, v in o.__dict__.items()}


class MiniGridSim:
    win_is_terminal = True

    def __init__(self, params, unit):
        self.game, self.seed = unit["game"], int(unit["level"])
        self.env, self.u = make_env(self.game, self.seed)
        self.objs = tag_objects(self.u)
        self.mutable = [o for o in self.objs if o.type in MUTABLE]
        self.instr = _instr_objects(self.u)
        self.n_actions = len(MACROS)
        self._stack = [self.snapshot()]
        self._seq = ""

    # -- state
    def snapshot(self):
        u = self.u
        return (dict(u.__dict__), list(u.grid.grid), [dict(o.__dict__) for o in self.mutable],
                [_copy_dict(o) for o in self.instr])

    def restore(self, s):
        u = self.u
        u.__dict__.clear()
        u.__dict__.update(s[0])
        u.grid.grid[:] = s[1]
        for o, d in zip(self.mutable, s[2]):
            o.__dict__.clear()
            o.__dict__.update(d)
        for o, d in zip(self.instr, s[3]):
            o.__dict__.clear()
            o.__dict__.update({k: (list(v) if isinstance(v, list) else v) for k, v in d.items()})

    def key(self):
        return state_key(self.u, self.mutable, self.instr)

    def macro(self, a):
        return apply_macro(self.u, a)

    # -- the search interface (jobs.run_search)
    def root_enc(self):
        return ""

    def root_info(self):
        self.restore(self._stack[0])
        return self.key(), False, False

    def _goto(self, enc):
        c = 0
        top = min(len(enc), len(self._seq), len(self._stack) - 1)
        while c < top and enc[c] == self._seq[c]:
            c += 1
        del self._stack[c + 1:]
        for ch in enc[c:]:
            self.restore(self._stack[-1])
            term, _r = self.macro(int(ch))
            if term:
                raise ValueError(f"the sequence {enc!r} passes through a terminal state")
            self._stack.append(self.snapshot())
        self._seq = enc
        return self._stack[-1]

    def expand(self, enc):
        """(parent key, [(action, child enc, child key, win, loss), ...])."""
        snap = self._goto(enc)
        self.restore(snap)
        pkey = self.key()
        out = []
        for a in range(self.n_actions):
            self.restore(snap)
            term, reward = self.macro(a)
            win = term and reward > 0
            out.append((a, enc + str(a), self.key(), win, term and not win))
        return pkey, out


def naive_counts(game, seed):
    """A plain breadth-first search that deep-copies every state; for the tests only."""
    import collections  # noqa: PLC0415
    _env, u = make_env(game, seed)
    tag_objects(u)

    def key_of(uu):
        objs, seen, todo = [], set(), list(uu.grid.grid) + [uu.carrying]
        while todo:
            o = todo.pop()
            if o is not None and id(o) not in seen:
                seen.add(id(o))
                objs.append(o)
                todo.append(getattr(o, "contains", None))
        mutable = sorted((o for o in objs if o.type in MUTABLE), key=lambda o: o._hz_id)
        return state_key(uu, mutable, _instr_objects(uu))

    start = copy.deepcopy(u)
    seen = {key_of(start)}
    q = collections.deque([(start, 0)])
    n_exp, sol, distinct = 0, None, 0
    while q:
        s, d = q.popleft()
        n_exp += 1
        pk, kids = key_of(s), set()
        for a in range(len(MACROS)):
            c = copy.deepcopy(s)
            term, reward = apply_macro(c, a)
            k = key_of(c)
            if k != pk:
                kids.add(k)
            if k in seen:
                continue
            seen.add(k)
            if term:
                if reward > 0 and sol is None:
                    sol = d + 1
                continue
            q.append((c, d + 1))
        distinct += len(kids)
    return dict(states_seen=len(seen), states_expanded=n_exp, solution_length=sol, successors_distinct=distinct)
