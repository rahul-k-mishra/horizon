# GVGAI files vendored for HORIZON

These files are copied unchanged from the General Video Game AI framework, https://github.com/GAIGResearch/GVGAI, at commit e58ff6597319155218759cc178931e05b81b524c. They are distributed under the GNU General Public License, version 3 or later; see LICENSE.txt in this folder.

What is here, and why:
- examples/gridphysics/: the VGDL descriptions and level files of the grid-physics games, read by scripts/vgdl_scan.py and scripts/truth_vgdl.py, and played by the engine;
- examples/all_games_sp.csv and the other game lists: the framework's lists of games;
- src/: the whole Java source of the engine (vendored on 14 November 2026; before that only src/ontology was here). scripts/automation/sim_gvgai.py compiles it with javac from a pinned Temurin JDK and runs it through JPype; docs/design/ENGINE.md gives the reasons.

Each file under src/ has the git blob hash of the same file at the upstream commit; .gitattributes keeps git from rewriting line endings here. The files under examples/ were committed with their line endings changed; their content is otherwise the same as upstream (logs/engine_inventory.log). This README is HORIZON's own note, not the upstream README.

Not vendored, because nothing in the study uses them: the sprite images (sprites/), the clients, the documentation, the two-player and continuous-physics games, and the bundled gson-2.6.2.jar (the gson source is under src/tools/com/google/gson).
