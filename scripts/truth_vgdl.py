"""
truth_vgdl.py -- the truth tables of HORIZON: A1 to A5 per (game, level), read from the VGDL description
and the level file (docs/DESIGN.md, Section 4; docs/PREREG.md draft v0, Section 5).

Reads only the vendored GVGAI files under third_party/gvgai (commit e58ff6597319155218759cc178931e05b81b524c):
examples/all_games_sp.csv, the grid-physics descriptions examples/gridphysics/<game>.txt and their level
files <game>_lvl<k>.txt, with the framework's two default characters, 'w' for wall and 'A' for avatar,
where a LevelMapping does not name them (src/core/game/BasicGame.java:51-56, not vendored).  Plays nothing and runs no simulator.  Writes docs/truth/gvgai.json: per game,
whether it is deterministic by the rule of scripts/vgdl_scan.py (imported, not copied), and per level
0 to 4 each predicate's verdict ("holds" or "fails") with the clauses that decide it: for each clause the
file, the line number, the text of the line, and what was read from it.

The predicates (the class lists are the module constants below; GVGAI source cited in DESIGN.md):
A1  The avatar present at level start is of a class that responds to at least two actions: every avatar
    class except NullAvatar (only the null action) and MissileAvatar ("has no actions available",
    src/ontology/avatar/oriented/MissileAvatar.java).  Fails if no avatar is present.
A2  Exactly one sprite's displacement is a function of the action.  Fails if the level does not hold
    exactly one avatar sprite at start; if any avatar type of the game is of a class whose use action
    creates a sprite (SHOOTERS; Decision 2 of 24 October 2026: a created sprite is another object
    responding to the action); or if an interaction pushes or pulls a non-avatar sprite with the avatar
    as partner (bounceForward, pullWithIt).
A3  Each movement action shifts the avatar by one constant vector, whatever its position, facing and
    history.  Every avatar type of the game must be MovingAvatar, HorizontalAvatar, VerticalAvatar or
    FlakAvatar without rotateInPlace=True, or OrientedAvatar or ShootAvatar with rotateInPlace=False
    (they turn in place by default, src/ontology/physics/GridPhysics.java:78-82), each at speed 1; and no
    interaction moves the avatar (MOVE_EFFECTS with the avatar as the first sprite).
A4  Every sprite type that blocks the avatar (stepBack or undoAll with the avatar first) is of a class
    that never moves on its own (STILL: Immovable, Passive, Door, Resource, ResourcePack and the stationary
    producers SpawnPoint, SpawnPointMultiSprite, Portal, SpriteProducer) and is created, removed or moved
    only by an interaction the avatar causes: one whose names include only agent-driven sprites, which
    are the avatar, the sprites its use action creates, and any stationary-class sprite moved only by
    those (a box that only the avatar pushes; agent_driven).
    No blocking type at all: holds (the edge of the level is fixed).
A5  The only winning termination is a SpriteCounter with limit 0 on one sprite type G; the level holds
    exactly one sprite of G at start; at least one interaction removes G, and every interaction that
    removes G has only avatar types as partners.  A partner that is an avatar type absent at level start
    (reached by a transform, as with a key) or a conditional kill is recorded as a precondition and keeps
    A5 holding.

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\truth_vgdl.py > logs\\truth_vgdl.log
Options: --root (default third_party/gvgai), --out (default docs/truth/gvgai.json).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import vgdl_scan  # noqa: E402  (the determinism rule of docs/PREREG.md, Section 4)

PREDICATES = ("A1", "A2", "A3", "A4", "A5")
LEVELS = range(5)
AVATARS = {"MovingAvatar", "HorizontalAvatar", "VerticalAvatar", "FlakAvatar", "NullAvatar", "OrientedAvatar",
           "ShootAvatar", "AimedAvatar", "BirdAvatar", "CarAvatar", "LanderAvatar", "MissileAvatar", "OngoingAvatar",
           "OngoingShootAvatar", "OngoingTurningAvatar", "PlatformerAvatar", "ShootOnlyAvatar", "SpaceshipAvatar",
           "WizardAvatar", "InertialAvatar", "MarioAvatar"}
NO_ACTIONS = {"NullAvatar", "MissileAvatar"}
SHOOTERS = {"ShootAvatar", "FlakAvatar", "ShootOnlyAvatar", "AimedAvatar", "OngoingShootAvatar"}
LATTICE = {"MovingAvatar", "HorizontalAvatar", "VerticalAvatar", "FlakAvatar"}
ROTATING = {"OrientedAvatar", "ShootAvatar"}
PUSH_EFFECTS = {"bounceForward", "pullWithIt"}
MOVE_EFFECTS = {"teleportToExit", "wrapAround", "pullWithIt", "bounceForward", "windGust", "slipForward",
                "conveySprite", "attractGaze"}
BLOCK_EFFECTS = {"stepBack", "undoAll"}
STILL = {"Immovable", "Passive", "Door", "Resource", "ResourcePack", "SpawnPoint", "SpawnPointMultiSprite", "Portal",
         "SpriteProducer"}   # classes that never move on their own (the producers here are stationary)
PRODUCERS = {"SpawnPoint", "SpawnPointMultiSprite", "Bomber", "RandomBomber", "BomberRandomMissile", "Spreader",
             "Portal", "SpriteProducer"}
CREATE_EFFECTS = {"spawn", "spawnAbove", "spawnBelow", "spawnLeft", "spawnRight", "spawnBehind", "spawnIfHasMore",
                  "spawnIfHasLess", "spawnIfCounterSubTypes", "cloneSprite", "transformTo", "transformToAll",
                  "transformToSingleton", "transformIfCount", "transformToRandomChild"}
REMOVE_EFFECTS = {"killSprite", "killBoth", "killIfOtherHasMore", "killIfHasLess", "killIfHasMore", "killIfFromAbove",
                  "killIfFrontal", "killIfNotFrontal", "killIfSlow", "killIfFast", "killIfAlive", "killIfNotUpright",
                  "transformTo", "transformToRandomChild", "transformIfCount", "transformToSingleton",
                  "collectResource", "collectResourceIfHeld"}
REMOVE_BY_STYPE = {"killAll", "transformToAll"}
CONDITIONAL = {"killIfOtherHasMore", "killIfHasLess", "killIfHasMore", "killIfFromAbove", "killIfFrontal",
               "killIfNotFrontal", "killIfSlow", "killIfFast", "killIfAlive", "killIfNotUpright", "transformIfCount",
               "collectResourceIfHeld"}
MOVERS_ANY = MOVE_EFFECTS | {"reverseDirection", "turnAround", "flipDirection"}


# ---------------------------------------------------------------- parsing, with line numbers

def relp(path):
    """The path relative to the repository, with forward slashes; the full path if on another drive."""
    try:
        return os.path.relpath(path, REPO).replace("\\", "/")
    except ValueError:
        return os.path.abspath(path).replace("\\", "/")


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

def _params(tokens):
    out = {}
    for t in tokens:
        if "=" in t:
            k, v = t.split("=", 1)
            out[k] = v
    return out


def parse(path):
    """The description with every entry's line: sprites {name: dict(cls, params, param_line, line, text,
    parents)}, mapping {char: (names, line, text)}, inter [dict(names, effect, params, line, text)],
    term [dict(cls, params, line, text)], headers {section: line}."""
    raw = read_text(path).replace("\t", "    ").splitlines()
    d = dict(path=path, sprites={}, mapping={}, inter=[], term=[], headers={})
    section, stack = None, []
    for no, ln in enumerate(raw, 1):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if s in ("SpriteSet", "LevelMapping", "InteractionSet", "TerminationSet"):
            section = s
            d["headers"][s] = no
            continue
        if section is None or ">" not in s and section != "TerminationSet":
            continue
        if section == "SpriteSet":
            ind = len(ln) - len(ln.lstrip())
            name, rest = [x.strip() for x in s.split(">", 1)]
            while stack and stack[-1][0] >= ind:
                stack.pop()
            parent = d["sprites"].get(stack[-1][1]) if stack else None
            toks = rest.split()
            cls = toks[0] if toks and "=" not in toks[0] else None
            params = dict(parent["params"]) if parent else {}
            pline = dict(parent["param_line"]) if parent else {}
            for k, v in _params(toks).items():
                params[k], pline[k] = v, no
            d["sprites"][name] = dict(
                cls=cls or (parent["cls"] if parent else None),
                cls_line=no if cls else (parent["cls_line"] if parent else None),
                params=params, param_line=pline, line=no, text=s,
                parents=([stack[-1][1]] + parent["parents"]) if parent else [])
            stack.append((ind, name))
        elif section == "LevelMapping":
            ch, rest = s.split(">", 1)
            d["mapping"][ch.strip()] = (rest.split(), no, s)
        elif section == "InteractionSet":
            lhs, rhs = s.split(">", 1)
            toks = rhs.split()
            if toks:
                d["inter"].append(dict(names=lhs.split(), effect=toks[0], params=_params(toks[1:]), line=no, text=s))
        elif section == "TerminationSet":
            toks = s.split()
            d["term"].append(dict(cls=toks[0], params=_params(toks[1:]), line=no, text=s))
    # The framework's defaults, which a description overrides by naming the same character or sprite:
    # 'w' places wall and 'A' places avatar (src/core/game/BasicGame.java:51-56); wall is Immovable and
    # avatar is MovingAvatar (src/core/game/Game.java:359-367).  Neither file is vendored; both are read at
    # the commit above, https://github.com/GAIGResearch/GVGAI/tree/e58ff6597319155218759cc178931e05b81b524c.
    for ch, name, line in (("w", "wall", 52), ("A", "avatar", 55)):
        if ch not in d["mapping"]:
            d["mapping"][ch] = ([name], None, f"{ch} > {name} (default of src/core/game/BasicGame.java:{line})")
    for name, cls, line in (("wall", "Immovable", 360), ("avatar", "MovingAvatar", 366)):
        if name not in d["sprites"]:
            d["sprites"][name] = dict(cls=cls, cls_line=None, params={}, param_line={}, line=None, parents=[],
                                      text=f"{name} > {cls} (default of src/core/game/Game.java:{line})")
    return d


def members(d, name):
    """The sprite types a name stands for in an interaction: itself and every descendant."""
    return {n for n, sp in d["sprites"].items() if n == name or name in sp["parents"]}


def leaves(d, names):
    sp = d["sprites"]
    return {n for n in names if n in sp and not any(n in sp[m]["parents"] for m in sp)}


def level_counts(d, level_path):
    """{sprite type: [(line, column), ...]} of the sprites the level file places, via the LevelMapping and
    the framework's defaults for 'w' and 'A' (parse)."""
    out = collections.defaultdict(list)
    for no, row in enumerate(read_text(level_path).splitlines(), 1):
        for col, ch in enumerate(row, 1):
            for n in d["mapping"].get(ch, ([], None, None))[0]:
                out[n].append((no, col))
    return out


