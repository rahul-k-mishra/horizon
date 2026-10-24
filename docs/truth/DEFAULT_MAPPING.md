# The default level mapping: eggomania's A1, settled

Written 25 October 2026. It settles a generator error found while building the hand-check tool. Nothing registered changes: A1's wording is the same and the deterministic suite is the same.

## What was found

The level files of eggomania place the avatar with the character A (third_party/gvgai/examples/gridphysics/eggomania_lvl0.txt, line 13), but the LevelMapping of third_party/gvgai/examples/gridphysics/eggomania.txt (lines 34 to 39) has no line for A, and none for w. scripts/truth_vgdl.py read only the LevelMapping, so it found no avatar in any of eggomania's five levels and failed A1 there.

## What GVGAI does

The framework supplies a meaning for both characters when a description leaves them out. The files are under src/core, which is not vendored here (third_party/gvgai/README.md lists src/ontology only). They were read at the vendored commit, https://github.com/GAIGResearch/GVGAI/tree/e58ff6597319155218759cc178931e05b81b524c:

- src/core/game/BasicGame.java, lines 51 to 56, in the constructor of every BasicGame: w is mapped to wall and A to avatar ("Add here whatever mappings are common for all BasicGames").
- src/core/vgdl/VGDLParser.java, lines 601 to 606: each LevelMapping line is put into the same map, so a description that names w or A replaces the default and one that does not keeps it.
- src/core/game/Game.java, lines 359 to 367: the two sprites have default definitions, wall as Immovable and avatar as MovingAvatar, which a SpriteSet entry of the same name replaces.

So the A1 failure on eggomania was wrong: the level does place an avatar, of eggomania's own avatar class FlakAvatar (eggomania.txt, line 15).

## The fix and what it changed

scripts/truth_vgdl.py now adds the two default characters and the two default sprites wherever a description does not name them. scripts/test_truth_vgdl.py has a new synthetic game, nomap, with no mapping line for w or A; it passes with the fix and fails without it (logs/test_truth_vgdl.log). The generator was rerun (logs/truth_vgdl.log), and scripts/truth_diff.py compares the new docs/truth/gvgai.json with the one at commit b0091c7 (logs/truth_diff.log):

- **Verdicts changed:** eggomania, A1, fails to holds on all five levels. That is the only change. eggomania is not deterministic, so it is outside the suite.
- **Clauses changed with the same verdict:** eggomania's A2 no longer cites "the level places 0 avatar sprites" and still fails because FlakAvatar's use action creates a sprite. In chopper, circuit and islands, wall is used in the InteractionSet and placed by w but has no SpriteSet entry. A4 now lists wall as an Immovable blocker, and its verdict stays the same. islands is deterministic.
- **The deterministic suite** stays the same 30 games (logs/truth_diff.log). The determinism rule of scripts/vgdl_scan.py reads the sprite classes and interactions only, never the LevelMapping, so the pilot draw of scripts/draw_pilot.py, which reads docs/design/vgdl_scan.json, is unchanged as well: bait, labyrinthdual, rivers, watergame.
- **The hand check:** scripts/draw_handcheck.py was rerun and draws the same 10 games, with docs/truth/HANDCHECK.md byte for byte the same. docs/truth/handcheck_rows.json was written again because it records the hash of docs/truth/gvgai.json. Its 100 rows are unchanged (logs/handcheck_rows.log). No answers existed.

scripts/vgdl_scan.py, the simplified eligibility scan, has the same omission in its own reading of A1 to A5 (docs/design/vgdl_scan.json). It was left as it is because only its determinism rule is used, and that rule does not read the mapping.
