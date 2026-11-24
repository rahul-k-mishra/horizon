# Decisions before the tag

Written 13 November 2026 for Rahul Kumar Mishra, to be answered before anything is registered. Each item can be answered in a word or two. The reasoning is in docs/design/STAGE_E_OPTIONS.md; the registration text that follows from the recommended answers is in docs/PREREG_stage_e_draft.md and docs/DESIGN_stage_e_draft.md. The answers were given by the author on 14 November 2026 and are written in each Answer line below; their adoption into docs/PREREG.md and docs/DESIGN.md follows in later commits. All MiniGrid/BabyAI figures are EXPLORATORY development data, never evidence for the claim, and each names the committed log it comes from.

## Where things stand, in five lines

1. Stage D is complete: 1,560 search units on 156 MiniGrid/BabyAI games (logs/dev_reading.log).
2. The registered contrast, search AUROC minus mechanics AUROC on 26 GVGAI games, has a smallest detectable difference of 0.51 (logs/sdd.log). If the true difference equals the development one (0.0818 for N), the registered test finds it with probability 0.0345 to 0.0517; power 0.80 would need 475 to 887 games (logs/stage_e_diagnosis.log, Section 1). No change of threshold or agents fixes that; the number of games is the limit.
3. The 25% capped-share rule would void every search measure on the development data (31.2% capped), yet capping costs the state-count AUROC almost nothing: 0.7115 to 0.7158 for N at every ceiling from 10,000 to 5,000,000 states (logs/stage_e_diagnosis.log, Section 3).
4. The fewest actions to a win ranks completion well even among games with the same mechanics score: AUROC 0.8277 for N, 0.8487 for I1 (Section 7). A test on those pairs has power 0.75 for N at the registered level on 26 games, if the confirmatory AUROC is near the development one (Section 6).
5. Stage E, a repeat of the development search that records when the first win is seen, is running (28 sessions, about 6.7 days, logs/make_stage_e_manifest.log). It is needed to pick the ceiling C with its effect on the development counts known.

## The decisions

**Every answer below was given by Rahul Kumar Mishra on 14 November 2026, with the development counts of logs/sdd.log, logs/dev_reading.log and logs/stage_e_diagnosis.log known to him, and before any confirmatory game was played.**

**1. Which path?**
A stop and report what is known; B register as drafted (d = 0.51); C as drafted with the cap rule repaired; D smaller claim on all pairs; E smaller claim on pairs of games with the same mechanics score; F a much larger suite; G edited games that switch predicates on and off.
Counts: B and C have power 0.03 to 0.12 at the development difference; E has 0.75 at 98.33% and 0.87 at 95% for N with L_C; D 0.88 and 0.95 (logs/stage_e_diagnosis.log, Sections 1 and 6). F and G have no cost estimate.
Recommended: **E**.
Answer: **E**, the smaller claim on pairs of games with the same mechanics score. Option F, a much larger suite, is recorded as the next study after this one, not as this registration; it is not registered and not designed here. (Rahul Kumar Mishra, 14 November 2026)

**2. Primary search score: the fewest actions to a win within C states (L_C), or the state count (H_C)?**
Counts, same-mechanics pairs, N: L 0.8277 against H_C 0.6321 on development data; power 0.75 against 0.31 (Sections 6 and 7). H_C is the construct v0 named ("number of reachable states"); L is already a v0 secondary measure.
Recommended: **L_C**.
Answer: **L_C**, the fewest actions to a win within C states. (Rahul Kumar Mishra, 14 November 2026)

**3. Which pairs does the primary test compare: games with the same mechanics score, or all games?**
Same-mechanics pairs answer "does search predict completion where mechanics cannot tell levels apart". All pairs answer only "does search predict completion". Power for N with L_C: 0.75 against 0.88.
Recommended: **same mechanics score**.
Answer: **Same mechanics score**: the primary test compares between-game pairs whose games have the same mechanics score. (Rahul Kumar Mishra, 14 November 2026)

