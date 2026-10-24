# Review of the five Phase 3 decisions

Written 24 October 2026, at the author's request, before the decisions were written into docs/DESIGN.md and docs/PREREG.md. This file changes nothing: the five decisions are implemented as the author gave them. A point adopted from here enters the design only by a dated change. Each point names its evidence; a point without evidence is marked **opinion**. Statements about GVGAI's truth tables come from scripts/truth_vgdl.py (logs/truth_vgdl.log), which is a generator not yet hand-checked: they are exploratory.

## Decision 1. The level as the unit, games as clusters

**Same choice: yes, with one change I would make to how the AUROCs are computed.**

- *Evidence.* The mechanics vector does not vary between the levels of any game. Over the 30 deterministic games the generator reports "games whose vector differs between levels: 0" (logs/truth_vgdl.log, the "deterministic games" block). The level-dependent clause, A5's count of goal sprites, never changes the verdict. So S_M is exactly constant inside every game.
- *Consequence.* The registered AUROC counts every (completed, not completed) pair of units (docs/PREREG.md, Section 7.2). In a pair of levels from the same game, S_M ties, and the Mann–Whitney statistic gives that pair ½ by definition. The search score can order the same pair. So within-game pairs pull AUROC_M towards 0.5 by construction, while AUROC_H can gain on them. Part of any positive Δ is therefore built in, and is not evidence that search size beats mechanics *between* games, which is where H1 makes its prediction. The sentence the author asked for (26 effective points for H1) is true, but it does not remove this asymmetry from the test statistic.
- *What I would do instead.* Compute both registered AUROCs over between-game pairs only: pairs whose completed and uncompleted units come from different games. Both scores then compete on the same pairs, and H1 is not charged for pairs it cannot order. Report the within-game AUROC of the search score as a secondary line: it measures what the level unit adds for H2.
- *Cost.* One definition in the analysis script, and fewer pairs, so slightly wider intervals. **Opinion:** the cost is small next to the bias it removes.

## Decision 2. A2 fails for a shooting avatar

**Same choice: yes.**

- *Evidence for the rule.* The registered wording is "exactly one sprite's displacement is a function of the action". A sprite created by the use action is a second object whose existence and position follow from the action. Study 1's census rule for A2 had no such clause. It held A2 when "some key was decided 'accepted' ... and counters.avatar_found == 1" (study 1, docs/PREREG.md v1, Section 5.3, line 157).
- *Evidence for the history, corrected in one detail.* On Procgen, center_off, the census held A2 on 6 games where the truth table fails it (study 1, docs/EXPLORATORY_V1_DIAGNOSIS.md, Table 1, line 40; the games at line 75: bossfight, dodgeball, miner, ninja, plunder, starpilot). In five of them the truth fails because the agent fires or throws (study 1, docs/GROUND_TRUTH_procgen.md, lines 61, 66, 73, 74, 75). In the sixth, miner, it fails because a push moves a boulder (line 72). The design records "six games, five of them by shooting or throwing and one by pushing", so that a reader checking the cited file finds what the text says.
- *Cost, recorded.* On the 30 deterministic games, A2 holds on 50 of 150 units (logs/truth_vgdl.log). With pushes and shooting both failing it, A2 is close to a flag for "has a push or a use action". **Opinion:** that is a fair reading of the construct, not a defect.

## Decision 3. The thresholds

**Same choice for the void band and the capped shares. For the AUROC floor and the family I would make the same choice only if the smallest detectable difference (Decision 5) comes out small enough. Otherwise I would narrow the family.**

- *Evidence on the void band.* Study 1's void rule removed a primary line in practice: R completed 101 of 112 games on MiniGrid macro and was void (docs/oracle/READING.md, Section 2). For GVGAI there is no evidence yet on completion shares. **Opinion:** the deterministic games include several box-pushing puzzles (sokoban, realsokoban, wrapsokoban, doorkoban, among the confirmatory games in logs/draw_pilot.log). There, all three evidence agents may complete almost nothing, and an agent then goes void. The pilot cannot warn of this well with 4 games.
- *Evidence on the family.* Bonferroni over three agents moves the interval from 95% to 98.33%. With 26 clusters that widens an interval that is already wide. docs/DESIGN.md, Section 7 already says no power calculation was made.
- *What I would do instead, if Decision 5's number is large.* Make N the single primary agent: the agent whose assumptions are A1 to A5, so the agent for which H1 is sharpest (docs/DESIGN.md, Section 6). Test it at 95%, and report R and I1 as registered secondary lines.
- *Cost.* The Support condition would rest on one agent, and the broad JAIR condition would need to be restated. **Opinion:** a sharper test of one agent is worth more than an unreachable test of three.

