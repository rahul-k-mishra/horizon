# PREREG.md — draft v0 (NOT REGISTERED)

Registration draft for HORIZON, written 24 October 2026 from docs/DESIGN.md, in the form of study 1's docs/PREREG.md v1. **Status: a draft; the author's decisions of 24 October 2026, and the four changes he adopted on 25 October 2026 from docs/design/DECISION_REVIEW.md (marked [changed 25 Oct 2026]), are written in as registered values.** It binds nothing until the author creates the git tag `prereg-v1` on a commit that contains it, as version v1. After the tag it changes only by a new version with a dated diff section (Section 12). Every number below is a chosen value, or is printed by a committed script whose console is committed (logs/suite_evidence.log, logs/vgdl_scan.log, logs/draw_pilot.log, logs/design_budget.log, logs/truth_vgdl.log, logs/draw_handcheck.log).

**What exists at this draft, and what does not.**
- Exists: the automation, proven by its dry run (docs/AUTOMATION.md, docs/DRYRUN.md); the GVGAI descriptions vendored under third_party/gvgai at commit e58ff6597319155218759cc178931e05b81b524c; the eligibility scan scripts/vgdl_scan.py and its output docs/design/vgdl_scan.json; the pilot draw scripts/draw_pilot.py; the truth-table generator scripts/truth_vgdl.py with its synthetic tests and its output docs/truth/gvgai.json (not yet hand-checked); the hand-check sheet docs/truth/HANDCHECK.md; the smallest-detectable-difference script scripts/sdd.py with its synthetic tests.
- Done before the tag, and frozen by blob hash at it: the hand check of Section 5 and any generator fix it requires; stage D (Section 9.1) and the smallest detectable difference (Section 7.8); the GVGAI adapter and frame contract; the search job for GVGAI; the copies of study 1's agents; the analysis script scripts/analyze_horizon.py with synthetic tests.
- Written after the tag, under v1.1: the pilot's values, by the rules of Section 8.

**Decided by the author on 24 October 2026**, each written below as a registered value with its reason (marked **[decided 24 Oct 2026]**):
1. The unit of analysis is the level, with games as bootstrap clusters (Section 4).
2. A2 fails for an avatar whose use action creates a sprite (Section 5).
3. The thresholds stand as drafted: the search AUROC floor 0.70, the Bonferroni family of 98.33% over three agents, the completion void band 10% to 90%, the capped-level shares 25% and 10% (Sections 7.4 to 7.6).
4. Stage D, the development search on study 1's MiniGrid/BabyAI levels, runs before the tag (Section 9.1).
5. The smallest detectable difference is computed and registered before the tag (Section 7.8).

---

## 1. Claim and non-claims

> For frame-only, prior-free agents that act on built-in assumptions, on the levels of unseen deterministic grid games, a pre-run measure of the size of the level's search (the number of reachable states) ranks the levels by first-level completion better than the match between the game's mechanics and the agents' assumptions (the number of the assumptions A1 to A5 that hold).

- H2, search size, is the hypothesis; H1, mechanics match, is the rival. The test can find for either, or for neither (Section 7.5).
- Not claimed: that search size causes failure; that the result transfers to games with random elements, which are excluded by construction (Section 4); that the agents are strong; that anything holds for agents with visual or language priors; any theorem. The effective-horizon bound is computed from a published theorem, not proved anew.
- **A registered limit [changed 25 Oct 2026]:** restricting the suite to deterministic games removes most of its A4 failures: A4 fails on 100 of 550 units across all 110 grid-physics games, against 5 of 150 in the 30 deterministic games (logs/truth_vgdl.log), and it holds on all 26 confirmatory games, as does A1 (logs/sdd.log). So the confirmatory suite varies little on A4, and the study tests H1 mainly through A2, A3 and A5. The smallest detectable difference (Section 7.8) must be read with that in mind; scripts/sdd.py reports the mechanics score's variation in the confirmatory suite beside its number.

## 2. Agents

| agent | what | role |
|---|---|---|
| N | study 1's G-NAV planner, scripts/g_nav.py on scripts/g_agent.py, mode nav: its assumptions are A1 to A5 | evidence, primary |
| R | study 1's hash_state explorer, scripts/g_agent.py, mode hash_state | evidence |
| I1 | Rudakov, Shock and Cowley, "Graph-Based Exploration for ARC-AGI-3 Interactive Reasoning Tasks" (arXiv:2512.24156; MIT), through study 1's adapter | evidence |
| Rand | uniform random actions over the action list, numpy default_rng(seed) | reported, outside the outcome table |

