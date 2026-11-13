# Stage E: what stage D showed, the options, and one recommendation

Written 13 November 2026. Nothing here is registered and nothing here decides. The registered documents, docs/PREREG.md draft v0 and docs/DESIGN.md, are unchanged; the text the author would adopt is in docs/PREREG_stage_e_draft.md and docs/DESIGN_stage_e_draft.md, and the questions are in docs/DECISIONS_BEFORE_TAG.md. **Every number below about MiniGrid/BabyAI is EXPLORATORY: development data, never evidence for the claim.** Each number names the committed log it comes from: logs/sdd.log, logs/dev_reading.log, logs/stage_e_diagnosis.log (scripts/stage_e_diagnosis.py, run on committed files only), logs/make_stage_e_manifest.log and logs/design_budget.log.

## 1. The diagnosis

### 1.1 The registered contrast cannot detect the difference the development data suggest

*Exploratory.* The registered smallest detectable difference is 0.51 (logs/sdd.log). The development Delta is 0.0818 for N, 0.0789 for R and 0.0236 for I1 (logs/sdd.log). If the true Delta on the confirmatory suite were the development value, the registered 98.33% interval would exclude zero with probability 0.0517 for N on the development structure and 0.0345 on the confirmatory structure; 0.0502 and 0.0333 for R; 0.0198 and 0.0179 for I1 (logs/stage_e_diagnosis.log, Section 1). Power 0.80 at N's development Delta would need 475 game clusters on the development structure or 887 on the confirmatory structure, against the 26 the suite has. Testing N alone at 95% instead of the three-agent family lowers the detectable difference to 0.3025 and 0.4134, still far above any development Delta (same section).

A Refute would read "no difference of at least 0.51". Both AUROCs lie between 0 and 1, and every development AUROC of H and S_M lies between 0.50 and 0.90 (logs/dev_reading.log), so that sentence would be true in nearly any world the development data allow. It would rule out almost nothing.

**Whose fault.** The number of clusters is a property of the world: GVGAI has 30 deterministic grid-physics games and the design keeps 26 of them (logs/vgdl_scan.log, logs/draw_pilot.log). So is the size of the difference, as far as the development data can tell. The design fault is to make a game-level contrast between two scores the registered claim on a 26-game suite. No choice of threshold, cap or agent family fixes it; only more games, or a different claim, can.

### 1.2 The development Delta does not measure what the registered Delta would measure

*Exploratory.* On the development data the mechanics score takes two values: 4 or 5 on MiniGrid (30 and 31 games), and 4 on all 95 BabyAI games (logs/stage_e_diagnosis.log, Section 2). So S_M's AUROC on BabyAI is 0.5000 by construction (logs/dev_reading.log). The overall Delta is the sum of three different comparisons. For N:

| between-game pairs | share of pairs | AUROC of H | AUROC of S_M | difference |
|---|---|---|---|---|
| both games MiniGrid | 18.0% | 0.8545 | 0.8886 | -0.0341 |
| both games BabyAI | 32.8% | 0.6849 | 0.5000 | +0.1849 |
| one of each | 49.2% | 0.7139 | 0.6585 | +0.0554 |
| all | 100% | 0.7297 | 0.6479 | +0.0818 |

(logs/stage_e_diagnosis.log, Section 2; R and I1 have the same shape.) Where the mechanics score varies, inside MiniGrid, it ranks completion as well as or better than search size, for N and R. The positive overall Delta comes from BabyAI, where S_M cannot rank anything, and from pairs across the two families. The development data therefore say little about the size or the sign of Delta on a suite where S_M takes four values, as it does on the confirmatory suite (S_M = 2, 3, 4, 5 on 3, 13, 7, 3 games, logs/sdd.log). The SE that scripts/sdd.py measures is real; the development Delta is not a forecast.

**Whose fault.** That MiniGrid/BabyAI barely vary in mechanics is the world (docs/oracle/READING.md, Section 5 had already said so). Reading the overall Delta as an effect size would be a fault of interpretation, which the design does not make: it uses the development data for the SE only.

### 1.3 The capped-share void rule guards against a loss that does not occur