## Decision 4. The development search on MiniGrid before the tag

**Same choice: yes. Three facts from study 1 decide how it must be built, and I have written them into the design as definitions, not as changes to the decision.**

- *The level depends on the seed.* Study 1 reset each MiniGrid environment once with the seed, and later resets were unseeded "so the environment RNG continues deterministically" (study 1, docs/PREREG.md v1, Section 3.2, line 97). Each seed of a game is a different layout. The development unit must be (game, seed), with the search run on the layout of reset(seed).
- *The completion may come on another layout.* An episode that ends without success is followed by "an unseeded reset" (same file, line 98), so study 1's level1_completed can come from a later episode with a different layout. The first layout's search quantities are then an imperfect predictor of the row's outcome. This weakens the development reading and cannot be repaired from the committed rows.
- *Some MiniGrid games move on their own.* Dynamic-Obstacles moves its obstacles at random (study 1, docs/PREREG.md v1, Section 7, line 239). A search over them is not defined, as in GVGAI. They are excluded from stage D.
- *What stage D can and cannot say about H1.* Under macro, the truth vector takes two values on MiniGrid/BabyAI (docs/oracle/READING.md, Section 5). The development contrast is therefore a contrast against an almost constant rival, and says much more about H2 than about H1.

## Decision 5. The smallest detectable difference

**Same choice: yes. Its development data differ from the confirmatory suite in ways that may make the number wrong in either direction.**

- *Evidence.* A development cluster holds 10 seed layouts of one environment; a confirmatory cluster holds 5 levels of one game (logs/vgdl_scan.log: 5 levels for each of the 30 games). A development outcome is one seed's completion; a confirmatory outcome is the majority of 10 seeds (docs/PREREG.md, Section 7.1). S_M takes two values on MiniGrid/BabyAI under macro (docs/oracle/READING.md, Section 5), but five on GVGAI (logs/truth_vgdl.log: S_M from 1 to 5 over the 150 units). scripts/sdd.py states these differences in its docstring and does not correct for them.
- *What I would add.* A second estimate by simulation on the confirmatory structure: 26 games of 5 levels, S_M taken from the GVGAI truth table, and the search score's relation to completion taken from stage D. Reported beside the first estimate, with the larger one registered.
- *Cost.* One more function in scripts/sdd.py, and one more assumption (that stage D's relation between search and completion carries over), stated as such.
- *The plain answer the author asked for.* **Opinion, until scripts/sdd.py has run:** with 26 clusters, a 98.33% interval and an AUROC floor of 0.70, the study can only detect a large difference between the two scores. If the true difference is moderate, the likely outcome is Refute read as "no difference at least this large". That is a legitimate result under rule R5, but a weak one. The alternatives, in order of cost:
  1. between-game pairs (Decision 1), which removes a bias and costs almost nothing;
  2. N as the single primary agent at 95% (Decision 3);
  3. a larger suite. The only nearby source of deterministic declarative games is Griddly, and it adds few: 17 distinct single-player games, 13 of them under its GVGAI folder (logs/suite_evidence.log).

  Making GVGAI's random games deterministic would need the forward model to copy its random generator. A copy gets a fresh, unseeded generator (third_party/gvgai, src/core/game/ForwardModel.java:452, cited in docs/DESIGN.md, Section 3.1). **Opinion:** even with the generator copied, a breadth-first count over states that include the generator's state would count nearly every step as a new state.

## A sixth consideration: the deterministic games remove most of H1's failures

- *Evidence.* Over all 110 grid-physics games, A4 fails on 100 of 550 units. Over the 30 deterministic games it fails on 5 of 150 (logs/truth_vgdl.log, the two blocks). The games excluded as random are those with RandomNPC, SpawnPoint, Chaser and similar classes (logs/vgdl_scan.log, "causes of non-determinism"). These are the moving obstacles that make A4 fail. On the confirmatory suite, A1 holds everywhere (150 of 150) and A4 almost everywhere, so S_M varies through A2, A3 and A5 only.
- *Consequence.* H1 is tested on games chosen, for a technical reason, to be the ones where its most common failure is absent. A Support result would say that search size beats mechanics where mechanics mostly fit. **Opinion:** this is an honest limit and should be stated in the claim's non-claims. It is not a reason to change the suite: the search quantities do not exist on the random games.
- *What I would do.* Add to docs/PREREG.md, Section 1, a non-claim in these words: "the suite excludes games with moving or random sprites, where A4 fails most often, so H1 is tested on games where A1 and A4 almost always hold."
- *Cost.* None in compute; a narrower claim.
