# DESIGN_gvgai_draft.md: the GVGAI frame contract and the search state, as built (draft, not adopted)

Written 14 November 2026, beside docs/DESIGN.md, because parts of it change what docs/PREREG.md (draft v0) and docs/DESIGN.md now say. Nothing here is registered or adopted. Each point the author must decide is marked **For the author**. The engine decision and its evidence are in docs/design/ENGINE.md.

## 1. The frame contract as built

This is how a GVGAI level is presented to study 1's frame-only agents. The code is scripts/automation/agents_gvgai.py, tested by scripts/automation/test_agents_gvgai.py (logs/test_agents_gvgai.log). It follows what study 1 did for MiniGrid (study 1, scripts/adapter_minigrid.py and scripts/env_frame.py at its tag prereg-v1.1): an adapter with study 1's contract, a key map, and the agents called as study 1's runner called them. Study 1's code itself is not edited.

- **Engine.** GVGAI's own forward model at commit e58ff6597319155218759cc178931e05b81b524c, through JPype (docs/design/ENGINE.md). Reset and restart copy the level start. A step is GVGAI's StateObservation.advance on the current state, the same transition the search uses.
- **Grid.** One cell per level cell. For each cell, the set of sprite types drawn in it. A sprite is drawn unless its hidden or invisible flag is set (GVGAI keeps both as text, first value for player 0). A sprite counts in the cell that holds its top-left corner.
- **Indices.** A cell's index belongs to its set of types, given in order of first appearance within the run, row by row, starting at 1. The empty set is a set like any other. Index 0 is the canvas padding. There is no cap. GVGAI gives the avatar one type whatever its facing, so its orientations share one index, as study 1 merged MiniGrid's four. An avatar subtype (a coat, a key held) is a different type and gets its own index, as an agent tile over an open door did in MiniGrid. Two types drawn with the same image get different indices; this is the known limit already in docs/PREREG.md, Section 3.
- **Canvas.** The grid goes at rows 1 onward and columns 0 onward of the 64 × 64 canvas, with padding 0 (study 1's env_frame.to_canvas). The frozen code reads rows 1 to 62 only (study 1, scripts/g_motion.py:30-31).
- **Actions and key map.** The adapter's actions are the avatar's available actions without ACTION_NIL, in GVGAI's order, labelled left, right, down, up and use. The key map from the ids the frozen code presses is 1 up, 2 down, 3 left, 4 right, 5 use. Id 7 has no GVGAI action and is not offered. This is study 1's macro map for MiniGrid (1 north, 2 south, 3 west, 4 east), with use in the place of pickup. I1 presses ids 1 to 5 only, as in study 1. The key map is added at run time to study 1's env_frame.KEY_MAPS under ("gvgai", "frame"), so env_frame.py is not edited.
- **Level end and game end.** level_end: the game reports a win. The next episode then begins at once on the same level, and its first frame is returned (study 1's semantics: a won level is followed by the next). game_end: the game reports a loss, or GVGAI's own limit of 2,000 game ticks ends it. The final frame is returned, and the next step or restart begins a new episode on the same level.
- **Seeds.** 1000 to 1009 seed the agent only; the games are deterministic.
- **Agents.** N is study 1's g_nav.play (mode nav) and R is g_agent.play (mode hash_state), each with Config(max_actions=budget, seed=s, **MODES[mode]). I1 is i1_suite_adapter.play through the unchanged e1_rudakov_adapter.py. Rand is numpy default_rng(seed) over the adapter's actions. Study 1's files are under third_party/study1, byte-identical to its tag prereg-v1.1 (Section 4).
- **Rows.** One row per (agent, game, level, seed), schema horizon.agent.v2: horizon.agent.v1 plus the field "level". This is the kind gvgaiagent, run on a worker pool in which a seed starts only if its wall-clock cap fits before the session's deadline.

**What it changes.** docs/PREREG.md, Section 3, and docs/DESIGN.md, Section 6, say "one cell per level cell", "the avatar's orientations are one index" and "the next episode starts on the same level"; the code does that. They do not name the key map, the canvas placement or the agent row schema; these are new. PREREG Section 9 names horizon.agent.v1 for agent rows; the GVGAI rows need v2, which carries the level (docs/STATE.md, amendment y, point 4).

## 2. A confirmatory game that does not fit the canvas

**garbagecollector** has levels of 25 rows by 69 columns (all five levels; checked by scripts/automation/test_agents_gvgai.py, part 4, on level 0). One cell per level cell cannot fit 64 columns. The adapter refuses such a level rather than crop it silently.

**For the author.** The options:
1. Drop garbagecollector from the confirmatory suite by a rule stated before the tag: a level must fit 62 rows by 64 columns at one cell per cell. That leaves 25 games and 125 levels; the void rule needs 20 games. S_M of garbagecollector must be read from docs/truth/gvgai.json to see what the change does to the spread of S_M.
2. Show a 64-column window that follows the avatar. The frame then shifts as a whole when the window moves, which study 1's motion detector reads as many changed cells; that is not "the same terms" as MiniGrid.
3. Crop a fixed 64 columns. Part of each level would be invisible to the agents but not to the search.

Recommendation: option 1, because it is a rule about the presentation fixed before any run, and it changes neither the agents nor the measure. garbagecollector is also the slowest level in logs/engine_speed.log.

## 3. The search state: the registered key leaves out counters GVGAI keeps

docs/PREREG.md, Section 6, defines the state as: for every sprite its type, cell, orientation and resources; the avatar's health points; and the game tick only where the description is timed. The search job implements exactly that key as its default ("registered"). Check 2 of scripts/engine_semantics.py runs a breadth-first search on the pilot levels. At each merge of two paths under one key, it compares the two states' successors. Under the registered key, 47 of 9,507 merges have different successors, all in rivers; the others are none. Under the "extended" key, 0 of 9,507 do (logs/engine_semantics.log). The extended key adds what GVGAI keeps per sprite that changes over time: the age of a Flicker (and of OrientedFlicker and Spreader), the counter and first tick of a SpawnPoint, the health points of every sprite, and the ticks since the last move of a sprite whose cooldown exceeds 1. A search under the registered key therefore merges states of rivers that are not the same state. It can miss states, and it can miss the shortest win.

scripts/engine_subset.py lists, per game, what the registered key leaves out (logs/engine_subset.log, last section). Of the pilot games, rivers is affected. Of the 26 confirmatory games, seven are: glow, grow, islands, lasers, painter, roadfighter and zenpuzzle.

Separately, the position in the key is the sprite's position in pixels, not its cell. For a sprite on the grid the two are the same thing. For a sprite between cells (a speed other than 1), the cell would merge different states.

**For the author.** Whether docs/PREREG.md, Section 6, adopts the extended key before the tag; and whether the pilot search runs under it. The job takes key_form "registered" or "extended" as a parameter of the kind; jobs/pilot_search/manifest.json has "registered", as Section 6 now reads. Recommendation: adopt the extended key, with "position in pixels" in place of "cell". The registered wording assumes the listed fields are the whole dynamic state, and the check shows they are not. Doing so before any confirmatory search changes no result.

## 4. The agents, frozen

Copied from study 1's tag prereg-v1.1, byte for byte, into third_party/study1 (third_party/ is vendored code, which scripts/check_no_aid.py reports apart). Blob hashes, as registered by study 1 and checked by agents_gvgai.check_frozen before every run:

| file | blob |
|---|---|
| scripts/g_agent.py | 72585a4dbb926d4512ff9596f58118a176bb0646 |
| scripts/g_nav.py | a8a7eb61e62a658c239b98e0224e3588a662d1a0 |
| scripts/g_motion.py | 14018512a5c6b0efc81aed61c5466654d338be0b |
| scripts/g_control_probe.py | d5ff2a4dc77b9e1148929e7db03fe99a9d2b0bf8 |
| scripts/g_nav_run.py | 2cc0146a697e525e5873d4e29cb80f4ae8bd6297 |
| scripts/g_census_table.py | 488feaca9c10985c4d0ff62791ceb4fa6fa6b9a8 |
| scripts/env_frame.py | bb3ff60acf88c220ec64e287c6c1d6bb899f879b |
| scripts/e1_rudakov_adapter.py | 39ab52f82f2fef3460ce83cb9db30d892b571d5b |
| scripts/i1_suite_adapter.py | 9d8a18548b958e70b1365b2eacb25d25f83284ba |

I1's own code is under third_party/study1/external/rudakov_just_explore: the six files its adapter loads, with LICENSE (MIT, the upstream notice kept) and PROVENANCE.md, whose sha256 lines the test checks. agents/swarm.py, listed there, is not loaded by the adapter and is not copied. The copy check of PREREG Section 2 (the same actions and row fields as study 1's committed rows on a sample of MiniGrid games) is not yet made: it needs study 1's MiniGrid adapter and a run, by the author or the loop.

## 5. The ceiling and a measure that ties

**For the author.** Under PREREG Section 7.4 as drafted, a level whose search sees no win among the first C states is censored ("beyond C"), and the share of such levels "is not a reason to void". If every confirmatory level, or nearly every one, lies beyond C, then L_C ties on all or nearly all pairs. AUROC_L is then 0.5 or near it, the verdict is "not shown", and the outcome is Refute, not Void. scripts/test_analyze_horizon.py, part 4, records this: with every level beyond C, AUROC_L is 0.5000, nothing is void, and the outcome is Refute. A Refute from a measure that could not rank anything would be read as evidence against the claim when it is not. A void rule for it would mirror the rule already registered for S_M ("fewer than two values ... each held by at least 10% of the levels"). For example: "L_C is void if fewer than 10% of the confirmatory levels show a win within C." This is not adopted, and the analysis script does not apply it. The pilot search (Section 8) is what tells the author how close the suite is to that case.
