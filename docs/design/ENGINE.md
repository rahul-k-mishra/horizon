# ENGINE.md: what steps a GVGAI game for HORIZON

Written 14 November 2026, before anything of the GVGAI build was relied on (Part A of the build). It answers one question: can a GVGAI game be stepped from Python, on Kaggle CPU, fast enough for a breadth-first search of up to 2,000,000 states inside a session, with the same rules the truth tables were read from? Nothing here is registered. Every number names the committed log of the script that printed it.

## 1. What was vendored, and what had to be obtained

Before this session, third_party/gvgai held the VGDL descriptions and level files (examples/gridphysics, 716 files), the game lists, and src/ontology (114 Java files: sprite classes, effects, physics, Types). It did not hold the engine itself. Missing were src/core (the game loop, the forward model, the parser, the registry, the terminations: 55 files), src/tools (90, the bundled JSON library among them), src/tracks (90) and src/testing (2). In all, 238 of the 352 files under src/ were missing. Without them no game can run (logs/engine_inventory.log).

What was obtained:
- the rest of src/ at the pinned commit. All 352 files under src/ are now vendored, each with the git blob hash of the same file upstream (logs/engine_inventory.log). The 137 example files vendored earlier differ from upstream in line endings only; their content is the same. The sprite images, clients, documentation and the bundled gson jar are not needed and not vendored;
- a JDK: Temurin 21.0.13+9, pinned by sha256 for Linux and Windows from the Adoptium record (logs/engine_evidence.log). scripts/automation/sim_gvgai.py downloads it into a cache folder and checks the hash;
- JPype1 1.7.1 from PyPI, with wheels for CPython 3.11 and 3.13 on Linux x86_64 (logs/engine_evidence.log), so the Kaggle image's Python 3.13 can load it.

The whole source compiles with javac from that JDK.

## 2. What can run the games

From the PyPI and GitHub records fetched by scripts/engine_evidence.py (logs/engine_evidence.log; the records kept are in docs/design/engine_evidence.json):

| candidate | how it steps a game | rules | licence | last change | on PyPI | games of the suite it carries |
|---|---|---|---|---|---|---|
| GVGAI's Java through JPype, in-process | the original engine's forward model, StateObservation.copy and advance | GVGAI's own | GVGAI GPL-3.0 (its LICENSE.txt; GitHub reports NOASSERTION); JPype Apache-2.0 | GVGAI last push 2022-04-23; JPype 1.7.1 uploaded 2026-05-06 | JPype1 yes; GVGAI no (vendored) | all 30 |
| GVGAI's Java through Py4J, in a separate JVM | the same engine over a socket | GVGAI's own | Py4J BSD | py4j 0.10.9.9, January 2025 | py4j yes | all 30 |
| GVGAI's own Python client, and the GVGAI gym wrapper (rubenrtorrado/GVGAI_GYM) | the Java game loop over a socket; the client sends actions and receives observations | GVGAI's own | GVGAI GPL-3.0; the wrapper Apache-2.0 | wrapper last push 2020-01-22 | no | all 30 |
| py-vgdl (schaul, the original; rubenvereecken, the Python 3 fork) | a Python reimplementation of VGDL | its own | BSD-3-Clause | 2019-06-23; 2022-10-04 | no | 1 of 30 (sokoban) |
| tsividis/vgdl | a Python reimplementation | its own | BSD-3-Clause | 2026-04-20 | no | 1 of 30 (sokoban) |
| VGDLx (shepardxia) | a JAX reimplementation | its own | none stated | 2026-03-20 | no | 30 of 30 named by a file |
| Griddly | a C++ engine for its own GDY format, with ports of some GVGAI games | its own | MIT | PyPI 1.6.7, March 2023, no CPython 3.13 wheel | yes | 6 of 30 |
| an interpreter written here | Python, for the subset the 30 games use | written here | ours | not written | no | all 30, if written |

