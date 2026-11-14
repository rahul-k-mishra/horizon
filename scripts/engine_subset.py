"""
engine_subset.py -- the part of VGDL that the 30 deterministic games use (docs/design/ENGINE.md, Section 2,
the third candidate: an interpreter written here for that subset).

Reads the vendored descriptions of the 30 deterministic games of docs/design/vgdl_scan.json with the parser of
scripts/vgdl_scan.py, and the vendored GVGAI Java source under third_party/gvgai/src.  Prints:
    - the sprite classes, interaction effects and termination classes the 30 descriptions use, each with the
      number of games that use it and the lines of the GVGAI Java file that implements it;
    - the parameters set on sprites, on effects, on terminations and on the game, each with its number of games;
    - the GVGAI core files an interpreter would have to match besides those classes (the game loop, the forward
      model, the sprite base class, the physics, the parser), with their lines;
    - per game, pilot or confirmatory, what GVGAI keeps per sprite that changes over time and that the registered
      state key (docs/PREREG.md, Section 6) leaves out: a sprite of class Flicker, OrientedFlicker or Spreader (its
      age, Flicker.java), SpawnPoint (its counter and first tick, SpawnPoint.java), a sprite other than the avatar
      with healthPoints or limitHealthPoints set (its health), and a sprite with cooldown above 1 (the ticks since
      it last moved, VGDLSprite.lastmove); and whether the registered key holds the tick.
A class or effect is matched to its Java file by name (an effect's name with its first letter in capitals);
a name with no file is listed.  The defaults GVGAI adds when a level mapping leaves out w or A (wall Immovable,
avatar MovingAvatar; docs/truth/DEFAULT_MAPPING.md) are counted as used where they apply.  Plays nothing.

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\engine_subset.py > logs\\engine_subset.log
"""
from __future__ import annotations

import collections
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import vgdl_scan  # noqa: E402

GV = os.path.join(REPO, "third_party", "gvgai")
SRC = os.path.join(GV, "src")
CORE = ["core/game/Game.java", "core/game/ForwardModel.java", "core/game/StateObservation.java",
        "core/vgdl/VGDLSprite.java", "core/vgdl/VGDLParser.java", "core/vgdl/VGDLFactory.java",
        "core/vgdl/VGDLRegistry.java", "core/vgdl/SpriteGroup.java", "core/vgdl/Node.java",
        "ontology/physics/GridPhysics.java", "ontology/Types.java", "ontology/effects/Effect.java",
        "ontology/effects/TimeEffect.java", "core/termination/Termination.java", "tools/Vector2d.java",
        "tools/Direction.java"]


def java_index():
    idx = {}
    for root, _, files in os.walk(SRC):
        for f in files:
            if f.endswith(".java"):
                idx.setdefault(f[:-5], os.path.join(root, f))
    return idx


def lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def main():
    with open(os.path.join(REPO, "docs", "design", "vgdl_scan.json"), encoding="utf-8") as f:
        det = sorted(g["game"] for g in json.load(f)["games"] if g["deterministic"])
    idx = java_index()
    classes, effects, terms = (collections.defaultdict(set) for _ in range(3))
    p_sprite, p_effect, p_term, p_game = (collections.defaultdict(set) for _ in range(4))
    gp = os.path.join(GV, "examples", "gridphysics")
    for g in det:
        d = vgdl_scan.parse(vgdl_scan.read_text(os.path.join(gp, f"{g}.txt")))
        for k in d["game"]:
            p_game[k].add(g)
        for name, s in d["sprites"].items():
            if s["cls"]:
                classes[s["cls"]].add(g)
            for k in s["params"]:
                p_sprite[k].add(g)
        if "wall" not in d["sprites"] and "w" not in d["mapping"]:
            classes["Immovable"].add(g)
        if not any(s["cls"] and "Avatar" in s["cls"] for s in d["sprites"].values()):
            classes["MovingAvatar"].add(g)
        for _names, eff, prm in d["inter"]:
            effects[eff].add(g)
            for k in prm:
                p_effect[k].add(g)
        for cls, prm in d["term"]:
            terms[cls].add(g)
            for k in prm:
                p_term[k].add(g)

    def table(title, dct, to_file):
        print(f"\n== {title}: {len(dct)}")
        total = 0
        missing = []
        for k in sorted(dct, key=lambda x: (-len(dct[x]), x)):
            fn = to_file(k)
            path = idx.get(fn)
            n = lines(path) if path else None
            total += n or 0
            if path is None:
                missing.append(k)
            rel = os.path.relpath(path, GV).replace(os.sep, "/") if path else "no Java file of that name"
            print(f"{k:28s} games {len(dct[k]):2d}   {rel}" + (f"  ({n} lines)" if n else ""))
        print(f"lines of the Java files above: {total}; names with no Java file: {', '.join(missing) or 'none'}")
        return total

    print(f"== the 30 deterministic games (docs/design/vgdl_scan.json): {', '.join(det)}")
    t1 = table("sprite classes", classes, lambda k: k)
    t2 = table("interaction effects", effects, lambda k: k[:1].upper() + k[1:])
    t3 = table("termination classes", terms, lambda k: k)
    for title, dct in (("sprite parameters", p_sprite), ("effect parameters", p_effect),
                       ("termination parameters", p_term), ("game parameters", p_game)):
        print(f"\n== {title}: {len(dct)}")
        print(", ".join(f"{k} ({len(dct[k])})" for k in sorted(dct, key=lambda x: (-len(dct[x]), x))))
    print("\n== GVGAI core files an interpreter must also match")
    tc = 0
    for rel in CORE:
        n = lines(os.path.join(SRC, rel))
        tc += n
        print(f"{rel:44s} {n:5d} lines")
    print(f"lines: classes {t1}, effects {t2}, terminations {t3}, core {tc}; together {t1 + t2 + t3 + tc}")
    print("(lines of Java source, comments and blank lines included; the classes' parent classes are counted only "
          "where a game names them)")

    with open(os.path.join(REPO, "logs", "draw_pilot.log"), encoding="utf-8") as f:
        line = next(ln for ln in f.read().splitlines() if ln.startswith("pilot ("))
    pilot = {x.strip() for x in line.split(":", 1)[1].split(",")}
    print("\n== what the registered key leaves out, per game (P pilot, C confirmatory)")
    hit_games = {"P": [], "C": []}
    for g in det:
        d = vgdl_scan.parse(vgdl_scan.read_text(os.path.join(gp, f"{g}.txt")))
        timed = any(c == "Timeout" for c, _ in d["term"]) or any(
            k in s["params"] for s in d["sprites"].values() for k in ("cooldown", "limit", "total"))
        found = []
        for name, s in sorted(d["sprites"].items()):
            cls, prm = s["cls"], s["params"]
            avatar = bool(cls and "Avatar" in cls)
            if cls in ("Flicker", "OrientedFlicker", "Spreader"):
                found.append(f"{name} {cls} (age)")
            if cls in ("SpawnPoint", "SpawnPointMultiSprite"):
                found.append(f"{name} {cls} (counter, first tick)")
            if not avatar and ("healthPoints" in prm or "limitHealthPoints" in prm):
                found.append(f"{name} health")
            try:
                if float(prm.get("cooldown", "0")) > 1:
                    found.append(f"{name} cooldown {prm['cooldown']} (ticks since last move)")
            except ValueError:
                pass
        tag = "P" if g in pilot else "C"
        if found:
            hit_games[tag].append(g)
        print(f"{tag} {g:18s} key holds the tick: {'yes' if timed else 'no '} | {'; '.join(found) or 'nothing'}")
    print(f"games with something left out: pilot {len(hit_games['P'])} ({', '.join(hit_games['P']) or 'none'}), "
          f"confirmatory {len(hit_games['C'])} ({', '.join(hit_games['C']) or 'none'})")
    print("(a sprite listed under a parent name with no class of its own inherits the parent's class; parents that "
          "are never placed are listed too)")


if __name__ == "__main__":
    main()