# ---------------------------------------------------------------- clauses
def clause(path, line, text, reads):
    if text is None and line:
        rows = read_text(path).splitlines()
        text = rows[line - 1] if 0 < line <= len(rows) else None
    return dict(file=relp(path), line=line, text=text, reads=reads)


def sprite_clause(d, n, reads):
    sp = d["sprites"][n]
    return clause(d["path"], sp["line"], sp["text"], reads)


def inter_clause(d, it, reads):
    return clause(d["path"], it["line"], it["text"], reads)


def header_clause(d, section, reads):
    return clause(d["path"], d["headers"].get(section), section, reads)


# ---------------------------------------------------------------- the predicates
def avatar_types(d):
    return {n for n, sp in d["sprites"].items() if sp["cls"] in AVATARS}


def is_avatar_name(d, name, av):
    """A name in an interaction stands only for avatar types."""
    m = members(d, name)
    return bool(m) and m <= av


def touches_avatar(d, name, av):
    return bool(members(d, name) & av)


def shot_types(d, av):
    """Sprite types the avatar's use action creates: the stype of every shooting avatar type."""
    out = set()
    for n in av:
        sp = d["sprites"][n]
        if sp["cls"] in SHOOTERS and sp["params"].get("stype"):
            out |= members(d, sp["params"]["stype"])
    return out