*Exploratory.* Under the registered rule, 31.2% of development units are capped against a 25% limit, and the effective-horizon bound is missing on 42.8% (logs/dev_reading.log), so every search quantity would be void on the development data. But:

- every node-capped unit had seen more states (at least 5,176,010) than any complete unit has (at most 4,757,411), so the registered rule 1, which ranks node-capped units largest, orders them correctly against complete units and loses only the order among them (logs/stage_e_diagnosis.log, Section 3);
- every time-capped unit had seen at least 3,091,281 states before it stopped (same section). Censored at a ceiling C of 3,000,000 or less, the score H_C = -log10 min(R, C) is defined on all 1,560 units: no exclusions;
- the AUROC of H_C barely moves with C. For N: 0.7115 at C = 10,000, 0.7158 at 1,000,000, 0.7145 at 5,000,000; for I1: 0.7187, 0.7031, 0.6945 (same section). At C = 1,000,000 N's AUROC is 0.7158 with 95% interval [0.6421, 0.7921], with 552 units (35.4%) at the ceiling and none excluded.

So the ceiling share is not a threat to the validity of the score on this data, and it costs almost no resolution. The 25% rule would void a score that keeps its AUROC. The effective-horizon bound is a different matter: its AUROC is 0.5164 for N on the 893 units where it exists (logs/dev_reading.log), and it cannot be computed above 200,000 states by design. It carries nothing here.

**Whose fault.** That some levels have more states than any cap can reach is the world (PutNext, ObstructedMaze and others are capped on every seed, logs/dev_reading.log). Treating the capped share as a reason to void, instead of censoring at a fixed ceiling, is a fault of the design, and it can be repaired before the tag at no cost in compute. Whether GVGAI levels reach a given ceiling within the time cap is unknown until GVGAI levels are searched.

### 1.4 Things neither the author nor the earlier sessions raised

*Exploratory.*

1. **N and R are almost the same agent on this data.** They give the same outcome on 1,547 of 1,560 units (99.2%) and the same number of completed seeds on 147 of 156 games (logs/stage_e_diagnosis.log, Section 4). N and I1 agree on 74.9% of units. The family of three evidence agents is in effect two. The Support rule ("N, and at least one of R and I1") is met by R almost whenever N meets it, and the Bonferroni correction pays for a third test that adds almost no information.
2. **The outcome lives between games.** Only 24 of 156 games have both outcomes among their 10 seeds for N, and within-game pairs are 0.1% of all completed–uncompleted pairs (Section 5). The effective sample is the number of games, whatever the number of levels. On GVGAI, with 26 games, every test of the study is limited by that count, not by the 130 levels.
3. **The fewest actions to a win, L, ranks completion better than the state count, and keeps doing so among games with the same mechanics score.** Overall, L's AUROC is 0.7996 for N against 0.7297 for H (logs/dev_reading.log). Over between-game pairs of games with the same development S_M, L gives 0.8277 [0.7676, 0.8802] for N and 0.8487 [0.7960, 0.8923] for I1, and H_C gives 0.6321 [0.5502, 0.7216] and 0.5760 [0.4744, 0.6817] (logs/stage_e_diagnosis.log, Section 7). L is already a registered secondary quantity.
4. **The information in H is mostly whether a level is small.** At C = 10,000 more than half the units sit at the ceiling (53.2%), and the AUROC is the same as at 5,000,000 (Section 3).
5. **The nuisance baseline is not part of any verdict.** For I1 the in-sample nuisance baseline B (area, actions, colours) has AUROC 0.7522 against H's 0.6919 overall, and on BabyAI B is above H for all three agents (logs/dev_reading.log). A Support for H2 could stand while a colour count ranks completion better. B is fitted in sample and so flattered, but the point stands as a limit to state.
6. **The development outcome is one seed's completion; the confirmatory outcome is the majority of 10 seeds on a deterministic level.** scripts/sdd.py states this and does not correct it; every power figure here inherits it.

## 2. The options

Kaggle costs are in chunks of one session each, run one at a time by the loop. GVGAI work is the adapter, the GVGAI search job, the copies of study 1's agents and scripts/analyze_horizon.py, all listed as "done before the tag" in docs/PREREG.md and none of them built yet; every option that reaches a confirmatory run needs them, and their engineering time has no committed estimate.

