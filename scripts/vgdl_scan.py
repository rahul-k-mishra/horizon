"""
vgdl_scan.py -- a feasibility scan of the GVGAI single-player grid-physics games (EXPLORATORY).

Reads only committed files: the VGDL descriptions and level files vendored under
third_party/gvgai/examples (GVGAI commit e58ff6597319155218759cc178931e05b81b524c, GPL-3.0, see
third_party/gvgai/LICENSE.txt) and the game list examples/all_games_sp.csv.  It plays nothing and
runs no simulator.  It answers three questions of docs/DESIGN.md, Section 3:
    1. how many games have a level-0 file and parse;
    2. how many are deterministic by the rule below, so that a breadth-first search over the forward
       model is well defined (a GVGAI forward-model copy draws from a fresh, unseeded generator,
       src/core/game/ForwardModel.java:452, so a random element makes a search state ambiguous);
    3. whether a first reading of A1 to A5 from the description varies across those games, since the
       oracle test found that on MiniGrid/BabyAI the truth vector barely varied (docs/oracle/READING.md,
       Section 5).
The readings of A1 to A5 here are a scan, not the registered truth tables: the registered generator
(docs/DESIGN.md, Section 4) is written and hand-checked separately, and may differ from this scan.

Deterministic rule (from the ontology source vendored under third_party/gvgai/src/ontology): a game
is stochastic if its SpriteSet uses a class that draws from the game's random generator, or one that
inherits from such a class (RandomNPC and its subclasses Chaser, Fleeing, LOSChaser, AlternateChaser,
PathAltChaser, RandomAltChaser, RandomPathAltChaser, PathChaser, RandomInertial; Walker, WalkerJumper;
RandomMissile, ErraticMissile; RandomBomber, BomberRandomMissile), or a producer with prob strictly
between 0 and 1 (SpawnPoint, SpawnPointMultiSprite, Bomber; Spreader with spreadprob), or if its
InteractionSet uses a random effect (flipDirection, attractGaze, transformToRandomChild,
teleportToExit, decreaseSpeedToAll, increaseSpeedToAll, setSpeedForAll) or any effect with prob
strictly between 0 and 1.

Scan readings (each "holds" or "fails"; the rules are in the functions below):
    A1  the avatar class has movement or use actions (every class except NullAvatar);
    A2  no sprite other than the avatar moves or appears as a function of the action: fails for
        shooting avatars and for push effects (bounceForward, pullWithIt) with the avatar as partner;
    A3  each movement action shifts the avatar by one constant vector: holds for MovingAvatar,
        HorizontalAvatar, VerticalAvatar and FlakAvatar at speed 1, and for OrientedAvatar and
        ShootAvatar only with rotateInPlace=False (they turn in place by default,
        src/ontology/physics/GridPhysics.java:78-82); fails for every other avatar class, for a speed
        other than 1, and when an effect moves the avatar (teleportToExit, wrapAround, pullWithIt,
        bounceForward, windGust, slipForward, conveySprite, attractGaze);
    A4  every sprite that blocks the avatar (stepBack or undoAll with the avatar) is of a class that
        does not move on its own (Immovable, Passive, Door, Resource, ResourcePack) and is not made by a
        producer or a spawn effect;
    A5  the only winning condition is a SpriteCounter with limit 0 on one sprite type, level 0 holds
        exactly one sprite of it, and every interaction that removes it has the avatar as partner.

Outputs docs/design/vgdl_scan.json and the console (logs/vgdl_scan.log).
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\vgdl_scan.py > logs\\vgdl_scan.log
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GV = os.path.join(REPO, "third_party", "gvgai")

AVATARS = {"MovingAvatar", "HorizontalAvatar", "VerticalAvatar", "FlakAvatar", "NullAvatar", "OrientedAvatar",
           "ShootAvatar", "AimedAvatar", "BirdAvatar", "CarAvatar", "LanderAvatar", "MissileAvatar", "OngoingAvatar",
           "OngoingShootAvatar", "OngoingTurningAvatar", "PlatformerAvatar", "ShootOnlyAvatar", "SpaceshipAvatar",
           "WizardAvatar", "InertialAvatar", "MarioAvatar"}
LATTICE = {"MovingAvatar", "HorizontalAvatar", "VerticalAvatar", "FlakAvatar"}
ROTATING = {"OrientedAvatar", "ShootAvatar"}
SHOOTERS = {"ShootAvatar", "FlakAvatar", "OngoingShootAvatar", "ShootOnlyAvatar", "AimedAvatar"}
RANDOM_CLASSES = {"RandomNPC", "Chaser", "Fleeing", "LOSChaser", "AlternateChaser", "PathAltChaser", "RandomAltChaser",
                  "RandomPathAltChaser", "PathChaser", "RandomInertial", "Walker", "WalkerJumper", "RandomMissile",
                  "ErraticMissile", "RandomBomber", "BomberRandomMissile"}
PROB_PRODUCERS = {"SpawnPoint": "prob", "SpawnPointMultiSprite": "prob", "Bomber": "prob", "Spreader": "spreadprob"}
RANDOM_EFFECTS = {"flipDirection", "attractGaze", "transformToRandomChild", "teleportToExit", "decreaseSpeedToAll",
                  "increaseSpeedToAll", "setSpeedForAll"}
MOVE_AVATAR_EFFECTS = {"teleportToExit", "wrapAround", "pullWithIt", "bounceForward", "windGust", "slipForward",
                       "conveySprite", "attractGaze"}
PUSH_EFFECTS = {"bounceForward", "pullWithIt"}
STILL_CLASSES = {"Immovable", "Passive", "Door", "Resource", "ResourcePack"}
PRODUCERS = {"SpawnPoint", "SpawnPointMultiSprite", "Bomber", "RandomBomber", "BomberRandomMissile", "Spreader",
             "Portal", "SpriteProducer"}
SPAWN_EFFECTS = {"spawn", "spawnAbove", "spawnBelow", "spawnLeft", "spawnRight", "spawnBehind", "spawnIfHasMore",
                 "spawnIfHasLess", "spawnIfCounterSubTypes", "cloneSprite", "transformTo", "transformToAll",
                 "transformToSingleton", "transformIfCount", "transformToRandomChild"}



def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

def params(tokens):
    out = {}
    for t in tokens:
        if "=" in t:
            k, v = t.split("=", 1)
            out[k] = v
    return out


def fnum(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def parse(text):
    """Sections of a VGDL description: sprites {name: {class, params, parents}}, mapping {char: [names]},
    interactions [(names, effect, params)], terminations [(class, params)], game params."""
    lines = [ln.rstrip() for ln in text.replace("\t", "    ").splitlines()]
    lines = [ln for ln in lines if ln.strip() and not ln.strip().startswith("#")]
    game = params(lines[0].split()[1:]) if lines else {}
    sections, cur = collections.defaultdict(list), None
    for ln in lines[1:]:
        s = ln.strip()
        if s in ("SpriteSet", "LevelMapping", "InteractionSet", "TerminationSet"):
            cur = s
            continue
        if cur:
            sections[cur].append(ln)
    sprites, stack = {}, []        # stack of (indent, name)
    for ln in sections["SpriteSet"]:
        ind = len(ln) - len(ln.lstrip())
        s = ln.strip()
        if ">" not in s:
            continue
        name, rest = [x.strip() for x in s.split(">", 1)]
        while stack and stack[-1][0] >= ind:
            stack.pop()
        parent = sprites.get(stack[-1][1]) if stack else None
        toks = rest.split()
        cls = toks[0] if toks and "=" not in toks[0] else None
        p = dict(parent["params"]) if parent else {}
        p.update(params(toks))
        sprites[name] = dict(cls=cls or (parent["cls"] if parent else None), params=p,
                             parents=([stack[-1][1]] + parent["parents"]) if parent else [])
        stack.append((ind, name))
    mapping = {}
    for ln in sections["LevelMapping"]:
        s = ln.strip()
        if ">" in s:
            ch, rest = s.split(">", 1)
            mapping[ch.strip()] = rest.split()
    inter = []
    for ln in sections["InteractionSet"]:
        s = ln.strip()
        if ">" in s:
            lhs, rhs = s.split(">", 1)
            toks = rhs.split()
            if toks:
                inter.append((lhs.split(), toks[0], params(toks[1:])))
    term = []
    for ln in sections["TerminationSet"]:
        toks = ln.split()
        if toks:
            term.append((toks[0], params(toks[1:])))
    return dict(game=game, sprites=sprites, mapping=mapping, inter=inter, term=term)


def members(d, name):
    """A name and every sprite that has it as an ancestor (VGDL type hierarchy)."""
    return {n for n, s in d["sprites"].items() if n == name or name in s["parents"]}


def scan_game(name, desc_path, lvl_path):
    d = parse(read_text(desc_path))
    sp = d["sprites"]
    avatars = sorted(n for n, s in sp.items() if s["cls"] in AVATARS)
    leaf_av = [n for n in avatars if not any(n in sp[m]["parents"] for m in avatars)]
    av_cls = sorted({sp[n]["cls"] for n in avatars})
    av_names = set().union(*[members(d, n) for n in avatars]) if avatars else set()
    av_names |= {p for n in avatars for p in sp[n]["parents"]}
    reasons = []
    for n, s in sp.items():
        if s["cls"] in RANDOM_CLASSES:
            reasons.append(f"sprite {n} is {s['cls']}")
        if s["cls"] in PROB_PRODUCERS:
            pv = fnum(s["params"].get(PROB_PRODUCERS[s["cls"]]), 1.0)
            if 0 < pv < 1:
                reasons.append(f"sprite {n} is {s['cls']} with {PROB_PRODUCERS[s['cls']]}={pv}")
    for names, eff, p in d["inter"]:
        if eff in RANDOM_EFFECTS:
            reasons.append(f"effect {eff} on {' '.join(names)}")
        pv = fnum(p.get("prob"), 1.0)
        if 0 < pv < 1:
            reasons.append(f"effect {eff} on {' '.join(names)} with prob={pv}")
    level = read_text(lvl_path).splitlines() if lvl_path else []
    counts = collections.Counter(ch for row in level for ch in row)

    def n_in_level(stype):
        mem = members(d, stype)
        return sum(c for ch, c in counts.items() if any(x in mem for x in d["mapping"].get(ch, [])))

    a = {}
    a["A1"] = "holds" if av_cls and av_cls != ["NullAvatar"] else "fails"
    pushes = [eff for names, eff, _ in d["inter"] if eff in PUSH_EFFECTS and len(names) > 1
              and names[0] not in av_names and any(x in av_names for x in names[1:])]
    a["A2"] = "holds" if len(leaf_av) >= 1 and not (set(av_cls) & SHOOTERS) and not pushes else "fails"
    moved = [eff for names, eff, _ in d["inter"] if eff in MOVE_AVATAR_EFFECTS and names and names[0] in av_names]
    a3 = bool(av_cls)
    for n in avatars:
        s = sp[n]
        if n not in leaf_av:
            continue
        rot = s["params"].get("rotateInPlace", "").lower()
        speed = fnum(s["params"].get("speed"), 1.0)
        ok = s["cls"] in LATTICE or (s["cls"] in ROTATING and rot == "false")
        a3 = a3 and ok and speed == 1.0
    a["A3"] = "holds" if a3 and not moved else "fails"
    blockers = set()
    for names, eff, _ in d["inter"]:
        if eff in ("stepBack", "undoAll") and names and names[0] in av_names:
            for x in names[1:]:
                blockers |= members(d, x)
    made = set()
    for n, s in sp.items():
        if s["cls"] in PRODUCERS and s["params"].get("stype"):
            made |= members(d, s["params"]["stype"])
    for names, eff, p in d["inter"]:
        if eff in SPAWN_EFFECTS and p.get("stype"):
            made |= members(d, p["stype"])
    bad = [b for b in blockers if b != "EOS" and (sp.get(b, {}).get("cls") not in STILL_CLASSES | {None} or b in made)]
    a["A4"] = "holds" if not bad else "fails"
    wins = [(c, p) for c, p in d["term"] if p.get("win", "").lower() == "true"]
    a5 = False
    if len(wins) == 1 and wins[0][0] == "SpriteCounter" and fnum(wins[0][1].get("limit"), 0) == 0:
        goal = wins[0][1].get("stype")
        gm = members(d, goal) if goal else set()
        removers = [(names, eff) for names, eff, _ in d["inter"] if names and names[0] in gm
                    and eff.startswith("kill") or (names and names[0] in gm and eff.startswith("transform"))]
        a5 = bool(goal) and n_in_level(goal) == 1 and bool(removers) and all(
            len(names) > 1 and all(x in av_names for x in names[1:]) for names, _ in removers)
    a["A5"] = "holds" if a5 else "fails"
    n_levels = sum(os.path.exists(os.path.join(os.path.dirname(desc_path), f"{name}_lvl{i}.txt")) for i in range(10))
    return dict(game=name, n_levels=n_levels, avatar_classes=av_cls, deterministic=not reasons, stochastic_reasons=reasons,
                level0_rows=len(level), level0_cols=max((len(r) for r in level), default=0), scan=a,
                win_conditions=[f"{c} {json.dumps(p, sort_keys=True)}" for c, p in wins])


def main():
    games = []
    for line in read_text(os.path.join(GV, "examples", "all_games_sp.csv")).splitlines():
        line = line.strip()
        if line:
            games.append(line.split(",", 1)[1])
    print(f"vgdl_scan: GVGAI commit e58ff6597319155218759cc178931e05b81b524c; {len(games)} games in examples/all_games_sp.csv")
    rows, skipped = [], []
    for rel in games:
        path = os.path.join(GV, rel)
        name = os.path.splitext(os.path.basename(rel))[0]
        if "/gridphysics/" not in rel:
            skipped.append((name, "not grid physics"))
            continue
        lvl = os.path.join(os.path.dirname(path), f"{name}_lvl0.txt")
        if not os.path.exists(path):
            skipped.append((name, "description missing"))
            continue
        if not os.path.exists(lvl):
            skipped.append((name, "no level-0 file"))
            continue
        try:
            rows.append(scan_game(name, path, lvl))
        except Exception as e:  # noqa: BLE001 -- a description that does not parse is reported, not hidden
            skipped.append((name, f"parse error {type(e).__name__}: {e}"))
    for name, why in skipped:
        print(f"skipped {name}: {why}")
    det = [r for r in rows if r["deterministic"]]
    print(f"grid-physics games with a level-0 file that parse: {len(rows)}; deterministic by the rule: {len(det)}")
    print(f"level files of the deterministic games: {sum(r['n_levels'] for r in det)} "
          f"({', '.join(f'{k} levels: {v} games' for k, v in sorted(collections.Counter(r['n_levels'] for r in det).items()))})")
    cause = collections.Counter()
    for r in rows:
        for x in {re.sub(r" (on|with) .*", "", re.sub(r"^sprite \S+ is ", "class ", x)) for x in r["stochastic_reasons"]}:
            cause[x] += 1
    print("causes of non-determinism (games with each cause): " + "; ".join(f"{k} {v}" for k, v in cause.most_common()))
    for label, sub in (("all parsed", rows), ("deterministic", det)):
        print(f"\n== {label} games ({len(sub)})")
        print("avatar classes: " + ", ".join(f"{k} {v}" for k, v in collections.Counter(
            "+".join(r["avatar_classes"]) or "none" for r in sub).most_common()))
        for k in ("A1", "A2", "A3", "A4", "A5"):
            c = collections.Counter(r["scan"][k] for r in sub)
            print(f"{k}: holds {c['holds']}, fails {c['fails']}")
        sc = collections.Counter(sum(r["scan"][k] == "holds" for k in ("A1", "A2", "A3", "A4", "A5")) for r in sub)
        print("score S (number of A1-A5 holding): " + ", ".join(f"S={k}: {sc[k]}" for k in sorted(sc)))
        pat = collections.Counter("".join("1" if r["scan"][k] == "holds" else "0" for k in ("A1", "A2", "A3", "A4", "A5"))
                                  for r in sub)
        print(f"distinct A1-A5 patterns: {len(pat)}; " + ", ".join(f"{k} {v}" for k, v in pat.most_common()))
        cells = sorted(r["level0_rows"] * r["level0_cols"] for r in sub)
        if cells:
            print(f"level-0 grid cells: smallest {cells[0]}, median {cells[len(cells) // 2]}, largest {cells[-1]}")
    print("\n== deterministic games")
    for r in det:
        print(f"{r['game']}: avatar {'+'.join(r['avatar_classes'])}, {r['n_levels']} levels, level 0 {r['level0_rows']}x{r['level0_cols']}, "
              + " ".join(f"{k}={r['scan'][k][0]}" for k in ("A1", "A2", "A3", "A4", "A5")))
    out = os.path.join(REPO, "docs", "design", "vgdl_scan.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(gvgai_commit="e58ff6597319155218759cc178931e05b81b524c", games=rows,
                       skipped=[dict(game=g, reason=w) for g, w in skipped]), f, indent=1)
    print(f"\nwritten {os.path.relpath(out, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