def agent_driven(d, av):
    """The avatar types, the sprites its use action creates, and every stationary-class type that moves
    only when one of those pushes or pulls it (a box only the avatar pushes), to a fixed point."""
    out = set(av) | shot_types(d, av)
    while True:
        new = set()
        for t, sp in d["sprites"].items():
            if t in out or sp["cls"] not in STILL:
                continue
            moves = [it for it in d["inter"] if it["effect"] in MOVERS_ANY and t in members(d, it["names"][0])]
            if moves and all(any(members(d, n) and members(d, n) <= out for n in it["names"][1:]) for it in moves):
                new.add(t)
        if not new:
            return out
        out |= new


def caused_by_avatar(d, it, driven):
    """An interaction the avatar causes: one of its names stands only for agent-driven sprites."""
    return any(members(d, n) and members(d, n) <= driven for n in it["names"])


def pred_A1(d, start_av):
    if not start_av:
        return "fails", [header_clause(d, "LevelMapping", "no avatar sprite is placed by the level file")]
    cls = {d["sprites"][n]["cls"] for n in start_av}
    cl = [sprite_clause(d, n, f"avatar type {n} is {d['sprites'][n]['cls']}") for n in sorted(start_av)]
    if cls <= NO_ACTIONS:
        return "fails", cl
    return "holds", cl