| | what is registered | re-run on development first | Kaggle cost | can show | cannot show | how it fails |
|---|---|---|---|---|---|---|
| **A. Stop** | nothing; the oracle test, stage D and this diagnosis go out as an exploratory report (repository and Zenodo) | nothing | none | what the development data say, labelled exploratory | any confirmatory claim | it does not fail; it gives up the GVGAI test |
| **B. As drafted** | the claim of PREREG v0 with d = 0.51 | nothing | pilot 6 chunks, confirmatory search at most 17, agents 14 to 82 (logs/design_budget.log) | a difference of 0.51 or more | anything smaller: power 0.03 to 0.05 at the development Delta | a Refute that rules out almost nothing; or Void, if GVGAI levels cap as often as MiniGrid/BabyAI (31.2%) |
| **C. As drafted, repaired** | B with the censoring rule of Section 1.3 in place of the 25% rule, EH dropped, and N alone at 95% | stage E (Section 4) to fix C | as B, plus stage E | a difference of 0.41 or more (N, confirmatory structure) | anything smaller: power 0.09 at N's development Delta | as B, without the risk of Void by capping |
| **D. Smaller claim, all pairs** | "the search score ranks first-level completion above chance": AUROC of L_C (or H_C) over between-game pairs, per agent; Delta as a registered secondary estimate | stage E | as B, plus stage E | that a pre-run search measure ranks completion on unseen games | anything about search against mechanics: the score may carry the mechanics signal | GVGAI levels beyond the ceiling for most units (L_C ties); power for N: L_C 0.88 at 98.33%, H_C 0.43 (logs/stage_e_diagnosis.log, Section 6) |
| **E. Smaller claim, same-mechanics pairs** (recommended) | "among levels of games with the same mechanics score, the search score ranks first-level completion above chance": AUROC of L_C over between-game pairs whose games share S_M, per agent; Delta and the all-pairs AUROC as registered secondary estimates | stage E | as B, plus stage E | that search predicts completion beyond what the mechanics score can, among games that match the agents' assumptions equally | how large search's advantage over mechanics is; anything about H1 alone | as D; power for N with L_C 0.75 at 98.33%, 0.87 at 95%; with H_C 0.31 and 0.48 (Section 6) |
| **F. Widen the suite** | the claim of v0, or of E, on a much larger set of deterministic grid games (for example a PuzzleScript corpus, not weighed in October) | a new development reading on the new suite | unknown: new engine, generator, adapter and agents | the original contrast, if the corpus offers hundreds of games: 475 to 887 clusters for N at the development Delta | nothing until the suite exists; whether a corpus with enough eligible games and an engine usable from Python on Kaggle exists has not been checked | months of building; and the development Delta may not be the confirmatory one (Section 1.2) |
| **G. Change mechanics inside games** | H1 tested on edited copies of each GVGAI game, each predicate switched on or off, so that mechanics vary within a game | a new generator and new levels | unknown | whether breaking an assumption lowers completion, game by game | anything about natural games; edited games are the author's construction | each edit also changes the search; and which edits are made is a choice that can follow the hoped-for result |

*Power figures in the table are exploratory and assume that the confirmatory AUROC is near the development one; the true AUROC needed for power 0.80 for N's same-mechanics L_C test is 0.8026 at 98.33% and 0.7620 at 95% (logs/stage_e_diagnosis.log, Section 6).*

## 3. The recommendation: E, with stage E run first

**What.** Keep the suite, the agents, the 98.33% family, the 0.70 floor and the venues. Register as the primary test, per evidence agent, the AUROC of L_C, the fewest actions to a win if one is seen among the first C states of the breadth-first search and "beyond C" otherwise, over between-game pairs of levels whose games have the same mechanics score. Keep the registered contrast Delta, the all-pairs AUROCs of L_C and H_C, the mechanics score's own AUROC and the nuisance baseline as registered secondary estimates with their intervals, and state Delta's detectable difference beside it. Replace the capped-share void rule by censoring at C: a unit is excluded only if it stops without completing before it has seen C states, and the score is void if more than 10% of the confirmatory units are excluded. Drop the effective-horizon bound. The full text is in docs/PREREG_stage_e_draft.md.

