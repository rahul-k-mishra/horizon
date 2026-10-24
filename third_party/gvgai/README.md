# GVGAI files vendored for HORIZON

These files are copied unchanged from the General Video Game AI framework, https://github.com/GAIGResearch/GVGAI, at commit e58ff6597319155218759cc178931e05b81b524c. They are distributed under the GNU General Public License, version 3 or later; see LICENSE.txt in this folder.

What is here, and why:
- examples/gridphysics/: the VGDL descriptions and level files of the grid-physics games, read by scripts/vgdl_scan.py and, once written, by the truth-table generator;
- examples/all_games_sp.csv and the other game lists: the framework's lists of games;
- src/ontology/: the Java sources of the sprite classes, effects and physics, cited by docs/DESIGN.md for the determinism rule and the truth predicates.

Nothing in this folder is run by this repository. The study compiles GVGAI from the same commit on Kaggle.