def pred_A2(d, av, start_av, n_av_sprites, av_positions, level_path):
    fails = []
    if n_av_sprites != 1:
        fails.append(clause(level_path, av_positions[0][0] if av_positions else None, None,
                            f"the level places {n_av_sprites} avatar sprites"))
    for n in sorted(leaves(d, av) | (av & start_av)):
        if d["sprites"][n]["cls"] in SHOOTERS:
            fails.append(sprite_clause(d, n, f"avatar type {n} is {d['sprites'][n]['cls']}: its use action creates a sprite"))
    for it in d["inter"]:
        if it["effect"] in PUSH_EFFECTS and members(d, it["names"][0]) - av and \
                any(touches_avatar(d, p, av) for p in it["names"][1:]):
            fails.append(inter_clause(d, it, f"{it['effect']} moves {it['names'][0]} when the avatar moves into it"))
    if fails:
        return "fails", fails
    return "holds", [sprite_clause(d, n, f"the one avatar sprite at start is {n}, {d['sprites'][n]['cls']}, which creates nothing")
                     for n in sorted(start_av)] + [header_clause(d, "InteractionSet", "no bounceForward or pullWithIt with the avatar as partner")]


def pred_A3(d, av):
    fails, ok = [], []
    for n in sorted(leaves(d, av)):
        sp = d["sprites"][n]
        rot = sp["params"].get("rotateInPlace", "").lower()
        speed = vgdl_scan.fnum(sp["params"].get("speed"), 1.0)
        if sp["cls"] in LATTICE and rot != "true" and speed == 1.0:
            ok.append(sprite_clause(d, n, f"{n} is {sp['cls']} at speed 1"))
        elif sp["cls"] in ROTATING and rot == "false" and speed == 1.0:
            ok.append(clause(d["path"], sp["param_line"]["rotateInPlace"], d["sprites"][n]["text"],
                             f"{n} is {sp['cls']} with rotateInPlace=False at speed 1"))
        elif speed != 1.0:
            fails.append(clause(d["path"], sp["param_line"].get("speed"), sp["text"], f"{n} has speed {speed}"))
        elif sp["cls"] in ROTATING:
            fails.append(sprite_clause(d, n, f"{n} is {sp['cls']}, which turns in place when pressed in a new direction"))
        elif sp["cls"] in LATTICE:
            fails.append(clause(d["path"], sp["param_line"].get("rotateInPlace"), sp["text"], f"{n} has rotateInPlace=True"))
        else:
            fails.append(sprite_clause(d, n, f"{n} is {sp['cls']}, whose motion is not one constant step per action"))
    for it in d["inter"]:
        if it["effect"] in MOVE_EFFECTS and touches_avatar(d, it["names"][0], av):
            fails.append(inter_clause(d, it, f"{it['effect']} moves the avatar"))
    if fails or not ok:
        return "fails", fails or [header_clause(d, "SpriteSet", "no avatar type")]
    return "holds", ok + [header_clause(d, "InteractionSet", "no interaction moves the avatar")]


