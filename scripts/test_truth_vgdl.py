"""
test_truth_vgdl.py -- synthetic tests of scripts/truth_vgdl.py on small VGDL games written into a temporary
folder laid out like third_party/gvgai.  Reads no vendored file and plays nothing.  Each game exercises
one path of one predicate; the expected verdicts and the line each verdict must cite were worked out by
hand from the texts below.
Run with warnings as errors (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe -W error scripts\\test_truth_vgdl.py
Expected last line: OK
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import truth_vgdl  # noqa: E402

# Every game: line 1 BasicGame, then sections.  Comments give the line numbers the tests check.
BASE = """BasicGame
    SpriteSet
        floor > Immovable
        wall > Immovable
        goal > Door
{avatar}
{extra_sprites}
    LevelMapping
        . > floor
        w > wall
        g > floor goal
        A > floor {start}
{extra_mapping}
    InteractionSet
        avatar wall > stepBack
        goal avatar > killSprite
{extra_inter}
    TerminationSet
        SpriteCounter stype=goal limit=0 win=True
        SpriteCounter stype=avatar limit=0 win=False
"""
LEVEL = "wwwww\nwA.gw\nwwwww\n"

GAMES = {
    # all five hold
    "plain": dict(avatar="        avatar > MovingAvatar"),
    # A1 fails: NullAvatar has only the null action
    "null": dict(avatar="        avatar > NullAvatar"),
    # A2 fails (Decision 2), A3 holds: a shooter that moves one cell per action
    "shooter": dict(avatar="        avatar > ShootAvatar stype=bullet rotateInPlace=False",
                    extra_sprites="        bullet > Missile"),
    # A3 fails: an oriented avatar turns in place by default
    "rotating": dict(avatar="        avatar > OrientedAvatar"),
    # A3 fails: speed 0.5
    "slow": dict(avatar="        avatar > MovingAvatar speed=0.5"),
    # A2 fails: the avatar pushes a box; A4 holds: the door is removed only through the box, and only
    # the avatar moves the box
    "pushbox": dict(avatar="        avatar > MovingAvatar",
                    extra_sprites="        box > Passive\n        hole > Immovable\n        door > Immovable",
                    extra_mapping="        b > floor box\n        h > floor hole\n        d > floor door",
                    extra_inter="        box avatar > bounceForward\n        avatar door > stepBack\n"
                                "        box hole > killAll stype=door"),
    # A4 fails: the same, but a random NPC can also push the box, so the door can open without the avatar
    "npcbox": dict(avatar="        avatar > MovingAvatar",
                   extra_sprites="        box > Passive\n        hole > Immovable\n        door > Immovable\n"
                                 "        bat > RandomNPC",
                   extra_mapping="        b > floor box\n        h > floor hole\n        d > floor door\n"
                                 "        z > floor bat",
                   extra_inter="        box avatar > bounceForward\n        box bat > bounceForward\n"
                               "        avatar door > stepBack\n        box hole > killAll stype=door"),
    # A4 fails: the avatar is blocked by a sprite that moves on its own
    "movingwall": dict(avatar="        avatar > MovingAvatar",
                       extra_sprites="        slider > Missile orientation=LEFT",
                       extra_mapping="        s > floor slider",
                       extra_inter="        avatar slider > stepBack"),
    # A5 holds with a precondition: only the key-holding subtype, absent at start, removes the goal
    "keydoor": dict(avatar="        avatar > MovingAvatar\n            nokey >\n            withkey >",
                    start="nokey",
                    extra_sprites="        key > Immovable",
                    extra_mapping="        k > floor key",
                    extra_inter="        nokey goal > stepBack\n        goal withkey > killSprite\n"
                                "        nokey key > transformTo stype=withkey killSecond=True"),
}
# keydoor's base interaction "goal avatar > killSprite" also names avatar, the parent of both subtypes,
# so it is replaced there by the subtype rule (see build()).

LEVELS = {"twogoals": "wwwwww\nwA.ggw\nwwwwww\n", "twoavatars": "wwwww\nwAAgw\nwwwww\n"}


def build(root):
    gp = os.path.join(root, "examples", "gridphysics")
    os.makedirs(gp)
    lines = []
    for i, (g, spec) in enumerate(list(GAMES.items()) + [("twogoals", {}), ("twoavatars", {}), ("timeout", {}),
                                                         ("nomap", {})]):
        spec = dict(avatar="        avatar > MovingAvatar", extra_sprites="", extra_mapping="", extra_inter="",
                    start="avatar") | spec
        text = BASE.format(**spec)
        if g == "keydoor":
            text = text.replace("        goal avatar > killSprite\n", "")
        if g == "timeout":
            text = text.replace("SpriteCounter stype=goal limit=0 win=True", "Timeout limit=100 win=True")
        if g == "nomap":   # no mapping line for w or A: the framework's defaults place wall and avatar
            text = text.replace("        w > wall\n", "").replace("        A > floor avatar\n", "")
        text = "\n".join(ln for ln in text.splitlines() if ln.strip()) + "\n"
        with open(os.path.join(gp, f"{g}.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        for k in range(5):
            lv = LEVELS.get(g, LEVEL)
            if g == "twogoals" and k > 0:
                lv = LEVEL   # only level 0 has two goals: a level-dependent verdict
            if g == "keydoor":
                lv = lv.replace(".", "k", 1)
            with open(os.path.join(gp, f"{g}_lvl{k}.txt"), "w", encoding="utf-8", newline="\n") as f:
                f.write(lv)
        lines.append(f"{i},examples/gridphysics/{g}.txt")
    with open(os.path.join(root, "examples", "all_games_sp.csv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def line_of(root, game, needle):
    with open(os.path.join(root, "examples", "gridphysics", f"{game}.txt"), encoding="utf-8") as f:
        for no, ln in enumerate(f.read().splitlines(), 1):
            if needle in ln:
                return no
    raise AssertionError(f"{needle!r} not in {game}")


def main():
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)
            print("FAIL:", msg)

    tmp = tempfile.mkdtemp(prefix="horizon-truthtest-")
    try:
        root = os.path.join(tmp, "gvgai")
        build(root)
        out = os.path.join(tmp, "truth.json")
        truth_vgdl.main(["--root", root, "--out", out])
        with open(out, encoding="utf-8") as f:
            t = json.load(f)["games"]

        def v(g, p, k="0"):
            return t[g]["levels"][k][p]["verdict"]

        def cites(g, p, needle, k="0"):
            want = line_of(root, g, needle)
            return any(c["line"] == want and c["file"].endswith(f"{g}.txt") for c in t[g]["levels"][k][p]["clauses"])

        check(all(v("plain", p) == "holds" for p in truth_vgdl.PREDICATES), "plain: every predicate must hold")
        check(cites("plain", "A5", "goal avatar > killSprite"), "plain A5 must cite the removing interaction")
        check(v("null", "A1") == "fails" and cites("null", "A1", "NullAvatar"), "null: A1 fails at the avatar line")
        check(v("shooter", "A2") == "fails" and cites("shooter", "A2", "ShootAvatar"), "shooter: A2 fails at the avatar line")
        check(v("shooter", "A3") == "holds", "shooter with rotateInPlace=False: A3 holds")
        check(v("rotating", "A3") == "fails" and cites("rotating", "A3", "OrientedAvatar"), "rotating: A3 fails")
        check(v("slow", "A3") == "fails" and cites("slow", "A3", "speed=0.5"), "slow: A3 fails at the speed")
        check(v("pushbox", "A2") == "fails" and cites("pushbox", "A2", "box avatar > bounceForward"), "pushbox: A2 fails at the push")
        check(v("pushbox", "A4") == "holds", "pushbox: A4 holds, since only the avatar moves the box that opens the door")
        check(v("npcbox", "A4") == "fails" and cites("npcbox", "A4", "box hole > killAll"), "npcbox: A4 fails at the removal")
        check(v("movingwall", "A4") == "fails" and cites("movingwall", "A4", "slider > Missile"), "movingwall: A4 fails")
        ok_pre = any("precondition" in c["reads"] for c in t["keydoor"]["levels"]["0"]["A5"]["clauses"])
        check(v("keydoor", "A5") == "holds" and ok_pre, "keydoor: A5 holds with a precondition recorded")
        check(v("twogoals", "A5", "0") == "fails" and v("twogoals", "A5", "1") == "holds",
              "twogoals: A5 fails on level 0 (two goals) and holds on level 1")
        lv_clause = [c for c in t["twogoals"]["levels"]["0"]["A5"]["clauses"] if c["file"].endswith("twogoals_lvl0.txt")]
        check(lv_clause and lv_clause[0]["line"] == 2, "twogoals: the level clause cites line 2 of the level file")
        check(v("twoavatars", "A2") == "fails", "twoavatars: A2 fails")
        check(v("timeout", "A5") == "fails" and cites("timeout", "A5", "Timeout"), "timeout: A5 fails at the termination")
        check(all(v("nomap", p) == "holds" for p in truth_vgdl.PREDICATES) and cites("nomap", "A1", "MovingAvatar"),
              "nomap: 'A' places avatar and 'w' places wall by default, so every predicate holds as in plain")
        for g in t:
            for k in t[g]["levels"]:
                for p in truth_vgdl.PREDICATES:
                    e = t[g]["levels"][k][p]
                    check(e["verdict"] in ("holds", "fails") and e["clauses"] and all(c["line"] for c in e["clauses"]),
                          f"{g} level {k} {p}: a verdict with at least one clause, each with a line number")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