**4. The ceiling C (states seen before the search stops).**
To be chosen when the stage E reading is committed (logs/stage_e_reading.log prints, for C = 10,000, 100,000, 300,000, 1,000,000 and 2,000,000, the units determined, the share beyond C and every AUROC). A smaller C makes the GVGAI search cheaper and more levels "beyond C".
Recommended now: **1,000,000, to confirm or change after the stage E reading**.
Answer: **Deferred.** C is fixed when the stage E reading is committed, with its effect on the development counts known; the registration records the date it was fixed and that it was fixed before any confirmatory game. (Rahul Kumar Mishra, 14 November 2026)

**4a. What each candidate C would mean (written 23 November 2026, for the author; no value is entered).**
*EXPLORATORY throughout:* every figure in this item is development data from MiniGrid/BabyAI, or a simulation built on it, and none is evidence for the claim. Sources: logs/stage_e_reading.log (Section 3, the 1,560 stage E units; Section 4, power on the confirmatory structure of 25 clusters of 5, 98.33% interval and the 0.5 bound as in scripts/stage_e_diagnosis.py, Section 6).

*EXPLORATORY.* Stage E saw 1,560 of 1,560 units, all under schema horizon.search.v3 and seen cap 2,000,000; 521 stopped at the seen cap and 1,039 completed. On the 1,039 units stage D finished with at most 2,000,000 states, stage E gave the same states seen, states expanded and solution length on all 1,039.

| C | units determined | H_C at the ceiling | L_C beyond C | N: AUROC L_C, same S_M [95%] | N: AUROC L_C, all pairs | N: AUROC H_C, same S_M | power of the primary test (L_C, same S_M, 98.33%): N / R / I1 |
|---|---|---|---|---|---|---|---|
| 10,000 | 1,560 (100%) | 830 (53.2%) | 378 (24.2%) | 0.8242 [0.7644, 0.8757] | 0.8081 | 0.6272 | 0.8471 / 0.8524 / 0.7880 |
| 100,000 | 1,560 (100%) | 733 (47.0%) | 243 (15.6%) | 0.8167 [0.7566, 0.8691] | 0.7990 | 0.6085 | 0.8109 / 0.8218 / 0.7435 |
| 300,000 | 1,560 (100%) | 618 (39.6%) | 187 (12.0%) | 0.8161 [0.7568, 0.8683] | 0.7977 | 0.6268 | 0.8059 / 0.8174 / 0.7362 |
| 1,000,000 | 1,560 (100%) | 552 (35.4%) | 162 (10.4%) | 0.8155 [0.7565, 0.8673] | 0.7966 | 0.6321 | 0.8003 / 0.8109 / 0.7354 |
| 2,000,000 | 1,560 (100%) | 521 (33.4%) | 147 (9.4%) | 0.8165 [0.7575, 0.8683] | 0.7972 | 0.6288 | 0.8022 / 0.8130 / 0.7330 |

*EXPLORATORY.* Per family, for N, L_C ranks MiniGrid at 0.8799 to 0.8612 and BabyAI at 0.7708 to 0.7636 as C rises from 10,000 to 2,000,000; R and I1 and their intervals are in the log. At every C no unit is excluded, so the void rule of decision 5 (more than 10% of levels that neither reach C nor complete) voids nothing on the development data.

*EXPLORATORY.* What the table says. Every candidate determines every development unit. The primary AUROC and its power move little with C: for N, same-mechanics AUROC 0.8155 to 0.8242 and power 0.8003 to 0.8471, highest at 10,000. The cost of a small C is the share of levels beyond C, all tied with one another: 24.2% at 10,000 against 10.4% at 1,000,000. On MiniGrid that tie costs nothing, because the levels beyond a small C are mostly the levels the agents fail. Whether the same holds on GVGAI is not known: a box-pushing level can need many states before any win is seen, and the void rule of L_C (PREREG Section 7.4, rule 5, threshold open) is about exactly that.

*The pilot counts (completed 24 November 2026; EXPLORATORY: the pilot games are excluded from every confirmatory analysis, so these counts are evidence about whether the claim can be tested, never evidence for it).* Source: scripts/pilot_reading.py, console logs/pilot_reading.log, which reads only the committed rows of campaign gvgai-pilot-search (chunks p-01 and p-02, kernel versions 123 and 124, code tag automation-v5). 40 rows, all horizon.search.v3: 20 under the registered (extended) key, 20 under the key of v0; every count below is from the 20 extended-key rows, as PREREG Section 8 requires. 12 of the 20 searches completed and 8 stopped at the seen cap of 2,000,000; none stopped by the time cap or the memory ceiling (Section 1 of the log).