The study-1 files are copied unchanged from study 1's tag prereg-v1.1 and frozen here by blob hash. Before the tag, the copies are checked against study 1's committed rows on a sample of study-1 MiniGrid games: the same (game, seed) must give the same actions and the same row fields except seconds.

## 3. Environment contract and adapter

**Contract** (study 1's, unchanged): reset(seed) gives a grid of integer colour indices; step(action) gives grid, level_end, game_end; a fixed action list per game. No reward, no score, no symbolic state, no text.

**GVGAI adapter [registered here]:**
- Framework: GVGAI at commit e58ff6597319155218759cc178931e05b81b524c, compiled with javac from a pinned Temurin JDK, called in-process through JPype1 1.7.1 under Python 3.11.
- Grid: one cell per level cell, read from the game's observation grid. Each cell's index is given online, in order of first appearance within the run, to the set of visible sprite types in the cell; sprites with hidden=True or invisible=True are not drawn and not counted; the avatar's orientations are one index. Known limit: two sprite types drawn with the same image get different indices.
- Action list: the avatar's available actions without the null action, in GVGAI's order.
- level_end: the game reports a win. game_end: the game reports a loss, or GVGAI's tick limit ends the episode; the next episode starts on the same level.
- Seeds 1000 to 1009 seed the agent; the games are deterministic, so the seed changes nothing in the game.

## 4. Suite, units and splits

- **Eligible games:** the single-player grid-physics games of GVGAI's examples/all_games_sp.csv at the commit above that have a level-0 file, parse, and are deterministic by the rule of scripts/vgdl_scan.py, frozen by its blob hash at the tag: 30 games, each with 5 level files (logs/vgdl_scan.log).
- **Unit [decided 24 Oct 2026]:** a (game, level) pair, levels 0 to 4, with games as the bootstrap clusters. An agent run starts on the unit's level, which is the first level it meets; the agents keep nothing between runs. *Reason:* every level is a first level for an agent that keeps nothing, and the level unit gives the search quantities their full resolution. **The mechanics score is constant within a game, so H1 is tested on 26 effective points whatever the level count; the level unit sharpens the search tests and not the mechanics test.** The 130 confirmatory levels are not 130 independent observations of the mechanics; the generator finds no game whose vector differs between its levels (logs/truth_vgdl.log).
- **Pilot:** 4 games drawn by scripts/draw_pilot.py with seed 20261024 (logs/draw_pilot.log): bait, labyrinthdual, rivers, watergame. They are excluded from every confirmatory analysis.
- **Confirmatory:** the other 26 games, 130 units: chipschallenge, clusters, colourescape, cookmepasta, doorkoban, escape, garbagecollector, glow, grow, hungrybirds, iceandfire, islands, labyrinth, lasers, modality, painter, racebet, racebet2, realsokoban, roadfighter, sokoban, tercio, thecitadel, thesnowman, wrapsokoban, zenpuzzle.
- **Development:** study 1's 175 games, rows and truth tables. Nothing from them enters a confirmatory analysis.

## 5. Truth tables: the mechanics vector

Per (game, level), from the description and the level file, by scripts/truth_vgdl.py (synthetic tests scripts/test_truth_vgdl.py, passing with warnings as errors), output docs/truth/gvgai.json with every clause that decided each entry: file, line, text, and what was read.

- **A1** holds iff the avatar present at level start is of a class that responds to at least two actions: every class except NullAvatar and MissileAvatar. Fails if no avatar is present.
- **A2** holds iff exactly one sprite's displacement is a function of the action, the avatar. It fails if the level does not place exactly one avatar sprite at start; if an interaction moves another sprite because the avatar moved into it (bounceForward, pullWithIt with the avatar as partner); and if the avatar's use action creates a sprite (ShootAvatar, FlakAvatar, ShootOnlyAvatar, AimedAvatar, OngoingShootAvatar) **[decided 24 Oct 2026]**. *Reason:* the predicate says only the avatar's displacement depends on the action; a shot is a sprite created by the action, another object responding to it. Study 1's census rule for A2 had no such clause (study 1, docs/PREREG.md v1, Section 5.3), and there it disagreed with the Procgen truth table on six games, five of them because the agent fires or throws and one (miner) because a push moves a boulder (study 1, docs/EXPLORATORY_V1_DIAGNOSIS.md, Tables 1 and 2).
- **A3** holds iff each movement action, when not blocked, shifts the avatar by one constant vector whatever its position, facing and history: MovingAvatar, HorizontalAvatar, VerticalAvatar and FlakAvatar at speed 1; OrientedAvatar and ShootAvatar only with rotateInPlace=False. It fails for every other avatar class, for a speed other than 1, and where an interaction moves the avatar (teleportToExit, wrapAround, pullWithIt, bounceForward, windGust, slipForward, conveySprite, attractGaze).
- **A4** holds iff every move without effect is explained by a sprite that blocks the avatar (stepBack or undoAll with the avatar), every blocking type is of a class that never moves on its own (Immovable, Passive, Door, Resource, ResourcePack, SpawnPoint, SpawnPointMultiSprite, Portal, SpriteProducer), and blocking sprites are created, removed or moved only through the avatar's own actions: by interactions whose names include only agent-driven sprites, which are the avatar, the sprites its use action creates, and stationary-class sprites that only those push or pull. A sprite that kills on contact does not block.
- **A5** holds iff the only winning condition is a SpriteCounter with limit 0 on one sprite type, the level holds exactly one sprite of that type, and every interaction that removes it has the avatar or an avatar subtype as partner; a precondition met elsewhere is recorded and keeps A5 holding.

**Mechanics score S_M** = the number of A1 to A5 that hold.

**Hand check.** Before the tag the author checks the generator by hand on 10 games drawn with seed 20261025 from the 30, every predicate, on level 0 and on one other level drawn with the same seed (scripts/draw_handcheck.py, logs/draw_handcheck.log; the sheet is docs/truth/HANDCHECK.md): clusters, colourescape, glow, labyrinthdual, lasers, painter, racebet, rivers, sokoban, wrapsokoban. Every disagreement is resolved from the GVGAI source, fixes the generator, and is listed in v1; the generator is rerun on all units and 5 fresh games are checked, which must agree on every predicate.

## 6. Search quantities

Per (game, level), by the search job of docs/AUTOMATION.md, Sections 5 and 6:
- **State:** for every sprite, its type, cell, orientation and resources, and the avatar's health points; the game tick only where the description has a Timeout termination or a sprite with a cooldown, limit or total parameter. Identified by a 64-bit hash of a canonical serialization. GVGAI's tick limit is not part of the search.
- **Actions:** the adapter's action list. **Start:** the state after the level file is loaded. Win and loss states are counted and not expanded.
- **R** = the number of distinct states reachable from the start. **L** = the fewest actions from the start to a win state; infinite if the search is complete without one. **b** = over the states expanded, the mean number of distinct successors other than the state itself.
- **EH** = the effective-horizon bound of Laidlaw, Russell and Dragan (NeurIPS 2023, arXiv:2304.09853), Theorem 5.4, on the level's deterministic MDP with reward 1 on entering a win state, win and loss states absorbing, horizon T = 400 and the uniform random exploration policy, minimised over k ∈ {1, 2, 3} for which the MDP is k-QVI-solvable (their Definition 5.1), as written out in docs/DESIGN.md, Section 5; infinite if none is or if L > T. Computed only when the search is complete with R ≤ 200,000.
- **Primary search score** = −log10 R. Secondary: L, b, EH.
- **Caps** (per unit, summed over sessions): node cap 5,000,000 states expanded; time cap 14,400 s; memory ceiling 6 GiB resident per worker; frontier spill at 1,000,000 entries; checkpoint every 600 s or 250,000 expansions.

## 7. Tests

### 7.1 Outcome
Per (agent, unit): 20,000 actions per seed, seeds 1000 to 1009. Y = 1 if the agent completed the level in at least 5 of the 10 seeds.

### 7.2 AUROC
AUROC_H = the AUROC of −log10 R for Y; AUROC_M = the AUROC of S_M for Y; the Mann–Whitney statistic with ties counted ½, over the pairs of a completed and an uncompleted confirmatory unit **that come from different games**; within-game pairs are excluded from both **[changed 25 Oct 2026]**. *Reason:* the mechanics score is constant inside a game, so a within-game pair is scored one half for the mechanics score by construction while the search score can order it, which would hand part of the contrast to H2 before any data. *Cost:* at most 6 within-game pairs per game, at most 156 over the 26 games: at most 10.3% of all pairs at an edge of the void band, 3.7% at a completed share of one half (logs/design_budget.log). The bootstrap of Section 7.3 is unchanged; pairs between two draws of the same game in a resample are within-game and excluded.

### 7.3 The contrast and its interval
Δ = AUROC_H − AUROC_M. Its interval is the percentile interval of 10,000 game-clustered bootstrap resamples: the 26 confirmatory games drawn with replacement, each with all its units, the same resample for both AUROCs. Seed 20261024 in 8 chunks (default_rng([20261024, k])) on a worker pool. Resamples with one class only are skipped and counted.

### 7.4 The capped-game rule [decided 24 Oct 2026]
1. A unit stopped by the node cap enters R as the node cap, ranked largest and tied with every other node-capped unit; L as found if a win state was reached, otherwise as infinite, ranked longest and tied; b over the states expanded; EH as not computed.
2. A unit stopped by the time cap or the memory ceiling before the node cap is excluded from the tests of R, b and EH, and from the test of L unless a win state was reached; it is listed with its partial counts.
3. A search quantity is void if more than 25% of the confirmatory units are capped by any cap, or more than 10% are excluded under rule 2. For EH the 25% counts units where EH was not computed for any reason.
4. Every analysis reports the number and share of capped units per cap.

### 7.5 Verdict per evidence agent [decided 24 Oct 2026]
Multiplicity: the family is the three evidence agents N, R and I1, and each interval of Δ is a two-sided 98.33% interval (Bonferroni, 0.05 / 3).
- **H2 over H1:** the interval's lower end > 0 and AUROC_H ≥ 0.70.
- **H1 over H2:** the interval's upper end < 0 and AUROC_M ≥ 0.70.
- **Neither:** otherwise.

The thresholds of Sections 7.4 to 7.6 (the AUROC floor 0.70, the 98.33% family, the void band 10% to 90%, the capped shares 25% and 10%) are arbitrary in the way all such thresholds are; their legitimacy comes from being fixed before any confirmatory run.

### 7.6 Void rules
- An agent is **void** if its share of units with Y = 1 lies outside [0.10, 0.90]; if the primary search score is void (Section 7.4); or if fewer than two values of S_M are each held by at least 10% of the confirmatory units.
- The study is **void** if fewer than 20 confirmatory games remain, or if two of the three evidence agents are void **[changed 25 Oct 2026]**. No agent is added, removed or re-weighted after the fact; the three agents and the 98.33% family stand as registered. *Reason:* what follows from agents voiding is fixed before any run. A single primary agent at 95% was considered and not adopted, because narrowing the test after seeing the risk would weaken the registration (docs/design/DECISION_REVIEW.md, Decision 3).

### 7.7 Secondary analyses, outside the outcome table
Unadjusted 95% intervals, each labelled secondary: AUROC and Δ against S_M for L, b and EH; the contrast on level 0 alone (26 units, games resampled); each of A1 to A5 alone; grid area, action count and colour count (study 1's nuisance features); Rand on every line.

### 7.8 The smallest detectable difference [decided 24 Oct 2026]
d = **[the number printed by scripts/sdd.py in logs/sdd.log, entered here before the tag, with both estimates below; the script waits on stage D's rows]**.

Estimate 1, from the development data: **[from logs/sdd.log]**. Estimate 2, on the confirmatory structure **[changed 25 Oct 2026]**: **[from logs/sdd.log]**. The mechanics score's variation in the confirmatory suite, reported beside them: S_M is 2 on 3 games, 3 on 11, 4 on 9 and 5 on 3, and A1 and A4 hold on all 26 (logs/sdd.log).

Method: on stage D's development units, for each evidence agent, 4,000 simulated studies each draw 26 development games with replacement (each with all its units) and compute Δ over between-game pairs; SE is the standard deviation of Δ over them; the estimate is (z(1 − α/2) + z(0.80)) × SE with α = 0.05 / 3. Estimate 2 **[changed 25 Oct 2026]** repeats this on the confirmatory structure: 26 clusters of 5 units, each carrying the actual S_M of a confirmatory game drawn with replacement and the search scores and outcomes of 5 units of a development game; there the mechanics score has no relation to the outcome, so the estimate measures the spread of Δ under the suite's own S_M values and ties. d is the larger estimate, the largest over N, R and I1, rounded up to two decimals. It is the true difference at which the registered interval would exclude zero with probability 0.80, under a normal approximation. *Reason:* a Refute outcome must state the size of difference it rules out. **A Refute outcome reads "no difference of at least d between the search score and the mechanics score", not "the data could not tell".** If d is so large that the study is uninformative, the author decides before the tag whether to proceed, widen the suite or change the claim, and records the decision in v1.

## 8. Pilot gate and stop rule [registered here]

Run after the tag of v1, before any confirmatory unit, on the 4 pilot games (20 units):

| gate | passes if |
|---|---|
| G1 | the adapter, JDK and JPype run in a Kaggle session from a clean start, and each of N, R, I1 and Rand plays 20,000 actions on 2 seeds of every pilot unit without an error |
| G2 | on every pilot unit, 1,000 random action sequences of length 200, each replayed twice from the start, give identical state hashes at every step |
| G3 | the agent unit cap given by the rule "twice the longest pilot time for 20,000 actions, rounded up to a whole minute" is at most 1,800 s, and the search job on every pilot unit completes or stops at the node cap |
| G4 | the hand check of Section 5 has passed |
| G5 | from the truth table alone, at least two values of S_M are each held by at least 10% of the confirmatory units |

**Stop rule.** If any gate fails, no confirmatory unit runs. A failure of G1, G2 or G4 may be repaired once, by changing adapter, search or generator code only, never a threshold, a cap rule, a predicate or the game list; the repair is recorded in v1.1 and the pilot is rerun on the same pilot games. A second failure of the same gate, or any failure of G3 or G5, stops the study with the outcome VOID. The agent unit cap enters v1.1 by the rule of G3, and v1.1 is tagged before any confirmatory unit runs.

## 9. Runs

- All runs go through the loop of docs/AUTOMATION.md under the author's Kaggle account; no run is made by hand.
- Search kind: one unit per (game, level). Agent kind: one unit per (agent, game, level, seed). A chunk holds one kind only.
- Session: work 28,800 s, checkpoint reserve 900 s, platform_limit_seconds 32,400; latest end 8 h 31 min after the notebook starts (logs/design_budget.log).
- Rows: the search and agent schemas horizon.search.v1 and horizon.agent.v1 (scripts/automation/schema.py); features are read only from search rows and truth tables, outcomes only from agent rows.
- Budget, at most (logs/design_budget.log): 3 chunks of pilot search, 3 of pilot agents, 17 of confirmatory search, and 14 to 82 of confirmatory agents, depending on the pilot's agent cap; 232 to 300 chunks with stage D (195 at most at the registered time cap; its manifest has 39 chunks, logs/make_stage_d_manifest.log).

### 9.1 Stage D, run before the tag [decided 24 Oct 2026]
- **What ran:** the search job of Section 6 with the same quantities (R, L, b, and EH where its limits allow) on study 1's confirmatory MiniGrid/BabyAI games in the macro condition, one unit per (game, seed) for seeds 1000 to 1009, the layout produced by reset(seed); the 5 Dynamic-Obstacles games excluded because their obstacles move at random, leaving 156 games and 1,560 units (logs/make_stage_d_manifest.log). The registered caps of Section 6. Kind devsearch, campaign dev-minigrid, rows of the schema horizon.search.v2 under runs/dev-minigrid/devsearch/ (docs/AUTOMATION.md, Section 5.1). Outcomes are study 1's committed rows, read and never written. *Reason:* the claim is registered knowing whether the search quantities rank completion at all on data whose outcomes already exist.
- **What it showed:** **[entered here before the tag, from its analysis log, each paragraph labelled exploratory]**.
- **It may not be used as evidence for the registered claim.** It is development data, and its mechanics vector takes two values (docs/oracle/READING.md, Section 5).
- **If the search quantities did not predict completion there,** the author decides before the tag whether the registered claim is weakened, and records the decision here.

## 10. Outcome and venue, fixed before any confirmatory run

| outcome | condition | venue |
|---|---|---|
| Support | N is H2 over H1; at least one of R and I1 is H2 over H1; no evidence agent is H1 over H2 | IEEE Transactions on Games; JAIR instead if all three evidence agents are H2 over H1 |
| Refute | N is not void and Support does not hold; read as "no difference of at least d" (Section 7.8) | this repository and a preprint on Zenodo |
| Void | N is void, two of the three evidence agents are void, the study is void, or the pilot gate stopped the study | this repository and a preprint on Zenodo, reported as void |

## 11. Analysis code

scripts/analyze_horizon.py reads the truth table, the search rows and the agent rows, and writes docs/tables/horizon.md and .json: every line of Sections 7.2 to 7.7 with its interval, the capped counts, and the verdicts. Its synthetic tests, with expected values computed by hand in the docstring, pass before the tag. The script is frozen at the tag; the only permitted change is a crash fix, logged in Section 13.

## 12. Amendment rules

- This file changes only by a new version (v1.1, v1.2, …), each with a dated diff section listing every changed line and why.
- The pilot may change adapter, search and generator code by the stop rule of Section 8, never a threshold, a predicate, a cap rule, a seed or the game list.
- A test not in the tagged version before its run is exploratory and enters no claim.

## 13. Diff section

Empty in draft v0. The author's decisions of 24 October 2026 and the changes of 25 October 2026 were written into the draft before any tag, so they are part of v1 as tagged, not amendments.