**Why.** It is the strongest statement about search against mechanics that 26 games can carry. Comparing levels only with levels whose games have the same mechanics score removes the mechanics score from the comparison by design, so a positive result says that search size predicts completion where mechanics cannot tell the levels apart. That is the part of "H2 over H1" that is testable here; the size of the advantage is not. It is the claim the development data support: 0.83 for N and R and 0.85 for I1 on same-mechanics pairs, with intervals well above one half (Section 1.4, point 3). It has usable power if the confirmatory AUROC is near the development one: 0.75 for N at the registered 98.33% level (Section 2). And it removes the two design faults of Section 1 without touching a predicate, the suite or the agents.

**Why stage E first.** The constraint is that any ceiling or exclusion rule is fixed with its effect on the development counts known and recorded. Stage D's rows give H_C exactly for every C up to 3,000,000, but not L_C: they record the length of the shortest solution, not when in the search the first win was seen, so for 521 units (those stage D did not finish at or below 2,000,000 states, logs/make_stage_e_manifest.log) L_C at a lower ceiling is unknown. Stage E searches the same 1,560 units again with a seen cap and records that count. Its rows give H_C and L_C exactly for every C up to 2,000,000, and its reading (scripts/stage_e_reading.py) prints, for each candidate C, the units determined, the units beyond the ceiling and the AUROCs, before the author picks C. It also repeats every stage D unit that finished below the cap, which checks that the search is deterministic across sessions and code versions.

**What would have to be true for this to be wrong.**

1. *GVGAI levels rarely show a win within C states.* Box-pushing games (sokoban, realsokoban, wrapsokoban, thecitadel, zenpuzzle and others among the 26) may need very many states before a win appears. If most confirmatory levels are "beyond C", L_C ties on most pairs and the test has little power. Stage E cannot measure this on GVGAI; a search of the four pilot games before the tag can (decision 10 of docs/DECISIONS_BEFORE_TAG.md).
2. *The development link between L and completion belongs to MiniGrid.* MiniGrid goals are mostly reached by walking, and N is a navigation planner. On GVGAI, where a win may need pushing, collecting or avoiding, completion may depend on things a solution length does not see. Then the confirmatory AUROC falls below about 0.76, and power with it (Section 2 note).
3. *A reader may call the claim close to self-evident:* a level with a short solution is solved by agents that explore. It is a pre-run property of the level and its rival is registered, but the paper must say this plainly.
4. *The author values the original question more than a testable narrower one.* Then A (stop, report what is known) or F (a larger suite) is the right answer, and E is a detour.

## 4. Stage E, built and launched

- **Code**, tagged automation-v3: the kind devsearch with the row schema horizon.search.v3, which adds a cap on the states seen (cap_hit "seen") and records seen_at_first_win and expanded_at_first_win (scripts/automation/jobs.py, schema.py, runner.py). Under v1 and v2 nothing changes; stage D's rows and code tag are untouched.
- **Tests**: scripts/automation/test_devsearch.py (eight parts; v3 equals v2 on six levels with a cap no search reaches, the seen cap stops within one state's successors and records the first win exactly, and a resumed v3 search equals an uninterrupted one), OK (logs/test_devsearch.log); scripts/automation/test_loop.py with a v3 run of the devsearch scenario, all scenarios OK (logs/test_loop.log); scripts/test_stage_e_reading.py, OK (logs/test_stage_e_reading.log).
- **Manifest** (scripts/make_stage_e_manifest.py, logs/make_stage_e_manifest.log): campaign dev-minigrid-e; 1,560 units, the units of stage D; seen cap 2,000,000 states, node cap 5,000,000, time cap 14,400 s, 6 GiB per worker; 28 chunks packed from stage D's own timings to at most 60% of a session; estimated 1,889,607 worker-seconds; the longest chunk estimated at 21,657 s against 28,800 s of work; expected 28 sessions and 6.71 days, with 195 sessions at most if every unit used its whole time cap.
- **Reading**: scripts/stage_e_reading.py, run once every chunk is done; until then it prints "waiting".
