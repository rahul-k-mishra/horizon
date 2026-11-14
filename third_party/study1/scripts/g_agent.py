"""
BRUTUS-G generic agent.  Reads nothing but frames; no game's source, no per-game code.

It plays a game by systematic exploration over what it has actually seen:

  * STATE     a hash of the playfield (rows 1-62; rows 0 and 63 hold bars and counters, which
              would make every frame look new)
  * ACTIONS   the keyboard actions the game offers, plus - when clicking is offered - a click on
              the centre of each of the rarest-coloured objects on screen (the top --click-topk)
  * GRAPH     every (state, action) it has tried and where it led
  * CHOICE    walk, over known edges, to the nearest state that still has an untried action,
              and try it.  In "pos" mode, keyboard moves are also generalised: once it knows
              what each key does to the object it controls (milestone 1) and which moves were
              blocked (milestone 2), it prefers moves into positions it has never stood on.
  * RESET     after --stuck-limit actions without reaching a new state, it resets the level
  * REPLAY    after a level is won, the next level first tries the winning action sequence
              of the previous one (levels often share their start)

Every setting is a field of Config, so an outside search can vary them.
"""
from __future__ import annotations

import hashlib
import random
import time
from collections import deque, Counter, defaultdict
from dataclasses import dataclass, asdict, replace

import numpy as np

import g_control_probe as M1
import g_motion as MV


# Each of these was MEASURED to be the best choice on at least one train game and wrong on
# others: repeat multiplies vc33 by 22 and kills tn36; edges doubles ft09 and kills three others.
BEHAVIOURS = {
    "plain":       {},
    "repeat":      {"repeat_key": 0.6},
    "edges":       {"click_edges": True},
    "common":      {"click_order": "common"},
    "fine_clicks": {"click_topk": 32, "click_tile": 4},
    "scan":        {"click_scan": 6, "scan_after": 0},
    "deep":        {"dry_deep": True, "burst": 100, "stuck_limit": 1000},
    "hash":        {"mode": "hash"},
}


@dataclass
class Config:
    mode: str = "pos"             # "hash" | "pos"  (pos: 0.125 vs 0.084 averaged over the search)
    learn_per_key: int = 4
    max_actions: int = 3000
    stuck_limit: int = 200        # 0 = never reset for being stuck
    click_topk: int = 16          # the strongest effect in the search: 0.199 vs 0.094 or less
    click_tile: int = 8           # blobs of one colour are split into tiles this size
    click_scan: int = 6           # grid spacing for the click scan, when it is triggered
    scan_after: int = 60          # trigger it after this many actions with the screen unchanged
    click_share: float = 0.3      # in games offering both keys and clicks
    replay: bool = False          # replay HURT on average: 0.078 vs 0.128
    # STATE ABSTRACTION.  MEASURED (25 games x 3 seeds): re86, sb26, wa30 and cn04 show 7,000 to
    # 12,000 distinct boards in 20,000 actions and never finish level 1 - a new board almost every
    # press, so the map the agent builds is noise.  These settings hash LESS of the board:
    #   "full"    every cell (what we did until now)
    #   "coarse"  the board reduced to blocks of `abstract_block` cells, each block the colour
    #             that dominates it - animation and enemy wiggles vanish, layout survives
    #   "objects" only WHICH colours are present and how many separate pieces each has, plus the
    #             controlled object's position - the smallest description that still says where
    #             I am and what is left
    abstract: str = "full"
    abstract_block: int = 4
    max_states: int = 60000       # bound the graph: 110 games at once share one machine
    # --- behaviour switches: each one is a different way to play, for the search to test ---
    reset_in_graph: bool = False  # treat RESET as an ordinary action inside the state graph
    click_edges: bool = False     # also click along the board's edges (lp85 responds only there)
    click_order: str = "rare"     # which colours to click first: "rare", "common", "mixed"
    repeat_key: float = 0.0       # after an action that changed something, chance to repeat it
    prefer_effect: bool = False   # try the actions that have changed things most often, first
    dry_deep: bool = False        # when dry, go to the state where something was last new
    burst: int = 0                # when exploration runs dry: RESET, then this many random moves
    # --- per-game adaptation: try several behaviours, keep the one that is working here ---
    # SEEK: aim at rare objects instead of wandering.  MEASURED (census, depth 7 = every key
    # sequence of 7 moves, 114,688 actions per game): tu93 reaches 61 boards, dc22 36, ls20 137,
    # and NO game crosses a level.  Seven moves is 35 pixels for a 5-pixel step - the agent
    # cannot even cross the board by enumeration, and enumeration is exponential in depth.  A
    # path search over positions is linear, so a target 30 moves away is reachable only by
    # aiming at it.
    # GIVE UP on a game that cannot go anywhere, so its budget can go to one that can.
    # MEASURED (100,000 actions per game, 2 seeds): tu93 rose from 2 levels to 7, sk48 and ar25
    # started winning - while dc22 spent 98,007 of 98,871 actions with nothing untried anywhere,
    # su15 97,577 of 97,611, ls20 89,571, lf52 98,932, and none of them won anything at any
    # budget.  Those actions are not scarce; they are spent where they cannot pay.
    # 1. DEATH MODEL.  MEASURED (100,000 actions): su15 died 1,905 times, tu93 3,940, r11l 4,764.
    #    Death has never been modelled at all - a game that dies constantly may look "dry" only
    #    because it keeps being sent back to the start.
    avoid_death: bool = True      # CONFIRMED over 4 seeds, 200 runs: train levels 26 -> 56,
                                  # train score 0.2039 -> 0.2422, held-out level (0.2484 ->
                                  # 0.2467, inside the noise).  tu93 averages 7.8 levels against
                                  # about 1; ls20 wins its first level in every seed.
    # 2. CLICK TYPING.  The scan finds WHERE a click does something; it never asks WHAT.  Clicks
    #    are ranked by how much they change, and the ones that do most are tried first.
    click_rank: bool = False
    # 3. PUSHING.  Every mechanism so far assumes the goal is reached by moving the avatar.  If an
    #    object moves when the avatar meets it, that object is pushable, and the goal may be to
    #    put it somewhere.
    push: bool = False
    give_up_after: int = 0        # stop after this many actions with no new state and no level
    give_up_dry: float = 0.5      # ...and exploration dry on at least this share of them
    seek: bool = False
    seek_after: int = 400         # start aiming once this many actions have won nothing
    seek_max_targets: int = 12
    adapt: int = 0                # actions to spend trying each behaviour before committing
    adapt_pool: str = ""          # names of the behaviours to try, separated by "|"
    adapt_after: int = 0          # only start trying behaviours after this many actions with no
                                  # level won - trying them up front costs more than it gains
    reset_when_dry: bool = False  # REJECTED: reset-when-dry cost tu93 4 levels -> 0, because
                                  # after a reset everything is tried again and the guard blocks it
    mask_after: int = 30          # presses before the volatile-cell mask is fixed
    volatile: float = 0.8         # a cell changing on this share of presses is a counter
    seed: int = 0

    def key(self):
        return tuple(sorted(asdict(self).items()))