| C | win within C | beyond C (complete without a win / at the ceiling without a win) | excluded, PREREG 7.4 rule 2 | bait | labyrinthdual | rivers | watergame |
|---|---|---|---|---|---|---|---|
| 10,000 | 8 of 20 (40.0%) | 12 (4 / 8) | 0 | 2 | 5 | 0 | 1 |
| 100,000 | 10 of 20 (50.0%) | 10 (2 / 8) | 0 | 2 | 5 | 0 | 3 |
| 300,000 | 12 of 20 (60.0%) | 8 (1 / 7) | 0 | 3 | 5 | 0 | 4 |
| 1,000,000 | 13 of 20 (65.0%) | 7 (0 / 7) | 0 | 3 | 5 | 0 | 5 |
| 2,000,000 | 13 of 20 (65.0%) | 7 (0 / 7) | 0 | 3 | 5 | 0 | 5 |

(The last four columns are the levels of each game, of 5, with a win within C; logs/pilot_reading.log, Sections 3 and 4.)

*EXPLORATORY.* What the pilot shows. The wins come by game. Every level of labyrinthdual shows a win early, at 2,028 to 8,833 states seen, and every search of it completes at 138,983 to 159,300 states. watergame shows a win on every level by 1,000,000, the deepest at 637,344 states (level 1). bait, whose boxes the avatar pushes (third_party/gvgai/examples/gridphysics/bait.txt, "box avatar > bounceForward"), shows a win on levels 0, 1 and 2, at 41, 4,356 and 211,672 states, and none within 2,000,000 on levels 3 and 4. rivers shows no win on any level: all five stopped at the seen cap without one. So 3 of the 4 games have a level with a win within C at every candidate, and rivers ties with itself at every candidate. Nothing is gained between 1,000,000 and 2,000,000; one level (watergame 1) is gained between 300,000 and 1,000,000. At 1,000,000 the pilot shows a win on 65.0% of its levels, against 89.6% of the development units of stage E (logs/pilot_reading.log, Section 8).

*EXPLORATORY.* Speed on Kaggle against the laptop (logs/pilot_reading.log, Section 5). Over the 16 pilot levels that ran at least 60 s, Kaggle's expansions per second, over the whole search with 4 workers in one session, were 0.388 of the laptop's figure in logs/engine_speed.log at the median, from 0.099 (labyrinthdual 4) to 0.656 (bait 2). The five slowest are the five labyrinthdual levels (0.099 to 0.409), the only pilot searches whose deepest layer reached 1,001 actions; the laptop's walk restarted at 300 actions. Projected on the 125 confirmatory levels by the method of logs/engine_speed.log (time to see C states bounded above by C over the expansions per second, the laptop's speed times the ratio): at the median ratio, no level's bound reaches the time cap at 10,000 to 1,000,000, and 4 (all lasers) at 2,000,000; the work is 0.03, 0.34, 1.01, 3.36 and 6.60 chunks against the 16 budgeted (logs/design_budget.log). At the lowest ratio, the bounds reach the time cap on 0, 0, 0, 39 and 92 of 125 levels, and the work is 0.13, 1.32, 3.96, 10.73 and 13.99 chunks. More than 10% of the levels' bounds reach the cap, which could void every search quantity under PREREG 7.4 rule 3 if those levels neither completed nor showed a win, only if Kaggle runs at 0.047 of the laptop's speed or less at 300,000, 0.155 or less at 1,000,000 and 0.310 or less at 2,000,000; of the 16 pilot levels, 0, 2 and 5 ran that slowly. The same figures for the 130 levels of v0, garbagecollector included, are in the log. The budget of 16 chunks holds at every C, since every unit is charged at the time cap.