def pred_A4(d, av):
    driven = agent_driven(d, av)
    blocking = {}
    for it in d["inter"]:
        if it["effect"] in BLOCK_EFFECTS and touches_avatar(d, it["names"][0], av):
            for p in it["names"][1:]:
                if p == "EOS":
                    continue
                for b in leaves(d, members(d, p)) - av:
                    blocking.setdefault(b, it)
    if not blocking:
        return "holds", [header_clause(d, "InteractionSet", "no sprite blocks the avatar (no stepBack or undoAll with "
                                                            "the avatar first, except at the edge)")]
    fails, ok = [], []
    for b, it in sorted(blocking.items()):
        sp = d["sprites"][b]
        ok.append(inter_clause(d, it, f"{b} blocks the avatar"))
        if sp["cls"] not in STILL:
            fails.append(sprite_clause(d, b, f"blocker {b} is {sp['cls']}, not a class that stays in place"))
        for n, ps in d["sprites"].items():
            if ps["cls"] in PRODUCERS and ps["params"].get("stype") and b in members(d, ps["params"]["stype"]):
                fails.append(sprite_clause(d, n, f"producer {n} creates blocker {b}"))
        for it2 in d["inter"]:
            st = it2["params"].get("stype")
            creates = it2["effect"] in CREATE_EFFECTS and bool(st) and b in members(d, st)
            removes = (it2["effect"] in REMOVE_EFFECTS and b in members(d, it2["names"][0])) or                 (it2["effect"] in REMOVE_BY_STYPE and bool(st) and b in members(d, st))
            moves = it2["effect"] in MOVERS_ANY and b in members(d, it2["names"][0])
            if (creates or removes or moves) and not caused_by_avatar(d, it2, driven):
                what = "creates" if creates else ("removes" if removes else "moves")
                fails.append(inter_clause(d, it2, f"{it2['effect']} {what} blocker {b} without the avatar"))
    if fails:
        return "fails", fails
    return "holds", ok + [sprite_clause(d, b, f"blocker {b} is {d['sprites'][b]['cls']}") for b in sorted(blocking)]


def pred_A5(d, av, start_av, counts, level_path):
    wins = [t for t in d["term"] if t["params"].get("win", "").lower() == "true"]
    tcl = [clause(d["path"], t["line"], t["text"], "a winning termination") for t in wins]
    if len(wins) != 1:
        return "fails", tcl or [header_clause(d, "TerminationSet", "no winning termination")]
    t = wins[0]
    limit = vgdl_scan.fnum(t["params"].get("limit"), 0.0)
    if t["cls"] != "SpriteCounter" or limit != 0 or not t["params"].get("stype"):
        return "fails", [clause(d["path"], t["line"], t["text"], f"the win is {t['cls']} (limit {limit:g}), not a "
                                                                  "SpriteCounter with limit 0 on one type")]
    gm = members(d, t["params"]["stype"])
    placed = sorted(p for g in gm for p in counts.get(g, []))
    lcl = clause(level_path, placed[0][0] if placed else None, None, f"the level places {len(placed)} sprite(s) of {t['params']['stype']}")
    if len(placed) != 1:
        return "fails", [tcl[0], lcl]
    removers = [it for it in d["inter"] if (it["effect"] in REMOVE_EFFECTS and members(d, it["names"][0]) & gm)
                or (it["effect"] in REMOVE_BY_STYPE and it["params"].get("stype") and members(d, it["params"]["stype"]) & gm)]
    if not removers:
        return "fails", [tcl[0], lcl, header_clause(d, "InteractionSet", "no interaction removes the goal")]
    bad, pre = [], []
    for it in removers:
        partners = it["names"][1:] if it["effect"] in REMOVE_EFFECTS else it["names"]
        if not partners or not all(is_avatar_name(d, p, av) for p in partners):
            bad.append(inter_clause(d, it, "removes the goal with a partner other than the avatar"))
            continue
        absent = [p for p in partners if not (members(d, p) & start_av)]
        if absent:
            pre.append(inter_clause(d, it, f"precondition: partner {', '.join(absent)} is an avatar type absent at start"))
        if it["effect"] in CONDITIONAL:
            pre.append(inter_clause(d, it, f"precondition: {it['effect']} is conditional"))
    if bad:
        return "fails", [tcl[0]] + bad
    return "holds", [tcl[0], lcl] + [inter_clause(d, it, "the avatar removes the goal") for it in removers] + pre


