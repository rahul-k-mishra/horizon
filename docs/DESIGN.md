# HORIZON: the study design

Written 24 October 2026; the author's five decisions of the same day are written in as registered values (Sections 2.1, 3.3, 4, 7 and 12), each with its reason. Status: a design; nothing in it is registered until the tag; the registration is docs/PREREG.md, draft v0, which binds only when the author tags it. Paragraphs that report something read from data or descriptions are marked *exploratory*; everything else is a design choice. Every number here is either a chosen value (docs/design/params_v0.json and the text below) or printed by a committed script whose console is committed: scripts/suite_evidence.py (logs/suite_evidence.log), scripts/vgdl_scan.py (logs/vgdl_scan.log), scripts/design_budget.py (logs/design_budget.log), and the oracle scripts of Phase 1 (logs/oracle_v2.log, logs/oracle_sat.log).

## 1. The question to register

For a frame-only agent that carries built-in assumptions about how games work, what decides whether it completes the first level of a game it has not seen?

- **H1, mechanics match:** it completes the level where the game's true mechanics agree with its assumptions A1 to A5 (docs/PROJECT_BRIEF.md, Section 2).
- **H2, search size:** it completes the level where the search the level presents is small, whatever the mechanics.

The registered test is a contrast: per agent, does a pre-run measure of search size rank the levels by completion better than the mechanics vector does, worse, or neither?

*Exploratory, and the reason for this shape.* The oracle test gave the mechanics vector its best case, exact truth in place of a census, and it ranked first-level completion on MiniGrid/BabyAI at AUROC 0.55 to 0.70, with nothing out of sample; grid area alone ranked the same games better on five of the six primary lines (docs/oracle/READING.md, Sections 2 to 4). The same reading said H1 had not had a fair test, because on MiniGrid/BabyAI its vector barely varied (Section 5 there). So the study is built around H2, with H1 as the rival, and on a suite where the mechanics vector does vary (Section 3).

## 2. The development set

The 175 games of study 1 (161 MiniGrid/BabyAI games and 14 Procgen games), with their truth tables and their 10,080 confirmatory rows, are development data from now on (docs/oracle/READING.md, Section 1). They are used for three things, all exploratory:
- to port and check the agents (Section 6): the ported N, R and I1 must reproduce their study-1 rows on a sample of study-1 games before any GVGAI run;
- to run stage D, the development search (Section 2.1), on a simulator that clones states: MiniGrid environments can be copied whole with copy.deepcopy, so the search quantities of Section 5 can be computed on study 1's MiniGrid/BabyAI levels;
- to read, before registration, how the search quantities rank study 1's outcomes against the oracle vector. That reading is exploratory and can change no registered value except by the rules of docs/PREREG.md.

No study-1 game is a confirmatory game.

### 2.1 Stage D: the development search (Decision 4, 24 October 2026)

**Decided:** the development search runs before the tag, on study 1's MiniGrid/BabyAI games, as development data. *Reason (the author's):* the registered claim should be written knowing whether the search quantities rank completion at all on data where the outcomes already exist.