*Recommendation: C = 1,000,000.* Reasons: on the development data its primary AUROC and power differ from the best candidate's by less than the width of one bootstrap interval (0.8155 against 0.8242 for N; power 0.8003 against 0.8471), while it leaves 10.4% of development levels beyond C rather than 24.2%, which keeps L_C able to rank GVGAI levels whose first win lies deep; and it is half the seen cap, so the confirmatory search costs at most what amendment (aa) measured for 2,000,000 states (logs/engine_speed.log), with room for Kaggle being slower than the laptop. *What would make it wrong:* (1) the pilot shows wins on markedly more pilot levels within 2,000,000 than within 1,000,000, which would argue for 2,000,000; (2) the pilot shows that most pilot levels with a win have it within 100,000 states and that the search at 1,000,000 runs into the time cap on Kaggle, which would argue for a smaller C; (3) the pilot shows that the extended key raises the states seen per level enough that few levels show a win even within 2,000,000, in which case no candidate rescues L_C and the void rule decides.

*The recommendation revisited with the pilot counts (24 November 2026; EXPLORATORY figures from logs/pilot_reading.log): keep C = 1,000,000; no value is entered.* Against the three conditions above. (1) Not met: 13 of 20 pilot levels show a win within 1,000,000 and the same 13 within 2,000,000. (2) Half met: 10 of the 13 pilot levels with a win have it within 100,000, but no pilot search stopped by the time cap, and the slowest search, rivers 0, saw 2,000,000 states in 6,932 s against the cap of 14,400 s. (3) Not met: the extended key left the states seen unchanged on 15 of the 20 levels and changed no level's place at or beyond any candidate C (item 4a's key paragraph below). Reasons to keep it: on the pilot it shows a win on one level more than 300,000 and on as many as 2,000,000; at the median Kaggle speed of the pilot no confirmatory level's bound reaches the time cap, against 4 at 2,000,000. *What weighs against it, stated plainly:* the time cap. At 1,000,000 the exclusion rule (7.4, rule 3) is threatened only if Kaggle runs at 0.155 of the laptop's speed or less on more than 10% of the confirmatory levels, and 2 of the 16 pilot levels did (labyrinthdual 2 and 4, both searches that completed at fewer than 160,000 states, so the cap never bore on them). At 300,000 no pilot level came near the corresponding ratio, 0.047. If the author weighs the risk of voiding every search quantity above one pilot level in twenty, 300,000 is the choice; on the development data it leaves 12.0% beyond C against 10.4% and its power for N is 0.8059 against 0.8003 (table above). 2,000,000 is not recommended: it gains no pilot level over 1,000,000, and 5 of the 16 pilot levels ran at or below the ratio, 0.310, at which it would put the rule at risk.

*The extended key's effect on the pilot levels (EXPLORATORY; logs/pilot_reading.log, Section 6), as the author asked in amendment (ab).* Measured, not estimated: each pilot level was searched under both keys in the same campaign. On 15 of the 20 levels (every level of bait, labyrinthdual and watergame) every count is equal under the two keys: states seen, states expanded, whether the search completed, the states seen and expanded at the first win, and the solution length. On the 5 rivers levels both searches stopped at the seen cap without a win; the extended key expanded 0.00% to 4.02% fewer states before reaching the cap (rivers 1: 761,631 against 793,500), so it told more states apart per expansion, but the states reachable under either key are known only to be at least 2,000,000. The levels with a win within C, beyond C and excluded are 8/12/0, 10/10/0, 12/8/0, 13/7/0 and 13/7/0 at the five candidates under both keys: the change of key moves no pilot level across any candidate ceiling. The extended-key searches took 49,200 s in all against 41,331 s for v0 (ratio 1.190), from sessions that ran both kinds at once. *What is not measured:* how much the extended key raises R on rivers beyond 2,000,000. Measuring it would take a search of the five rivers levels under both keys with a seen cap and a time cap high enough for each to complete; the cost cannot be stated, since R under either key is not known.

**5. Replace the 25% capped-share void rule by censoring at C, with a score void only if more than 10% of levels cannot reach C or complete?**
Counts: under v0 every search measure is void on the development data; under censoring at C of 3,000,000 or less, 0 of 1,560 units are excluded for the state count (Section 3).
Recommended: **yes**.
Answer: **Yes.** Censoring at C replaces the 25 per cent capped-share void rule; a score is void only if more than 10 per cent of levels cannot reach C or complete. (Rahul Kumar Mishra, 14 November 2026)