def truth_for_level(d, level_path):
    counts = level_counts(d, level_path)
    av = avatar_types(d)
    start_av = {n for n in av if counts.get(n)}
    av_positions = sorted(p for n in av for p in counts.get(n, []))
    out = {}
    for name, (v, cl) in (("A1", pred_A1(d, start_av)),
                          ("A2", pred_A2(d, av, start_av, len(av_positions), av_positions, level_path)),
                          ("A3", pred_A3(d, av)), ("A4", pred_A4(d, av)),
                          ("A5", pred_A5(d, av, start_av, counts, level_path))):
        out[name] = dict(verdict=v, clauses=cl)
    return out


def games_of(root):
    out = []
    for line in read_text(os.path.join(root, "examples", "all_games_sp.csv")).splitlines():
        line = line.strip()
        if line and "/gridphysics/" in line:
            out.append(os.path.splitext(os.path.basename(line.split(",", 1)[1]))[0])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(REPO, "third_party", "gvgai"))
    ap.add_argument("--out", default=os.path.join(REPO, "docs", "truth", "gvgai.json"))
    a = ap.parse_args(argv)
    gp = os.path.join(a.root, "examples", "gridphysics")
    games, skipped = {}, []
    for g in games_of(a.root):
        desc = os.path.join(gp, f"{g}.txt")
        lvls = [os.path.join(gp, f"{g}_lvl{k}.txt") for k in LEVELS]
        if not os.path.exists(desc) or not all(os.path.exists(p) for p in lvls):
            skipped.append(f"{g}: description or a level file 0-4 missing")
            continue
        d = parse(desc)
        det = vgdl_scan.scan_game(g, desc, lvls[0])["deterministic"]
        games[g] = dict(description=relp(desc), deterministic=det,
                        levels={str(k): dict(level_file=relp(p),
                                             **truth_for_level(d, p)) for k, p in zip(LEVELS, lvls)})
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(generator="scripts/truth_vgdl.py", gvgai_commit="e58ff6597319155218759cc178931e05b81b524c",
                       games=games), f, indent=1, sort_keys=True)
    det = sorted(g for g in games if games[g]["deterministic"])
    print(f"truth_vgdl: {len(games)} grid-physics games with levels 0-4; {len(det)} deterministic; skipped {len(skipped)}")
    for s in skipped:
        print(f"skipped {s}")
    for label, gs in (("deterministic games", det), ("all games", sorted(games))):
        units = [(g, k) for g in gs for k in games[g]["levels"]]
        print(f"\n== {label}: {len(gs)} games, {len(units)} (game, level) units")
        for p in PREDICATES:
            c = collections.Counter(games[g]["levels"][k][p]["verdict"] for g, k in units)
            print(f"{p}: holds {c['holds']}, fails {c['fails']}")
        sm = collections.Counter(sum(games[g]["levels"][k][p]["verdict"] == "holds" for p in PREDICATES) for g, k in units)
        print("S_M (number holding): " + ", ".join(f"{v}: {sm[v]}" for v in sorted(sm)))
        varying = [g for g in gs if len({tuple(games[g]["levels"][k][p]["verdict"] for p in PREDICATES)
                                         for k in games[g]["levels"]}) > 1]
        print(f"games whose vector differs between levels: {len(varying)}" + (f" ({', '.join(varying)})" if varying else ""))
    print("\n== deterministic games, per level (h holds, f fails; A1 A2 A3 A4 A5)")
    for g in det:
        print(f"{g}: " + "  ".join(f"L{k} " + "".join(games[g]["levels"][k][p]["verdict"][0] for p in PREDICATES)
                                    for k in sorted(games[g]["levels"])))
    print(f"\nwritten {relp(a.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