- **What runs.** The search job of Section 5 with the same quantities, R, L, b and EH (where its limits allow), on study 1's confirmatory MiniGrid/BabyAI games in the macro condition, the condition study 1 tested. Its outcomes are study 1's committed rows, which this repository reads (through study 1's own parsers, as scripts/oracle_v2.py does) and never writes.
- **The unit is (game, seed).** Study 1 reset each environment once with its seed, so each seed is a different layout (study 1, docs/PREREG.md v1, Section 3.2). The search runs on the layout that reset(seed) produces, for seeds 1000 to 1009, and is matched to that seed's row. Games whose sprites move at random (Dynamic-Obstacles; study 1, docs/PREREG.md v1, Section 7) are excluded, because their search is not defined. Study 1 started a new, unseeded layout after an episode that ended without success, so a row's completion can come from a later layout than the one searched; this is a known limit of the stage.
- **Its own manifest kind.** Stage D runs through the loop as the kind devsearch, campaign dev-minigrid, with its own chunks (Section 10): rows of the search schema horizon.search.v1 with suite "minigrid", game the environment id and level the seed, under runs/dev-minigrid/search/. A devsearch chunk never holds a confirmatory unit, and no confirmatory analysis reads these rows.
- **What it is for.** An exploratory reading of the contrast on development data, and the input of the smallest detectable difference (Section 7.1). It may not be used as evidence for the registered claim. Under macro the MiniGrid/BabyAI truth vector takes two values (docs/oracle/READING.md, Section 5), so stage D says much more about the search quantities than about H1.
- **If the search quantities do not predict completion there**, the author decides before the tag whether the registered claim is weakened. This design does not decide it in advance.

## 3. The confirmatory suite: what was weighed

The suite must have mechanics written as declarative descriptions, so that truth tables come from the description and not from reading code, and a simulator whose state can be copied, so that search quantities can be computed. Four candidates were weighed on 24 October 2026. The evidence is the packages' own release records on PyPI and their source repositories at the tags and commits named, fetched and saved by scripts/suite_evidence.py (logs/suite_evidence.log, raw records docs/design/suite_evidence.json), and the scan of Section 3.2.

| candidate | descriptions | state copy | runs on Kaggle CPU | games | verdict |
|---|---|---|---|---|---|
| Griddly | GDY files (YAML): actions, collision behaviours and win/lose conditions are declared (resources/games/Single-Player/GVGAI/labyrinth.yaml at tag 1.6.6) | yes: GymWrapper.clone() and get_state() (python/griddly/GymWrapper.py:532 and 269 at tag 1.6.6) | PyPI release 1.6.7, March 2023, with a CPython 3.11 Linux wheel; C++ engine; built before numpy 2, so numpy must be pinned below 2 | 17 distinct single-player games at tag 1.6.6, 13 of them under its GVGAI folder and 4 under Mini-Grid | **not used as a suite**: too few games, most of them copies of games in the other candidates or in the development set |
| py-vgdl | VGDL text | the Python 3 fork (rubenvereecken/py-vgdl) has state get/set; the original (schaul/py-vgdl) is Python 2 | not on PyPI under vgdl or py-vgdl; last push October 2022 (fork) and June 2019 (original); implements part of VGDL | 9 games in the fork | **not used**: few games, unmaintained, and the same descriptions run under GVGAI, the reference implementation |
| GVGAI framework | VGDL text (examples/gridphysics) | yes: StateObservation.copy() and advance() (src/core/game/StateObservation.java:55 and 70) | Java, GPL-3.0; no build tool: 347 Java source files and a bundled JSON library, compiled with javac; reachable from Python in-process through JPype (PyPI JPype1 1.7.1 has a CPython 3.11 Linux wheel); Kaggle's image is not known to ship a JDK, so the notebook downloads a pinned JDK (Section 11) | 122 single-player games listed, 110 grid-physics games with a level-0 file that parse, **30 deterministic** (Section 3.2) | **the confirmatory suite**, restricted to its deterministic grid-physics games |
| MinAtar | none: the mechanics are Python code | by copying the environment object | pure Python (PyPI MinAtar 1.0.15, May 2023, a wheel for every platform; GPL-3.0) | 5 games, with random enemies and no first level in the sense used here | **not used**: five games cannot carry a game-level test, and their randomness makes a search state ambiguous |

GVGAI is also where the audience of the Support venue, IEEE Transactions on Games, works.

### 3.1 Why only deterministic games

A GVGAI forward-model copy draws from a fresh, unseeded random generator (src/core/game/ForwardModel.java:452), and the generator's state is not part of the copied game state. In a game with a random element, the successor of a state under an action is therefore not a function of the state, and a breadth-first count of reachable states is not defined. The suite is restricted to games whose descriptions contain no random element, by the rule written out in scripts/vgdl_scan.py (the classes and effects that draw from the generator, read from the ontology source vendored under third_party/gvgai/src/ontology). GVGAI's own flag is_stochastic is not used: it misses teleportToExit, attractGaze and transformToRandomChild, which draw from the generator without setting it.

### 3.2 The scan of the descriptions

*Exploratory.* scripts/vgdl_scan.py read the VGDL descriptions of GVGAI commit e58ff6597319155218759cc178931e05b81b524c, vendored under third_party/gvgai with its licence. Of the 122 single-player games listed, 12 are not grid physics; 110 grid-physics games have a level-0 file and parse; 30 of them are deterministic by the rule. The commonest causes of randomness are RandomNPC (22 games), SpawnPoint (20), Chaser (17) and attractGaze (17). Each of the 30 deterministic games has 5 level files, 150 in all (logs/vgdl_scan.log).

*Exploratory.* The scan also gives a first reading of A1 to A5 from each description, by simplified rules that are not the registered truth tables (Section 4). On the 30 deterministic games it reads A1 as holding on all 30, A2 on 10, A3 on 22, A4 on 25 and A5 on 13; the score S, the number of A1 to A5 holding, takes every value from 1 to 5 (1, 6, 9, 10 and 4 games), in 11 distinct patterns (logs/vgdl_scan.log). If the registered truth tables vary as much, the mechanics vector varies here far more than on MiniGrid/BabyAI, where A1 to A3 were constant and S took two values per condition (docs/oracle/READING.md, Section 5). This is what makes the suite a fair test of H1.

### 3.3 The unit: a level, with games as clusters

The agents of this study keep nothing between runs: every run starts from nothing on the level it is given. A run that starts on level 3 of a game therefore meets that level as its first level, exactly as a run on level 0 does. The unit of analysis is a (game, level) pair: 30 deterministic games times 5 levels. Levels of one game share their mechanics and most of their sprites, so they are not independent: every interval is computed by resampling games, each with all its levels (Section 7). Four games are drawn for the pilot and never enter a confirmatory analysis, leaving 26 games and 130 level units (logs/design_budget.log). Level 0 alone, one unit per game, is reported as a secondary analysis.

**Decided (Decision 1, 24 October 2026):** the unit of analysis is the level, with games as the bootstrap clusters. *Reason (the author's):* the agents keep nothing between runs, so every level is a first level, and the level unit gives the search quantities their full resolution.

**The mechanics score is constant within a game, so H1 is tested on 26 effective points whatever the level count; the level unit sharpens the search tests and not the mechanics test.** The 130 confirmatory levels are not 130 independent observations of the mechanics. *Exploratory, from the generator:* on the 30 deterministic games no game's A1 to A5 vector differs between its levels (logs/truth_vgdl.log), so the constancy is exact, not approximate.

A result where search size wins mainly by separating levels within games is still a result for H2, and the secondary game-level analysis shows whether it holds between games as well. docs/design/DECISION_REVIEW.md, Decision 1, sets out a further point on this for the author.

## 4. The mechanics vector

The five assumptions keep study 1's wording (study 1, docs/PREREG.md v1, Section 7, quoted in docs/PROJECT_BRIEF.md, Section 2), so that the predicates and the agent N's assumptions are the same constructs. For VGDL they are read from the description of the game and the layout of the level, by these registered predicates:

- **A1, input coupling.** Holds iff the avatar present at level start is of a class that responds to at least two actions: every avatar class except NullAvatar, which has only the null action, and MissileAvatar, which "has no actions available" (third_party/gvgai/src/ontology/avatar/oriented/MissileAvatar.java). Fails if no avatar is present.
- **A2, one controlled object.** Holds iff exactly one sprite's displacement is a function of the action: the avatar. It fails if the level does not place exactly one avatar sprite at start; if an interaction moves another sprite because the avatar moved into it (bounceForward, pullWithIt with the avatar as partner); and **if the avatar's use action creates a sprite** (ShootAvatar, FlakAvatar, ShootOnlyAvatar, AimedAvatar, OngoingShootAvatar). *Decided (Decision 2, 24 October 2026); reason:* the predicate says only the avatar's displacement depends on the action, and a shot is a sprite created by the action, so another object responds to the action. Study 1's census rule for A2 had no such clause (study 1, docs/PREREG.md v1, Section 5.3), and this is where it disagreed with the Procgen truth table: the census held A2 on six games where the truth fails it, in five of them because the agent fires or throws (bossfight, dodgeball, ninja, plunder, starpilot) and in the sixth, miner, because a push moves a boulder (study 1, docs/EXPLORATORY_V1_DIAGNOSIS.md, Tables 1 and 2; docs/GROUND_TRUTH_procgen.md).
- **A3, lattice motion.** Holds iff each movement action, when not blocked, shifts the avatar by one constant vector whatever its position, facing and history. It holds for MovingAvatar, HorizontalAvatar, VerticalAvatar and FlakAvatar at speed 1, and for OrientedAvatar and ShootAvatar only when the description sets rotateInPlace=False, because by default they turn in place when pressed in a new direction (third_party/gvgai/src/ontology/physics/GridPhysics.java:78-82). It fails for every avatar class with persistent or ongoing motion, for a speed other than 1, and wherever an interaction moves the avatar (teleportToExit, wrapAround, pullWithIt, bounceForward, windGust, slipForward, conveySprite, attractGaze).
- **A4, a fixed set of blockers.** Holds iff every move the avatar makes without effect is explained by a sprite that blocks it (stepBack or undoAll with the avatar), every blocking sprite type is of a class that never moves on its own (Immovable, Passive, Door, Resource, ResourcePack, and the stationary producers SpawnPoint, SpawnPointMultiSprite, Portal and SpriteProducer), and blocking sprites are created, removed or moved only through the avatar's own actions. An interaction counts as the avatar's own when the sprites it names are agent-driven: the avatar, the sprites its use action creates, and any stationary-class sprite that only those push or pull (a box that only the avatar pushes, whose arrival on a hole opens a door, as in doorkoban). A blocker that moves on its own, or that a producer, a spawn effect or a transform effect can create other than through the avatar, fails A4. A sprite that kills on contact does not block and does not affect A4. *Clarified 24 October 2026 while writing the generator:* the stationary producers and the agent-driven chain were not in the first draft; without them a laser cannon that never moves (lasers) and a door the avatar opens with a box (doorkoban) failed A4 against the construct's wording.
- **A5, a place goal.** Holds iff the level is won when the avatar enters a particular place, with no other condition at that moment: the only winning condition is a SpriteCounter with limit 0 on one sprite type, the level holds exactly one sprite of that type, and every interaction that removes it has the avatar (or an avatar subtype) as partner. A precondition met elsewhere (a key that turns the avatar into the subtype that may open the door) keeps A5 holding and is recorded. A win by collecting a set, defeating sprites, a timer or a count of several sprites fails A5.

**The generator.** scripts/truth_vgdl.py reads only the vendored descriptions and level files and writes docs/truth/gvgai.json: per (game, level), each predicate's verdict with every clause that decided it (file, line, text, and what was read). It plays nothing. Its synthetic tests, scripts/test_truth_vgdl.py, pass with warnings as errors. After the hand check it is the registered answer key. scripts/vgdl_scan.py is not the generator: its rules are simplified and it reads level 0 only; the generator imports only its determinism rule.

**The hand check.** Before the tag, the author checks the generator against the descriptions by hand on a sample drawn by a fixed seed: 10 of the 30 games, every predicate, on level 0 and one other level. scripts/draw_handcheck.py draws them with seed 20261025 (logs/draw_handcheck.log) and writes the sheet docs/truth/HANDCHECK.md. Every disagreement is resolved by reading the GVGAI source of the classes involved, fixes the generator, and is listed in the registration; the generator is then rerun on all games and a fresh sample of 5 games is checked, which must agree on every predicate.

## 5. The search quantities

**State.** A search state is the full dynamic content of the level: for every sprite, its type, cell, orientation and resources, together with the avatar's health points. The game tick is part of the state only where the description has a timed element (a Timeout termination, or a sprite with a cooldown, limit or total parameter); otherwise two moments with the same content are the same state. GVGAI's own limit on game ticks is not part of the search. States are identified by a 64-bit hash of a canonical serialization; a collision would merge two states, and none is checked for.

**Action set.** The avatar's available actions without the null action, the same list the agents use (Section 6).

**Level start, win and loss.** The level start is the state after the level file is loaded. A win state is one where the game reports a win; a loss state is one where it reports a loss. Win and loss states are counted and never expanded.

**The quantities, per (game, level):**
- **R, reachable-state count:** the number of distinct states reachable from the level start by any sequence of actions, counting win and loss states and not expanding them.
- **L, shortest solution length:** the smallest number of actions from the level start to a win state; infinite if the search is complete and reaches no win state.
- **b, branching:** over the states expanded, the mean number of distinct successor states other than the state itself.
- **EH, effective-horizon bound,** in the sense of Laidlaw, Russell and Dragan, "Bridging RL Theory and Practice with the Effective Horizon", NeurIPS 2023 (arXiv:2304.09853), on the deterministic MDP of the level: states as above, actions as above, reward 1 on the transition into a win state and 0 otherwise, win and loss states absorbing, horizon T = 400, exploration policy the uniform random policy over the action set. With Q¹ the random policy's Q-function and Q^(i+1) = QVI(Q^i), where QVI(Q)_t(s, a) = R_t(s, a) + max_a′ Q_(t+1)(f(s, a), a′), the MDP is k-QVI-solvable if every policy acting greedily on Q^k is optimal (their Definition 5.1). The effective horizon of their Definition 5.2 is H = min_k H_k with H_k = k + log_A m_k, where m_k is the smallest number of rollouts with which their algorithm GORP returns an optimal policy with probability at least 1/2; it is not computable exactly, so the registered quantity is the upper bound of their Theorem 5.4:

  EH_k = k + max over t ∈ [T], s ∈ S_t^opt, a ∈ A of log_A( Q^k_t(s, a) · V*_t(s) / Δ^k_t(s)² ) + log_A( 6 · ln(2 T A^k) ),

  where A is the number of actions, S_t^opt is the set of states some optimal policy visits at step t, V*_t is the optimal value, and Δ^k_t(s) = max_a Q^k_t(s, a) − max over a′ not in argmax_a Q^k_t(s, a) of Q^k_t(s, a′). Terms with Q^k_t(s, a) = 0 do not enter the maximum, and states where every action is in the argmax have no gap and do not enter it. EH = min over k ∈ {1, 2, 3} of EH_k over the k for which the MDP is k-QVI-solvable; infinite if it is k-QVI-solvable for none of them or if L > T. Optimality is checked exactly by dynamic programming: every greedy policy is optimal iff, at every (t, s) that some greedy policy reaches from the level start, every action in the argmax of Q^k_t(s, ·) has Q*_t(s, a) = V*_t(s). EH is computed only for levels whose search is complete with R ≤ 200,000 states, because the dynamic programme holds T × R values; for larger levels it is not computed and the level is excluded from the EH test.

**The primary search score** is −log10 R (smaller search, higher score). L, b and EH are secondary.

**The search job** is the search kind of docs/AUTOMATION.md, Sections 5 and 6: breadth first, one layer after another, with the frontier spilled to disk. A frontier entry is the action sequence from the level start; within a layer, entries are expanded in lexicographic order of their sequences, keeping a stack of state copies along the shared prefix, so that a level is replayed only from the nearest shared ancestor. The visited set holds the 64-bit hashes.

**Caps** (docs/AUTOMATION.md, Section 6; per (game, level), summed over sessions): node cap 5,000,000 states expanded; time cap 14,400 s; memory ceiling 6 GiB of resident memory per worker, four workers to a session; frontier spill at 1,000,000 entries.

**The capped-game rule** (decided here, registered in docs/PREREG.md, Section 7.4):
1. **Node-capped levels** contribute R = the node cap, ranked as the largest value and tied with every other node-capped level; L as infinite (ranked longest, tied) if no win state was reached, or as found if one was, since a breadth-first search finds the shortest solution before any longer one; b over the states expanded; EH as not computed.
2. **Time- or memory-capped levels** (stopped before the node cap) are excluded from every test of a quantity the cap left undecided: R and b always, L unless a win state was reached, EH always. They are listed with their partial counts.
3. **A search quantity is void for the suite** if more than 25% of the confirmatory levels are capped by any cap, or more than 10% are excluded under rule 2. For EH the 25% counts levels not computed for any reason.
4. Every analysis reports, next to its result, the number and share of capped levels by cap.

The node cap is chosen so that rule 1 loses nothing below it: a level's rank is exact among uncapped levels and correct, as a tie at the top, for every level with more reachable states than the cap.

## 6. The agents

- **N**, study 1's G-NAV planner (scripts/g_nav.py on scripts/g_agent.py, mode nav), the agent whose assumptions are A1 to A5. In study 1 it was only an instrument check, because the census was read from its own runs; here the mechanics come from the descriptions and the search quantities from the simulator, so neither measure is read from N's runs, and N is the primary agent.
- **R**, study 1's hash_state explorer (scripts/g_agent.py, mode hash_state).
- **I1**, the graph-based explorer of Rudakov, Shock and Cowley (arXiv:2512.24156, MIT licence), through study 1's adapter.
- **Rand**, uniform random actions from the action set, seeded. It assumes nothing and is reported as a reference, outside the outcome table.

The study-1 files are copied unchanged into this repository and frozen by blob hash; the copy is checked by rerunning a sample of study-1 rows on MiniGrid and comparing them field by field (Section 2).

**The frame contract** is study 1's (study 1, docs/PREREG.md v1, Section 3): reset(seed) gives a grid of integer colour indices; step(action) gives the grid, level_end and game_end; a fixed action list. For GVGAI, the grid has one cell per level cell. Each cell's index is given online, in order of first appearance, to the set of visible sprite types drawn in it; sprites marked hidden or invisible are not drawn and do not count; the avatar's orientations are merged into one index, as study 1 merged MiniGrid's. Two sprite types that GVGAI draws with the same image still get different indices; this is a known limit. level_end is a win. game_end is a loss or GVGAI's own tick limit, after which a new episode starts on the same level.

**Budget and outcome.** 20,000 actions per (agent, game, level, seed), seeds 1000 to 1009. **Y = 1** if the agent completed the level in at least 5 of its 10 seeds (study 1's convention).

## 7. The registered tests

Per evidence agent (N, R, I1), on the 130 confirmatory level units. The mechanics score is constant within a game, so H1 is tested on 26 effective points whatever the level count (Section 3.3).
- **AUROC_H** = the AUROC of the primary search score −log10 R for Y; **AUROC_M** = the AUROC of the mechanics score S_M, the number of A1 to A5 holding in the truth table, for Y. Both are fixed scores, not fitted models, so no cross-validation is needed. Ties count ½ (the Mann–Whitney statistic).
- **Δ = AUROC_H − AUROC_M**, with a paired, game-clustered bootstrap: 10,000 resamples of the 26 confirmatory games with replacement, each with all its levels, seed 20261024 in 8 chunks on a worker pool; resamples with one class only are skipped and counted; percentile interval.
- **Multiplicity:** the primary family is the three evidence agents. Each interval is a two-sided 98.33% interval (Bonferroni, 0.05 / 3).
- **Per agent:** *H2 over H1* if the lower end of Δ's interval is above 0 and AUROC_H ≥ 0.70; *H1 over H2* if the upper end is below 0 and AUROC_M ≥ 0.70; otherwise *neither*.
- **Void, per agent:** if the share of units with Y = 1 is outside [0.10, 0.90]; if the primary search score is void by the capped-game rule; or if the mechanics score cannot rank, that is, fewer than two values of S_M are each held by at least 10% of the units. A void agent is reported as void, not as any of the three verdicts.
- **Void, study:** if fewer than 20 confirmatory games remain after the pilot.

**Secondary, registered, outside the outcome table** (unadjusted 95% intervals, each labelled secondary): AUROC and Δ against S_M for L, b and EH; the same contrast at the game level (level 0 only, 26 units); per predicate A1 to A5, the AUROC of the predicate alone; grid area, action count and colour count (study 1's nuisance features); Rand on every line.

**The thresholds are registered (Decision 3, 24 October 2026):** the search AUROC floor of 0.70, the Bonferroni family of 98.33% over the three evidence agents, the completion void band of 10% to 90%, and the capped-level shares of 25% capped and 10% excluded (Section 5). They are arbitrary in the way all such thresholds are; their legitimacy comes from being fixed before any confirmatory run.

### 7.1 The smallest detectable difference (Decision 5, 24 October 2026)

**Decided:** before the tag, the smallest difference in AUROC between the search score and the mechanics score that this design can detect with 26 game clusters is computed from the development data and the registered interval, and registered. *Reason (the author's):* a Refute outcome must say how large a difference it rules out, not only that the data did not show one.

**Method** (scripts/sdd.py, console logs/sdd.log, numbers docs/design/sdd.json; synthetic tests scripts/test_sdd.py). On stage D's units (Section 2.1), for each evidence agent: 4,000 simulated studies, each drawing 26 development games with replacement, each game with all its units, and computing Δ on them; the standard error SE is the standard deviation of Δ over the simulated studies. The smallest detectable difference is (z(1 − α/2) + z(0.80)) × SE with α = 0.05 / 3, the registered family-wise level: the true difference at which an estimate with that SE clears zero at the registered level with probability 0.80. The registered number is the largest over N, R and I1, rounded up to two decimals. The script states, and does not correct, how the development data differ from the confirmatory suite: a development cluster holds 10 seed layouts of one environment, a confirmatory cluster 5 levels of one game; a development outcome is one seed's completion, a confirmatory outcome the majority of 10 seeds; and S_M takes two values on MiniGrid/BabyAI under macro.

**Status.** The script is written and tested; it waits on stage D's rows, which the loop has not yet produced. The number enters docs/PREREG.md, Section 7.8, before the tag.

**How a Refute outcome reads.** Under the registered number d, a Refute outcome reads "no difference of at least d between the search score and the mechanics score", not "the data could not tell".

**If d is so large that the study is uninformative,** the author decides before the tag whether to proceed, widen the suite, or change the claim. This design does not decide it in advance.

## 8. The pilot gate

Four of the 30 deterministic games are drawn for the pilot with seed 20261024 before the tag, listed in the registration, and excluded from every confirmatory analysis. The pilot runs after the tag of v1 and before any confirmatory unit.

| gate | passes if |
|---|---|
| G1, running | on every pilot level, the GVGAI adapter, the JDK and JPype run in a Kaggle session from a clean start; each of N, R, I1 and Rand plays 20,000 actions on 2 seeds without an error |
| G2, determinism | on every pilot level, 1,000 random action sequences of length 200, each replayed twice from the level start, give identical state hashes at every step |
| G3, cost | the registered agent unit cap, set by the rule "twice the longest pilot time for 20,000 actions, rounded up to a whole minute", is at most 1,800 s; and the search job on every pilot level either completes or stops at the node cap |
| G4, answer key | the hand check of Section 4 has passed |
| G5, the rival can rank | on the confirmatory levels, from the truth table alone (no run), at least two values of S_M are each held by at least 10% of the levels |

**Stop rule.** If any gate fails, no confirmatory unit runs. A failure of G1, G2 or G4 may be repaired once, by changing adapter, search or generator code only (never a threshold, a cap rule, a predicate or the game list), recorded in v1.1, with the pilot rerun on the same pilot games. A second failure of the same gate, or any failure of G3 or G5, stops the study: the outcome is VOID, reported in the repository and as a preprint on Zenodo. The pilot's values (the agent unit cap) enter v1.1 by the rule above, and v1.1 is tagged before any confirmatory unit runs.

## 9. The outcome table and venues

Fixed before any confirmatory run (project rule R5):

| outcome | condition | venue |
|---|---|---|
| **Support** | N is *H2 over H1*; at least one of R and I1 is *H2 over H1*; no evidence agent is *H1 over H2* | IEEE Transactions on Games; JAIR instead if all three evidence agents are *H2 over H1* (the broad result) |
| **Refute** | N is not void and the Support condition does not hold (N *neither*, N *H1 over H2*, or N *H2 over H1* without support from R or I1, or with an evidence agent *H1 over H2*) | the repository and a preprint on Zenodo |
| **Void** | N is void, the study is void (Section 7), or the pilot gate stopped the study (Section 8) | the repository and a preprint on Zenodo, reported as void |

Whatever the outcome, the report gives every agent's verdict, both AUROCs with their intervals, and the secondary analyses labelled as such. A Refute outcome is read against the registered smallest detectable difference d (Section 7.1): "no difference of at least d".

## 10. The Kaggle session and the compute budget

**The session limit is an assumption** (docs/AUTOMATION.md, Section 3). Kaggle's documentation page could not be read on 24 October 2026 (it returns only a script shell to a plain fetch), so the commonly stated 12-hour limit for CPU sessions was not verified, and the design is built to stay correct at 9 hours. The latest end of a session after the notebook starts is 900 s of start-up allowance + 28,800 s of work + one search batch of at most 60 s + 900 s of checkpoint reserve = 30,660 s (8 h 31 min): 1,740 s (29 min) inside a 9-hour limit, 12,540 s (3 h 29 min) inside 12 hours, and inside the 11 hours of project rule R4 (logs/design_budget.log).

**The budget** (logs/design_budget.log; upper bounds, since every unit is charged its whole cap, one session runs at a time, and each session is charged the loop's largest gap):

| stage | units | cap per unit | chunks at most |
|---|---|---|---|
| D, development search on MiniGrid/BabyAI macro, kind devsearch (exploratory; before the tag) | 1,610 (161 games × 10 seeds, at most) | 900 s | 13 |
| pilot search | 20 | 14,400 s | 3 |
| pilot agents (2 seeds) | 160 | 1,800 s | 3 |
| confirmatory search | 130 | 14,400 s | 17 |
| confirmatory agents | 5,200 | set by the pilot, at most 1,800 s | 14 at 300 s, 28 at 600 s, 55 at 1,200 s, 82 at 1,800 s |

All stages together: at most 50 chunks (18.8 days) if the pilot sets the agent cap at 300 s, and at most 118 chunks (44.3 days) at the largest cap G3 allows. Sessions run one after another; a second notebook would halve the days, and is not built.

## 11. What the automation needs before the study tag

These are code changes to the automation, made and tested with the dry-run machinery before the study's code tag; they change no registered value.
- **A worker pool in the runner** (project rule R4): four units at a time. The dry run's runner ran units one after another.
- **The study's software in the notebook:** a pinned Python 3.11 environment made with uv, numpy below 2 if Griddly is ever used, JPype1 1.7.1, and a pinned Temurin JDK downloaded by URL and checked by sha256, since the Kaggle image's Python and Java versions are not known (the dry run's rows record the image digest, not its versions).
- **The study's caps:** work_seconds 28,800, checkpoint reserve 900 s, platform_limit_seconds 32,400 in the study manifest, and the search memory ceiling of 6 GiB per worker (docs/AUTOMATION.md, Sections 3 and 6).
- **The consecutive-crash counter**, done on 24 October 2026 (docs/AUTOMATION.md, Section 7).
- **The kind devsearch** for stage D (Section 2.1): a third kind in the manifest, with rows of the search schema, whose job is the search of Section 5 on a MiniGrid layout copied with copy.deepcopy.

## 12. The author's decisions of 24 October 2026

The five items left open in the first draft were decided by the author on 24 October 2026 and are written above as registered values:
1. **The unit** is the level, with games as bootstrap clusters; the mechanics score is constant within a game, so H1 is tested on 26 effective points (Section 3.3).
2. **A2 fails for a shooting avatar**, because a shot is another object responding to the action (Section 4).
3. **The thresholds stand as drafted** and are registered (Section 7).
4. **Stage D runs before the tag** as development data, as its own kind with its own chunks (Section 2.1).
5. **The smallest detectable difference is registered** before the tag (Section 7.1).

Before the decisions were written in, a review of each, with its evidence, was written for the author: docs/design/DECISION_REVIEW.md. It changes nothing; a point adopted from it enters by a dated change.

Two decisions remain the author's, after stage D has run and before the tag: whether the claim is weakened if the search quantities do not predict completion on the development data (Section 2.1), and whether to proceed, widen the suite or change the claim if the smallest detectable difference is too large to be informative (Section 7.1).