**6. Drop the effective-horizon bound?**
Counts: AUROC 0.5164 for N on the 893 units where it exists; missing on 42.8% (logs/dev_reading.log).
Recommended: **drop**.
Answer: **Dropped from every registered verdict, not deleted.** It is reported in the supplement as an exploratory quantity, with its development AUROC and the share of units on which it could not be computed, so the record shows that a theoretically motivated measure carried nothing on this data. (Rahul Kumar Mishra, 14 November 2026)

**7. The v0 contrast (search AUROC minus mechanics AUROC): keep as a registered secondary estimate with d = 0.51 beside it, or drop?**
Recommended: **keep as secondary**, so the original question is still reported, with its limit stated.
Answer: **Keep** the original contrast, search AUROC minus mechanics AUROC, as a registered secondary estimate, with its smallest detectable difference stated beside it. (Rahul Kumar Mishra, 14 November 2026)

**8. The agents and the Support rule.**
N and R give the same outcome on 99.2% of development units; N and I1 on 74.9% (Section 4). Under "N, and at least one of R and I1", R carries the second condition almost whenever N meets the first. Options: keep as drafted; require N and I1; N alone at 95%. Your decision of 25 October kept the three-agent family and rejected a single primary agent.
Recommended: **keep as drafted, and state the agreement of N and R as a registered limit**.
Answer: **Keep as drafted**, and register the agreement of N and R on 99.2 per cent of development units as a limit. (Rahul Kumar Mishra, 14 November 2026)

**9. Keep the AUROC floor of 0.70 in the verdict?**
Counts: for N, same-mechanics L_C, 0.76 of simulated studies clear both the floor and the 98.33% interval (logs/stage_e_diagnosis.log, Section 6: "both at 98.33% 0.7615").
Recommended: **keep**.
Answer: **Keep** the AUROC floor of 0.70 in the verdict. (Rahul Kumar Mishra, 14 November 2026)

**10. Search the four GVGAI pilot games (bait, labyrinthdual, rivers, watergame; 20 levels) before the tag?**
This is the only way to learn, before C is fixed, how many GVGAI levels show a win within C states; box-pushing games may show none. It needs the GVGAI search job, which must be built before the tag anyway. The pilot games never enter a confirmatory analysis (docs/PREREG.md, Section 4).
Recommended: **yes**.
Answer: **Yes**: search the four GVGAI pilot games before the tag. (Rahul Kumar Mishra, 14 November 2026)

**11. Report the primary score against the nuisance baseline (area, action count, colour count) as a registered secondary comparison?**
Counts: for I1 the in-sample baseline ranks development completion at 0.7522 against the state count's 0.6919 (logs/dev_reading.log).
Recommended: **yes**.
Answer: **Yes**: report the primary score against the nuisance baseline as a registered secondary comparison. (Rahul Kumar Mishra, 14 November 2026)

**12. State the power of the primary test in the registration, as v0 states d for the contrast?**
The stage E reading prints it for every C (Section 4 of its log).
Recommended: **yes**.
Answer: **Yes**: state the power of the primary test in the registration. (Rahul Kumar Mishra, 14 November 2026)

## Still open from earlier sessions

**13. The hand check of the truth tables (gate G4): made by you, or the generator's automated checks alone?** (docs/STATE.md, amendment h). G4 as drafted requires the hand check. Recommended: **by you**, with scripts/handcheck_app.py. Answer: **By the author**, with scripts/handcheck_app.py, as gate G4 requires. Gate G4 stands as drafted. (Rahul Kumar Mishra, 14 November 2026)

**14. The Kaggle image for the confirmatory code tag** (amendment u): the image of every stage D session, gcr.io/kaggle-images/python@sha256:17b2fc7f27c25c6c2fd4230ec8e66097ab2b89fc88e1e4d6f338b72e1ee0bc3e, or another. Recommended: **the stage D image, if Kaggle still runs it then**. Answer: **Stage D's image**, if Kaggle still runs it when the tag is cut; otherwise the author decides again. (Rahul Kumar Mishra, 14 November 2026)

## What happens after the answers

If the answers follow the recommendations: when stage E is done, its reading is committed; the drafts are written into docs/PREREG.md and docs/DESIGN.md with your dates; then the GVGAI adapter, search job, agent copies and analysis script are built and tested, the pilot games are searched (if 10 is yes), C is confirmed, and you create the tag.