Notes on the table:
- The socket clients cannot serve the search. In both, every line of their Python code that calls copy( or advance( copies an array or a timer, not a game state (logs/engine_evidence.log). They play the game loop forward; they cannot copy a state or step a copy.
- VGDLx's README says "67/68 supported GVGAI games match exactly over 40-step validation trajectories". That is its own claim, not checked here, and it states no licence, so it cannot be used.
- The subset an interpreter written here would have to cover is counted by scripts/engine_subset.py (logs/engine_subset.log): 13 sprite classes, 19 interaction effects, 4 termination classes, 22 sprite parameters, 11 effect parameters, 5 termination parameters and 2 game parameters. GVGAI implements these in 1,295 + 1,083 + 300 lines of Java for the classes, effects and terminations, and 8,009 lines in the core files an interpreter would also have to match (game loop, forward model, sprite base class, parser, physics): 10,687 lines in all.

## 3. The semantics question

The truth tables were read from the GVGAI source, and the hand check checks them against it. The engine that runs the search and the agents must have those rules, or the answer key and the measure are different constructs, which is how study 1 failed.

- **GVGAI's Java through JPype (or Py4J).** The engine is the source the truth tables were read from, at the same commit, byte for byte (Section 1). There is no second implementation whose agreement must be shown. Three things remain, and each was checked on the 20 pilot levels by scripts/engine_semantics.py (logs/engine_semantics.log):
  1. *The forward model against the game loop.* The search and the agents step a level through GVGAI's forward model, which is separate code from GVGAI's game loop (Game.runGame). 1,000 seeded random sequences of 200 actions were played both ways. All 1,000 agree at every one of 115,653 decisions compared before a game ended. In the 555 sequences that ended the game, the final states agree. The final tick is one higher in the forward model, because the game loop counts a tick when a cycle starts and the forward model when an advance ends. That is bookkeeping after the last move, and it changes no state that is expanded.
  2. *Whether the state key holds everything the next step depends on.* A breadth-first search merges states with equal keys. At every merge of two paths on the pilot levels, up to 500 per level, both states were stepped by every action and their successors compared. Under the key registered in docs/PREREG.md, Section 6, 47 of 9,507 merges have different successors, all on rivers. Under the "extended" key, which adds the counters GVGAI keeps per sprite (a Flicker's age, a SpawnPoint's counter and first tick, every sprite's health, the ticks since a slow sprite last moved), 0 of 9,507 do. The registered key is therefore not sufficient for rivers. By the static count of logs/engine_subset.log, it is not sufficient for seven confirmatory games either. This is set out for the author in docs/DESIGN_gvgai_draft.md, Section 3.
  3. *Determinism.* Each sequence replayed twice through the forward model gives identical keys: 1,000 of 1,000.
  What remains unverified: the forward model on the confirmatory levels themselves, which were not played in this session; and GVGAI's own limit of 2,000 game ticks, a compile-time constant that cannot be lifted without editing the source. A state at that limit is a loss in GVGAI. A breadth-first search reaches it only if a level's search goes 2,000 actions deep, which each row's depth_max shows.
- **Py4J.** The same engine, so the same answer, at a socket's cost per call.
- **The socket clients.** The same engine, but they cannot copy a state (Section 2).
- **py-vgdl, tsividis/vgdl, VGDLx, Griddly.** Each is its own implementation. Agreement with the Java could be shown only by running the same levels under both and comparing states, which needs the Java engine running anyway. Until then, all of their rules would remain unverified. Four of them do not carry the games. VGDLx states no licence.
- **An interpreter written here.** About 10,700 lines of Java behaviour to match (Section 2). Its agreement could be shown the same way as above, against the Java engine, but that again needs the Java engine running, which is the first candidate.

## 4. Speed

scripts/engine_speed.py measures the code the search job runs (sim_gvgai.py and the bridge) on every one of the 150 levels of the 30 games, on this laptop (logs/engine_speed.log). It walks each level with seeded random actions and times the search's expansion: the state's key, plus a copy, GVGAI's advance and the successor's key for every action. It does not search, so it records no state count, win or solution length of any level. A breadth-first search to S states expands at most S states, so S divided by expansions per second bounds its time from above.

On the smallest confirmatory level 0 by key size, painter level 0, the engine makes 4,274 expansions per second, so a search of 2,000,000 states takes at most 468 s. Over the 130 confirmatory levels the median is 1,026 expansions per second, the fastest 5,265, and the slowest 94 (garbagecollector level 1). Garbagecollector's five levels, with keys of 90,316 bytes, are the only levels whose bound reaches the registered time cap of 14,400 s. There the time cap, not the ceiling, would stop the search. Summed over the 130 levels, each bound capped at 14,400 s, the search needs at most 372,346 worker-seconds: 3.23 sessions of 4 workers × 28,800 s, so at least 4 sessions if packed perfectly. The registered budget charges every unit its whole time cap and allows 17 chunks (logs/design_budget.log). The 20 pilot levels need at most 63,163 worker-seconds, 0.55 of a session. In the state key, 19 of the 30 games hold the tick (logs/engine_speed.log).

These are the laptop's figures: an Intel processor with 8 logical CPUs, under Windows, with OpenJDK 21.0.13 and JPype 1.7.1. Kaggle's CPU is not measured. The laptop's figures also vary between runs of the script: an earlier run before the bridge's last change gave other values, and only this run's log is kept. The memory a search needs is its visited set and frontier in Python and one JVM of at most 2 GiB per worker, within the registered 6 GiB per worker.

## 5. Recommendation

**GVGAI's own Java engine, compiled from the vendored source at the pinned commit with a pinned Temurin JDK, called in-process through JPype**, as docs/PREREG.md, Section 3, already names; Python 3.13 on the Kaggle image, for which JPype1 1.7.1 has a wheel. It is the only candidate that runs all 30 games, can copy and step a state, and has the rules of the source the truth tables come from by construction. Its two separate code paths agree on the pilot levels. Its speed fits the budget with a wide margin on this laptop. It was built in this session (docs/DESIGN_gvgai_draft.md), behind the condition of the build prompt that the route be verifiable and fast enough.

What would make it wrong:
- *Kaggle.* None of this has run on Kaggle. The JDK download, JPype on CPython 3.13, the memory of four JVMs and the session's speed are untested there. The dry run of the kind (rule R8) and the pilot search are the test.
- *Speed on Kaggle* well below the laptop's. The time cap then decides more levels than the ceiling does, and garbagecollector is closest to it.
- *The state key.* Under the registered key a search merges states that differ (Section 3, check 2). If the author keeps the registered key, the search measures a slightly different graph from GVGAI's on rivers and possibly on seven confirmatory games.
- *The canvas.* garbagecollector's levels are 69 columns wide and do not fit the 64-column frame (docs/DESIGN_gvgai_draft.md, Section 2).
- *The confirmatory levels.* The forward model was checked against the game loop on the pilot levels only.