def _blobs(body, c):
    """Connected pieces of one colour, as (count, cells)."""
    m = body == c
    if not m.any():
        return 0, np.zeros((0, 2), dtype=int)
    seen = np.zeros_like(m)
    n = 0
    for y, x in zip(*np.nonzero(m)):
        if seen[y, x]:
            continue
        n += 1
        stack = [(y, x)]
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            for ny in (cy - 1, cy, cy + 1):
                for nx in (cx - 1, cx, cx + 1):
                    if 0 <= ny < m.shape[0] and 0 <= nx < m.shape[1] and m[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
    return n, np.argwhere(m)


def _facts(g):
    """Object-level facts about one board.  MEASURED: counting cells of each colour was too
    crude - on vc33 the fluid moves one way on level 1 and the other way on level 2, so the
    colour counts made the goal look REVERSED.  These facts survive a change of direction."""
    body = g[1:63]
    vals, cnts = np.unique(body, return_counts=True)
    bg = int(vals[int(cnts.argmax())])
    # anything that is not the background counts, up to 60% of the board.  MEASURED: a fixed
    # 900-cell limit silently dropped vc33's fluid and sp80's large regions, so those games
    # reported NO goal rules at all - the very thing the game is about was being skipped.
    live = [int(c) for c, n in zip(vals, cnts) if c != bg and n < 0.6 * body.size]
    f = set()
    pieces, cells = {}, {}
    for c in live:
        n, pts = _blobs(body, c)
        pieces[c] = n
        cells[c] = pts
        f.add(f"pieces:{c}={min(n, 9)}")
        if n:
            ys, xs = pts[:, 0], pts[:, 1]
            if ys.max() - ys.min() == 0:
                f.add(f"onerow:{c}")
            if xs.max() - xs.min() == 0:
                f.add(f"onecol:{c}")
    for i, c in enumerate(live):
        for d in live[i + 1:]:
            if pieces[c] and pieces[d]:
                if pieces[c] == pieces[d]:
                    f.add(f"samecount:{c},{d}")
                a, b = cells[c], cells[d]
                if (a[:, 0].min() >= b[:, 0].min() and a[:, 0].max() <= b[:, 0].max()
                        and a[:, 1].min() >= b[:, 1].min() and a[:, 1].max() <= b[:, 1].max()):
                    f.add(f"inside:{c},{d}")
                da = np.abs(a[:, None, :] - b[None, :, :]).sum(2) if len(a) * len(b) < 40000 else None
                if da is not None and (da <= 1).any():
                    f.add(f"touch:{min(c, d)},{max(c, d)}")
    return f


def abstract_rules(start, end, facts_end, facts_start):
    """The same rule written without naming colours, so a goal that uses different colours on
    different levels still matches.  MEASURED on cd82: level 1 ended with colour 15 in three
    pieces, level 2 with colour 12 in three pieces - the same goal, and the literal form missed
    it."""
    changed = set()
    def counts(g):
        v, n = np.unique(g[1:63], return_counts=True)
        return {int(a): int(b) for a, b in zip(v, n)}
    cs, ce = counts(start), counts(end)
    for c in set(cs) | set(ce):
        if cs.get(c, 0) != ce.get(c, 0):
            changed.add(c)
    out = set()
    for f in facts_end - facts_start:
        head, _, rest = f.partition(":")
        if head == "pieces":
            col, _, n = rest.partition("=")
            if int(col) in changed:
                out.add(f"changed-colour in {n} pieces")
        elif head in ("onerow", "onecol"):
            if int(rest) in changed:
                out.add(f"changed-colour in one {head[3:]}")
        elif head in ("touch", "inside", "samecount"):
            a, _, b = rest.partition(",")
            ca, cb = int(a) in changed, int(b) in changed
            if ca or cb:
                out.add(f"{head}: changed-colour with {'changed' if ca and cb else 'fixed'}-colour")
    return sorted(out)


def level_rules(start, end):
    """The candidate goal: object-level facts TRUE when the level ended and FALSE when it began.
    A game reuses its goal across levels, so a fact that holds at every level end is something a
    planner could aim at instead of exploring blindly."""
    try:
        fs, fe = _facts(start), _facts(end)
        return sorted(fe - fs) + abstract_rules(start, end, fe, fs)
    except Exception as e:                      # never silent: a hidden failure taught us nothing
        return [f"ERROR:{type(e).__name__}:{str(e)[:60]}"]


def _coarse(body, blk):
    h, w = body.shape
    hh, ww = h // blk, w // blk
    cut = body[:hh * blk, :ww * blk].reshape(hh, blk, ww, blk).transpose(0, 2, 1, 3)
    cut = cut.reshape(hh, ww, blk * blk)
    out = np.zeros((hh, ww), dtype=np.int16)
    for i in range(hh):
        for j in range(ww):
            vals, cnts = np.unique(cut[i, j], return_counts=True)
            out[i, j] = vals[int(cnts.argmax())]
    return out


def abstract_state(g, mode, blk, pos=None, mask=None):
    body = g[1:63]
    if mask is not None:
        # the volatile mask was only being applied on the "full" path, so the abstract modes
        # still saw the step counter tick on every press and gave every frame its own key -
        # they were not abstracting anything at all
        body = np.where(mask, 0, body)
    if mode == "coarse":
        return _coarse(body, blk).tobytes()
    if mode == "objects":
        vals, cnts = np.unique(body, return_counts=True)
        bg = int(vals[int(cnts.argmax())])
        parts = []
        for c, n in zip(vals, cnts):
            if int(c) == bg:
                continue
            k, _ = _blobs(body, int(c))
            parts.append((int(c), min(k, 9), min(int(n) // 8, 60)))
        return (repr(sorted(parts)) + repr(pos)).encode()
    return body.tobytes()


def state_hash(g, mask=None):
    """Hash of the playfield.  Cells in mask - ones that change on almost every press, such as
    a step counter - are left out.  MEASURED on ls20: its counter sits inside the playfield, so
    without the mask 1,500 presses looked like 1,234 different states and exploration was blind."""
    body = g[1:63]
    if mask is not None:
        body = np.where(mask, 0, body)
    return hashlib.blake2b(body.tobytes(), digest_size=10).digest()


def click_targets(g, topk, tile=8, click_order="rare", edges=False):
    """Centres of the rarest-coloured blobs on the playfield (the background colour excluded)."""
    body = g[1:63]
    counts = np.bincount(body.ravel().clip(0, 15), minlength=16)
    bg = int(counts.argmax())
    out0 = []
    if edges:
        # MEASURED on lp85: of 240 sampled clicks only 6 changed anything, all at the board's
        # edges - x=4 or x=56-60 - where no blob centre ever falls.
        for v in range(2, 62, 6):
            out0 += [("c", 1, v), ("c", 62, v), ("c", v, 2), ("c", v, 61)]
    order = np.argsort(counts)
    if click_order == "common":
        order = order[::-1]
    elif click_order == "mixed":
        order = np.array([c for pair in zip(order, order[::-1]) for c in pair])
    colours = [c for c in order if counts[c] > 0 and c != bg]
    out = list(out0)
    for c in colours:
        ys, xs = np.nonzero(body == c)
        if len(ys) == 0:
            continue
        # split into coarse blobs by 8x8 tiles so one colour can give several targets
        tiles = defaultdict(list)
        for y, x in zip(ys, xs):
            tiles[(int(y) // tile, int(x) // tile)].append((int(y), int(x)))
        for pts in tiles.values():
            cy = int(round(sum(p[0] for p in pts) / len(pts))) + 1
            cx = int(round(sum(p[1] for p in pts) / len(pts)))
            out.append(("c", cx, cy))
            if len(out) >= topk:
                return out
    return out


def play(game, cfg: Config, env_dir, seconds=600.0, scorecard=True, hook=None):
    """hook: an optional policy layer (g_nav.NavHook).  When it returns an action, that action
    is taken instead of the explorer's choice; every step still goes through step(), so the
    action count, the graph and the level bookkeeping are the explorer's own.  With hook=None
    this function is unchanged (checked: identical scores on the train games, g_nav_equiv.py)."""
    import logging
    logging.disable(logging.CRITICAL)
    from arc_agi import Arcade
    from arcengine import GameAction
    t0 = time.time()
    rng = random.Random(cfg.seed)
    arc = Arcade(operation_mode="offline", environments_dir=env_dir)
    card = arc.open_scorecard(tags=["brutus-g"]) if scorecard else None
    env = arc.make(game, scorecard_id=card) if card else arc.make(game)
    raw = env.observation_space
    avail = [int(a) for a in (raw.available_actions or [])]
    keys = [a for a in avail if a in M1.KEYS]
    can_click = 6 in avail

    edges = {}                                 # (state, action) -> next state
    tried = defaultdict(set)                   # state -> actions tried
    acts_of = {}                               # state -> candidate actions
    seen_states = set()
    actions = 0
    since_new = 0
    dry_run = 0          # actions since the last NEW board; the stuck rule resets since_new
                         # every stuck_limit actions, so it can never reach the give-up threshold
    level = int(raw.levels_completed)
    level_trace, last_win = [], []
    replay_queue = []
    eff, pos, visited_pos, blocked = {}, None, set(), set()
    chosen = [None]
    seek_path, seek_goal, seek_arrived, seek_done = [], [None], [True], set()
    deadly = Counter()          # colours that were next to the object just before it died
    pushable = Counter()        # colours that moved when the object met them
    click_effect = {}           # click target -> how many cells it changed
    diag = Counter()
    lvl_start = [None]
    prev_frame = [None]
    burst_left = [0]
    last_effective = [None]
    newest = [None]
    effect_tries, effect_hits, effect_rate = Counter(), Counter(), {}

    def _akey(a):
        return a if not isinstance(a, tuple) else "click"
    level_log, lvl_actions, lvl_states, lvl_resets, lvl_exhausted = [], 0, set(), 0, 0
    obj = None
    change_count = np.zeros((62, 64), dtype=np.int32)
    row_count = np.zeros(62, dtype=np.int32)
    col_count = np.zeros(64, dtype=np.int32)
    presses_seen = 0
    mask = None

    last_was_reset = [False]

    def step(act):
        nonlocal raw, actions
        before = M1.grid(raw)
        # EVERY path must record the frame the action was taken from, not only the main loop:
        # levels were being won DURING the click scan, so the "frame just before the level ended"
        # was stale and vc33 and sp80 reported no goal rules at all.
        prev_frame[0] = before
        if act == "RESET":
            # MEASURED: 273 of the 12-hour search's game runs ended with a positive score and
            # zero levels - levels won, then thrown away.  A RESET with no action since the
            # previous RESET restarts the WHOLE game from level 1 (found on ls20 earlier), and
            # the stuck rule could fire right after the RESET that follows a game over.
            if last_was_reset[0]:
                return before, before
            last_was_reset[0] = True
            raw = env.step(GameAction.RESET)
            actions += 1
            return before, M1.grid(raw)
        last_was_reset[0] = False
        if isinstance(act, tuple):
            raw = env.step(GameAction.ACTION6, data={"x": int(act[1]), "y": int(act[2])})
        else:
            raw = env.step(GameAction.from_id(int(act)))
        actions += 1
        return before, M1.grid(raw)

    def candidates(g, h):
        if h in acts_of:
            return acts_of[h]
        c = list(keys)
        if can_click:
            clicks = list(scan_hits) if scan_hits else click_targets(
                g, cfg.click_topk, cfg.click_tile, cfg.click_order, cfg.click_edges)
            if keys:
                rng.shuffle(clicks)
                c += clicks[:max(1, int(round(len(clicks) * cfg.click_share)))] if cfg.click_share > 0 else []
            else:
                c += clicks
        if cfg.reset_in_graph:
            c = c + ["RESET"]
        acts_of[h] = c
        return c

    # Find out WHERE clicking does anything - but ONLY when nothing else is working.
    # MEASURED: on ft09 only 16 of 240 sampled clicks change the screen, all in one band, and the
    # rarest-blob targets never touch it: the agent saw ONE state in 3,000 actions, and the scan
    # turned that into 128 states and a level.  Run at the START, the same scan cost lp85
    # 2.78 -> 0.03 and r11l 3.69 -> 0.00: those games already worked, and the scan's wasted
    # actions are punished by the efficiency score, which is squared.
    scan_hits = []

    def run_scan():
        nonlocal actions
        step_px = cfg.click_scan or 6
        for yy in range(1, 63, step_px):
            for xx in range(0, 64, step_px):
                if actions >= cfg.max_actions or time.time() - t0 > seconds:
                    return
                b, af = step(("c", xx, yy))
                if (b[1:63] != af[1:63]).any():
                    scan_hits.append(("c", xx, yy))
                if raw.state.name in ("WIN", "GAME_OVER"):
                    step("RESET")

    # milestone 1 inside the agent: what does each key do to the object it controls
    if cfg.mode == "pos" and keys:
        per = defaultdict(Counter)
        for i in range(cfg.learn_per_key * len(keys)):
            if actions >= cfg.max_actions:
                break
            a = keys[i % len(keys)]
            b, af = step(a)
            d, cells, _w = MV.best_shift(b, af)
            if d is not None:
                per[a][d] += 1
                obj = cells
            if raw.state.name in ("WIN", "GAME_OVER"):
                break
        eff = {a: c.most_common(1)[0][0] for a, c in per.items() if c}
        if obj:
            pos = (min(y for y, _ in obj), min(x for _, x in obj))

    # PER-GAME ADAPTATION, honestly costed: each behaviour is tried INSIDE this game, so every
    # probe action counts against the efficiency score exactly as it will on Kaggle.  The winner
    # is the behaviour that crossed the most levels, then found the most new states per action.
    base_cfg = cfg
    pool_names = [n for n in cfg.adapt_pool.split("|") if n in BEHAVIOURS] if cfg.adapt else []
    # MEASURED: trying eight behaviours up front, 150 actions each, cost as much as it gained
    # (mean 1.3306 without, 1.3336 with) - 1,200 presses before the real attempt, punished by an
    # efficiency score that is squared.  So wait until the plain way has clearly stalled.
    trial_names = [] if cfg.adapt_after else list(pool_names)
    trial_at, trial_i, trial_marks, trials = cfg.adapt, 0, (0, 0), {}
    trial_order0 = list(pool_names)
    if trial_names:
        cfg = replace(base_cfg, **BEHAVIOURS[trial_names[0]])

    while actions < cfg.max_actions and time.time() - t0 < seconds:
        if trial_names and actions >= trial_at:
            name = trial_names[trial_i]
            trials[name] = (level - trial_marks[0], len(seen_states) - trial_marks[1])
            trial_i += 1
            if trial_i < len(trial_names):
                trial_marks = (level, len(seen_states))
                trial_at = actions + base_cfg.adapt
                cfg = replace(base_cfg, **BEHAVIOURS[trial_names[trial_i]])
                step("RESET")
                pos, obj, scan_hits[:] = None, None, []
                # each behaviour is judged on its OWN work: without this, later behaviours
                # inherited the map the earlier ones had built and looked better than they were
                edges.clear(); tried.clear(); acts_of.clear(); seen_states.clear()
                trial_marks = (level, 0)
                continue
            # MEASURED: choosing purely on states-per-action switched away from plain on noise
            # and cost ft09 its level (0.1156 -> 0).  A behaviour has to EARN the switch: more
            # levels, or clearly more of the game seen.
            base_lv, base_st = trials.get(trial_order0[0], (0, 0))
            best_name, best_key = trial_order0[0], (base_lv, base_st)
            for n, (lv, st) in trials.items():
                if lv > best_key[0] or (lv == best_key[0] and st > 1.5 * max(1, best_key[1])):
                    best_name, best_key = n, (lv, st)
            cfg = replace(base_cfg, **BEHAVIOURS[best_name])
            trial_names = []
            edges.clear(); tried.clear(); acts_of.clear(); seen_states.clear()
            chosen[0] = best_name
            step("RESET")
            pos, obj, scan_hits[:] = None, None, []
            continue
        st = raw.state.name
        diag["state_" + st] += 1
        if st == "GAME_OVER" and cfg.avoid_death and pos is not None and prev_frame[0] is not None:
            pf = prev_frame[0]
            for dy in (-6, -3, 0, 3, 6):
                for dx in (-6, -3, 0, 3, 6):
                    y, x = pos[0] + dy, pos[1] + dx
                    if 1 <= y < 63 and 0 <= x < 64:
                        deadly[int(pf[y, x])] += 1
            diag["death_seen"] += 1
        if st == "WIN":
            break
        if hook is not None and st == "GAME_OVER":
            hook.on_death(prev_frame[0])
        if st != "NOT_FINISHED":
            # GAME_OVER, and also NOT_STARTED: offline the game is already running when the
            # first frame arrives, but through the competition's gateway a game begins
            # un-started and every action before the first RESET is wasted.
            step("RESET")
            pos, obj = None, None
            if raw.state.name == st and st not in ("GAME_OVER",):
                break                      # a RESET that changes nothing: nothing to play here
            continue
        if int(raw.levels_completed) != level:
            if lvl_start[0] is None or prev_frame[0] is None:
                rules = ["NOFRAMES"]
            elif not (lvl_start[0] != prev_frame[0]).any():
                rules = ["SAMEFRAME"]           # the level's start and its last frame are equal
            else:
                rules = level_rules(lvl_start[0], prev_frame[0]) or ["NODIFF"]
            level_log.append(dict(level=level, actions=lvl_actions, states=len(lvl_states),
                                  resets=lvl_resets, exhausted=lvl_exhausted, ended="won",
                                  rules=rules))
            lvl_start[0] = M1.grid(raw)
            lvl_actions, lvl_states, lvl_resets, lvl_exhausted = 0, set(), 0, 0
            last_win = list(level_trace)
            level_trace = []
            level = int(raw.levels_completed)
            edges.clear(); tried.clear(); acts_of.clear()
            visited_pos, blocked = set(), set()
            pos, obj = None, None
            since_new = 0
            dry_run = 0
            if cfg.replay and last_win:
                replay_queue = list(last_win)
            if hook is not None:
                hook.on_level(level, M1.grid(raw))
        g = M1.grid(raw)
        if lvl_start[0] is None:
            lvl_start[0] = g
        prev_frame[0] = g
        if (pool_names and not trial_names and not trials and base_cfg.adapt_after
                and actions >= base_cfg.adapt_after and level == 0):
            trial_names = list(pool_names)
            trial_at = actions + base_cfg.adapt
            trial_marks = (level, 0)
            cfg = replace(base_cfg, **BEHAVIOURS[trial_names[0]])
            step("RESET")
            pos, obj, scan_hits[:] = None, None, []
            edges.clear(); tried.clear(); acts_of.clear(); seen_states.clear()
            continue
        if (cfg.scan_after and can_click and not scan_hits and actions >= cfg.scan_after
                and len(seen_states) <= 1):
            run_scan()
            acts_of.clear()
            continue
        if mask is None and presses_seen >= cfg.mask_after:
            # a whole row or column that changes on nearly every press is a counter or bar,
            # even when no single cell of it does (ls20's step bar drains one cell per press)
            m = change_count > cfg.volatile * presses_seen
            m[row_count > cfg.volatile * presses_seen, :] = True
            m[:, col_count > cfg.volatile * presses_seen] = True
            if m.all():
                m[:] = False
            if m.any():
                mask = m
                edges.clear(); tried.clear(); acts_of.clear(); seen_states.clear()
        h = (state_hash(g, mask) if cfg.abstract == "full"
             else hashlib.blake2b(abstract_state(g, cfg.abstract, cfg.abstract_block,
                                                 pos, mask), digest_size=10).digest())
        if cfg.max_states and len(edges) > cfg.max_states:
            # keep the agent's memory bounded; on Kaggle 110 games run as threads in ONE process
            edges.clear(); tried.clear(); acts_of.clear()
        lvl_states.add(h)
        if h not in seen_states:
            seen_states.add(h)
            newest[0] = h
            since_new = 0
            dry_run = 0
        # MEASURED: with the dry share required at 0.9 the rule never fired at all in a short
        # trial - the stuck games do still find the occasional new board, which resets the
        # counter, and the dry share is computed per level.  No new state for a long stretch,
        # with no level won, is the signal that matters.
        # MEASURED at the shipped settings (100,000 actions, 2 seeds): tu93 finished in 20,285
        # actions, but lp85 burned 99,506 with 99,475 of them dry, ft09 99,338 with 99,214 dry,
        # vc33 98,529 with 97,294 dry.  They won level 1 early and then spent 98,000 actions
        # achieving nothing, with efficiency squared against them the whole way.  The old rule
        # only fired when NO level had been won, which is why it never fired at all.
        if (cfg.give_up_after and dry_run >= cfg.give_up_after
                and lvl_exhausted >= cfg.give_up_dry * max(1, lvl_actions)):
            diag["gave_up_at"] = actions
            break
        if cfg.stuck_limit and since_new > cfg.stuck_limit and not (hook is not None and hook.steering()):
            lvl_resets += 1
            step("RESET")
            if hook is not None:
                hook.on_reset()
            since_new = 0
            pos, obj = None, None
            continue

        act = None
        if hook is not None:
            act = hook.act(g, raw, level)
            if act is not None:
                diag["nav_steps"] += 1
        # --- aim at a rare object, by planning a path over positions ---
        if (cfg.seek and eff and pos is not None and level == 0
                and actions >= cfg.seek_after and not seek_path):
            if seek_goal[0] is None or seek_arrived[0]:
                body = g[1:63]
                vals, cnts = np.unique(body, return_counts=True)
                bg = int(vals[int(cnts.argmax())])
                cands = []
                # MEASURED on tu93: the two nearest "rare" objects were colour 4 and colour 9 -
                # the avatar's own marker and body.  The agent aimed at ITSELF, planned a
                # zero-step path, and crossed the target off.  Its own colours are excluded, and
                # so is anything it is already standing on.
                own = {int(body[y - 1, x]) for y, x in (obj or set())
                       if 1 <= y < 63 and 0 <= x < 64}
                for c, n in zip(vals, cnts):
                    c = int(c)
                    if c == bg or c in seek_done or c in own:
                        continue
                    k, cells = _blobs(body, c)
                    if 0 < k <= 3 and n <= 200:          # rare things: doors, flags, keys
                        cy, cx = cells.mean(0)
                        dist = abs(cy + 1 - pos[0]) + abs(cx - pos[1])
                        if dist < 4:
                            continue                      # already there
                        cands.append((dist, c, (int(cy) + 1, int(cx))))
                cands.sort()
                if cands:
                    _d, colour_t, target = cands[0]
                    seek_goal[0], seek_arrived[0] = (colour_t, target), False
                    diag["seek_targets"] += 1
                else:
                    seek_goal[0] = None
            if seek_goal[0] is not None:
                # shortest path over the positions the object can occupy, using the learned moves
                tgt = seek_goal[0][1]
                # shortest path over the lattice the object can occupy.  MEASURED: the first
                # version took the START as its own best node, so prev[best] was None and no path
                # was ever produced - tu93 proposed 3 targets and planned 0 paths.  Now the start
                # is excluded as a destination and the search runs to exhaustion of the lattice.
                q, prev = deque([pos]), {pos: None}
                best, bestd = None, 10 ** 9
                while q:
                    u = q.popleft()
                    for a, dd in eff.items():
                        if (u, a) in blocked:
                            continue
                        v = (u[0] + dd[1], u[1] + dd[0])
                        if v in prev or not (1 <= v[0] < 63 and 0 <= v[1] < 64):
                            continue
                        prev[v] = (u, a)
                        d = abs(v[0] - tgt[0]) + abs(v[1] - tgt[1])
                        if d < bestd:
                            best, bestd = v, d
                        q.append(v)
                    if len(prev) > 20000:
                        break
                if best is not None:
                    path, node = [], best
                    while prev[node] is not None:
                        node, a = prev[node]
                        path.append(a)
                    seek_path.extend(reversed(path))
                    diag["seek_plans"] += 1
                    diag["seek_pathlen"] += len(path)
                if not seek_path:
                    seek_done.add(seek_goal[0][0])
                    seek_goal[0] = None
                    if len(seek_done) >= cfg.seek_max_targets:
                        cfg = replace(cfg, seek=False)
        if seek_path:
            act = seek_path.pop(0)
            diag["seek_steps"] += 1
        if act is None and (cfg.repeat_key and last_effective[0] is not None
                and rng.random() < cfg.repeat_key):
            # some games turn first and move second, so the same key twice is not a wasted press
            act = last_effective[0]
        if act is None and burst_left[0] > 0:
            burst_left[0] -= 1
            cand = candidates(g, h)
            if cand:
                act = rng.choice(cand)
        if act is None and replay_queue:
            act = replay_queue.pop(0)
        if act is None and cfg.mode == "pos" and eff and pos is not None:
            # prefer a key that leads to a position never stood on and not known to be blocked
            opts = []
            bad = {c for c, n in deadly.items() if n >= 3} if cfg.avoid_death else set()
            for a, d in eff.items():
                nxt = (pos[0] + d[1], pos[1] + d[0])
                if (pos, a) in blocked:
                    continue
                if bad and 1 <= nxt[0] < 63 and 0 <= nxt[1] < 64 and int(g[nxt[0], nxt[1]]) in bad:
                    diag["death_avoided"] += 1
                    continue
                opts.append((nxt in visited_pos, rng.random(), a))
            if opts:
                opts.sort()
                if not opts[0][0]:
                    act = opts[0][2]
        if act is None:
            cand = candidates(g, h)
            untried = [a for a in cand if a not in tried[h]]
            if untried and cfg.click_rank and click_effect:
                untried.sort(key=lambda a: -click_effect.get(a, 0) if isinstance(a, tuple) else 0)
                act = untried[0]
            elif untried:
                if cfg.prefer_effect:
                    untried.sort(key=lambda a: (-effect_rate.get(_akey(a), 0.0), rng.random()))
                    act = untried[0]
                else:
                    act = rng.choice(untried)
            else:
                # walk towards the nearest state that still has an untried action
                q, prev, target = deque([h]), {h: None}, None
                while q:
                    u = q.popleft()
                    if u != h and any(a not in tried[u] for a in acts_of.get(u, [])):
                        target = u
                        break
                    for a in acts_of.get(u, []):
                        v = edges.get((u, a))
                        if v is not None and v not in prev:
                            prev[v] = (u, a)
                            q.append(v)
                else:
                    lvl_exhausted += 1          # nothing left untried anywhere it can reach
                if target is not None:
                    node = target
                    while prev[node] is not None and prev[node][0] != h:
                        node = prev[node][0]
                    act = prev[node][1]
                elif cfg.dry_deep and newest[0] is not None and newest[0] != h:
                    # head back to the state where something new last appeared, and try there
                    q2, prev2 = deque([h]), {h: None}
                    while q2:
                        u = q2.popleft()
                        if u == newest[0]:
                            break
                        for a2 in acts_of.get(u, []):
                            v2 = edges.get((u, a2))
                            if v2 is not None and v2 not in prev2:
                                prev2[v2] = (u, a2)
                                q2.append(v2)
                    if newest[0] in prev2 and prev2[newest[0]] is not None:
                        node = newest[0]
                        while prev2[node] is not None and prev2[node][0] != h:
                            node = prev2[node][0]
                        act = prev2[node][1]
                    else:
                        act = rng.choice(cand) if cand else "RESET"
                elif cfg.burst:
                    # Return, then explore.  MEASURED: when the agent runs dry it has nothing
                    # untried ANYWHERE it can reach - vc33 level 3 wandered 1,732 presses in a
                    # 36-state pocket.  These games are one-way, so the way out is to go back to
                    # the level's start and take a FRESH random run from there.  (Resetting
                    # without the random run was tried and rejected: it froze, because the start
                    # state has nothing untried either.)
                    burst_left[0] = cfg.burst
                    act = "RESET"
                elif cfg.reset_when_dry:
                    # MEASURED: on vc33 level 3 the agent found 36 states, then wandered at
                    # random for 1,732 presses with nothing untried; ls20 the same, 2,374 times.
                    # These games are one-way - fluid poured, a corner walked into - and the only
                    # way back to the untried part of the game is the level's own start.
                    act = "RESET"
                elif cand:
                    act = rng.choice(cand)
                else:
                    act = "RESET"
        b, af = step(act)
        if hook is not None:
            if act == "RESET":
                hook.on_reset()
            else:
                hook.observe(act, b, af, raw, level_changed=int(raw.levels_completed) != level,
                             died=raw.state.name == "GAME_OVER")
        lvl_actions += 1
        since_new += 1
        dry_run += 1
        level_trace.append(act)
        if act != "RESET":
            dd = b[1:63] != af[1:63]
            change_count += dd
            row_count += dd.any(axis=1)
            col_count += dd.any(axis=0)
            presses_seen += 1
        h2 = (state_hash(af, mask) if cfg.abstract == "full"
              else hashlib.blake2b(abstract_state(af, cfg.abstract, cfg.abstract_block, pos, mask),
                                   digest_size=10).digest())
        changed_now = bool((b[1:63] != af[1:63]).any())
        diag["acts"] += 1
        diag["changed"] += int(changed_now)
        diag["click" if isinstance(act, tuple) else "key"] += 1
        if isinstance(act, tuple):
            diag["click_changed"] += int(changed_now)
            if cfg.click_rank:
                click_effect[act] = max(click_effect.get(act, 0),
                                        int((b[1:63] != af[1:63]).sum()))
        else:
            diag["key_changed"] += int(changed_now)
        if h2 not in seen_states:
            diag["new_state"] += 1
        k = _akey(act)
        effect_tries[k] += 1
        effect_hits[k] += int(changed_now)
        effect_rate[k] = effect_hits[k] / max(1, effect_tries[k])
        last_effective[0] = act if changed_now else None
        if act != "RESET":
            tried[h].add(act)
            edges[(h, act)] = h2
        if cfg.seek and seek_goal[0] is not None and not seek_path and diag.get("seek_steps"):
            seek_arrived[0] = True
            seek_done.add(seek_goal[0][0])       # walked the whole way and the level did not end
        if cfg.push and act in eff and pos is not None:
            sh = MV.best_shift(b, af)[0]
            if sh is not None and sh == eff[act]:
                moved_cols = set()
                for c in np.unique(b[1:63]):
                    c = int(c)
                    gone = ((b[1:63] == c) & (af[1:63] != c)).sum()
                    if gone and c not in (int(np.bincount(b[1:63].ravel().clip(0, 15),
                                                          minlength=16).argmax()),):
                        moved_cols.add(c)
                for c in moved_cols:
                    pushable[c] += 1
                diag["push_seen"] += len(moved_cols)
        if cfg.mode == "pos" and eff and act in eff:
            d, cells, _w = MV.best_shift(b, af)
            if pos is not None:
                if d is None:
                    blocked.add((pos, act))
                elif d == eff[act]:
                    visited_pos.add(pos)
            if cells:
                obj = cells
                pos = (min(y for y, _ in obj), min(x for _, x in obj))
                visited_pos.add(pos)

    level_log.append(dict(level=level, actions=lvl_actions, states=len(lvl_states),
                          resets=lvl_resets, exhausted=lvl_exhausted,
                          ended="won" if raw.state.name == "WIN" else raw.state.name))
    out = dict(diag=dict(diag), effects={str(a): list(d) for a, d in eff.items()},
               chose=chosen[0], trials=trials, game=game, actions=actions, levels=int(raw.levels_completed), state=raw.state.name,
               states_seen=len(seen_states), seconds=round(time.time() - t0, 1), score=0.0,
               level_log=level_log)
    if card:
        sc = arc.close_scorecard(card)
        for e in sc.environments:
            if e.id.startswith(game):
                out["score"] = round(float(e.score), 4)
                # the scorecard's own per-level counts: these are what the leaderboard scores,
                # and they include the probe, scan and reset presses that level_log leaves out
                for run in (e.runs or [])[:1]:
                    out["card_levels"] = [int(x) for x in (run.level_actions or [])]
                    out["card_baseline"] = [int(x) for x in (run.level_baseline_actions or [])]
                    out["card_scores"] = [round(float(x), 3) for x in (run.level_scores or [])]
    if hook is not None:
        out["nav"] = hook.report()
    return out
