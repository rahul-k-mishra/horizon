# PREREG, stage E draft: the changes option E would make to docs/PREREG.md draft v0

**Status: not adopted.** Written 13 November 2026 beside docs/PREREG.md, which is unchanged. If the author adopts option E (docs/design/STAGE_E_OPTIONS.md, Section 3), each block below replaces the named part of docs/PREREG.md, marked **[decided <date>]** with his reasons, before the tag. Values in square brackets are open: the ceiling C is chosen from the stage E reading (logs/stage_e_reading.log, once stage E is done), and the other brackets are the decisions of docs/DECISIONS_BEFORE_TAG.md. Every number cited comes from a committed log, as in v0. What v0 says and this draft does not touch stays as it is: the suite, the pilot draw, the agents, the truth tables and predicates, the 98.33% family, the 0.70 floor, the void band, the unit, the bootstrap and the venues.

---

## Replaces Section 1, the claim (first paragraph and the H1/H2 line)

> For frame-only, prior-free agents that act on built-in assumptions, on the levels of unseen deterministic grid games, among levels whose games match the agents' assumptions equally (the same number of the assumptions A1 to A5 holds), a pre-run measure of the level's search, the fewest actions to a win found by breadth-first search within a fixed number of states, ranks the levels by first-level completion above chance.

- H2, search size, is the hypothesis; H1, mechanics match, is held fixed by the comparison: only levels of games with the same mechanics score are compared, so the mechanics score cannot rank them. The registered contrast of v0, Delta = AUROC_H - AUROC_M, becomes a registered secondary estimate (Section 7.7), reported with its smallest detectable difference.
- *Reason:* stage D showed that the contrast of v0 has power 0.03 to 0.05 at the development difference on 26 games, and needs 475 to 887 game clusters for power 0.80 for N (logs/stage_e_diagnosis.log, Section 1). The test above is the part of "search over mechanics" that 26 games can carry.
- Not claimed, in addition to v0's list: how much better search predicts than mechanics; that a level with a longer solution is harder for any agent other than the three evidence agents.

## Replaces Section 6, the search quantities (the lines from "R =" to "Caps")

- **Ceiling.** The breadth-first search of a level stops when it has seen **C = [value] states**, or when its frontier is empty (complete), whichever comes first; the check falls between expansions.
- **L_C** = the fewest actions from the start to a win state, if a win state is among the states seen when the search stops; otherwise "beyond C", ranked longest and tied with every other level beyond C. A level whose search completed without a win is beyond C.
- **H_C** = -log10 min(R, C), R the number of distinct states reachable from the start; a level that reached the ceiling sits at -log10 C, tied with every other such level.
- **b** = over the states expanded, the mean number of distinct successors other than the state itself.
- **Primary search score** = -L_C. Secondary: H_C and b. The effective-horizon bound of v0 is not computed. *Reason:* on development data its AUROC was 0.5164 for N on the 893 units where it exists, and it was missing on 42.8% (logs/dev_reading.log).
- **Caps** (per level, summed over sessions): the ceiling C; time cap 14,400 s; memory ceiling 6 GiB resident per worker; frontier spill at 1,000,000 entries; checkpoint every 600 s or 250,000 expansions. The node cap of v0 is dropped, since a search sees at least as many states as it expands.

## Replaces Section 7.2, the AUROC

AUROC_L = the AUROC of -L_C for Y, over the pairs of a completed and an uncompleted confirmatory level **that come from different games with the same mechanics score S_M**. Mann-Whitney with ties counted 1/2. Pairs from the same game, and pairs from games with different S_M, are excluded. *Reason:* comparing only levels whose games have the same mechanics score holds H1's score fixed by construction. *Cost:* with S_M at 2, 3, 4 and 5 on 3, 13, 7 and 3 games (logs/sdd.log), [the share of between-game pairs kept, printed by the stage E reading on the confirmatory structure].

## Replaces Section 7.3, the interval

The interval of AUROC_L is the percentile interval of 10,000 game-clustered bootstrap resamples: the 26 confirmatory games drawn with replacement, each with all its levels and its S_M. Pairs between two draws of the same game are within-game and excluded. Two-sided at 98.33% (Section 7.5). Seed 20261024 in 8 chunks (default_rng([20261024, k])) on a worker pool. Resamples with no eligible pair are skipped and counted.

## Replaces Section 7.4, the capped-game rule

1. A level whose search stops at the ceiling enters L_C and H_C as defined in Section 6: censored, not excluded.
2. A level whose search stops by the time cap or the memory ceiling before it has seen C states and without completing is excluded from the tests of L_C, H_C and b, unless a win state was seen, in which case it enters L_C with that length. It is listed with its partial counts.
3. A search quantity is void if more than 10% of the confirmatory levels are excluded under rule 2. The share at the ceiling is reported, and is not a reason to void.
4. Every analysis reports the number and share of levels complete, at the ceiling, beyond C for L_C, and excluded.

*Reason:* on development data every level capped by nodes had seen more states than any complete level has, every level capped by time had seen at least 3,091,281 states, and the AUROC of the censored state count was 0.7115 to 0.7158 for N for every ceiling from 10,000 to 5,000,000 states (logs/stage_e_diagnosis.log, Section 3). The 25% rule of v0 would have voided a score that kept its AUROC. [The effect of C on L_C and H_C on the development units: logs/stage_e_reading.log, Section 3, at the C chosen.]

## Replaces Section 7.5, the verdict per evidence agent

Multiplicity unchanged: the family is N, R and I1, each interval two-sided at 98.33%.
- **Search ranks completion among mechanics-matched levels:** the interval's lower end > 0.5 and AUROC_L >= 0.70.
- **Not shown:** otherwise.

## Replaces Section 7.6, the void rules (the first bullet)

- An agent is **void** if its share of levels with Y = 1 lies outside [0.10, 0.90]; if L_C is void (Section 7.4); if fewer than two values of S_M are each held by at least 10% of the confirmatory levels; or if no pair of a completed and an uncompleted level from different games with the same S_M exists.

## Replaces Section 7.7, the secondary analyses

Unadjusted 95% intervals, each labelled secondary, except the first, which keeps the 98.33% level of v0:
- Delta = AUROC_H - AUROC_M of v0, with H_C in place of -log10 R, over all between-game pairs, with its 98.33% interval and its smallest detectable difference d (Section 7.8);
- AUROC of -L_C and of H_C over all between-game pairs; AUROC of H_C over same-S_M pairs; AUROC of S_M; AUROC of b;
- the nuisance baseline B and its three features, and the AUROC of -L_C against B on the same resamples;
- each of A1 to A5 alone; the test on level 0 alone (26 levels); Rand on every line.

## Replaces Section 7.8, first sentence

d = **0.51**, the smallest detectable difference of the secondary Delta (logs/sdd.log): estimate 1, 0.3493, 0.3439 and 0.3208 for N, R and I1; estimate 2, 0.4775, 0.4757 and 0.5059. It is reported beside Delta; it no longer governs the outcome table. [Optional, decision 12: the same method applied to AUROC_L, printed by the stage E reading.]

## Replaces Section 8, gate G3

| G3 | the agent unit cap given by the rule "twice the longest pilot time for 20,000 actions, rounded up to a whole minute" is at most 1,800 s, and the search job on every pilot level completes or reaches the ceiling C within the time cap |

## Replaces Section 9.1, "What it showed"

*Exploratory, development data, not evidence for the registered claim.* On 1,560 units of 156 MiniGrid/BabyAI games, the censored state count ranked first-level completion at AUROC 0.7158 for N, 0.7149 for R and 0.7031 for I1 at a ceiling of 1,000,000 states, with 95% intervals above 0.5 (logs/stage_e_diagnosis.log, Section 3). *Exploratory.* The fewest actions to a win ranked it at 0.7996, 0.8007 and 0.7769 (logs/dev_reading.log), and, over pairs of games with the same mechanics score, at 0.8277, 0.8304 and 0.8487 (logs/stage_e_diagnosis.log, Section 7). *Exploratory.* The mechanics score took two values on this data and was constant on BabyAI, so the development Delta (0.0818, 0.0789, 0.0236, logs/sdd.log) is not an estimate of the confirmatory Delta: inside MiniGrid, where the score varies, it was -0.0341 for N (logs/stage_e_diagnosis.log, Section 2). *Exploratory.* N and R gave the same outcome on 99.2% of units (Section 4). [The stage E paragraph, once read.]

## Replaces Section 10, the outcome table

| outcome | condition | venue |
|---|---|---|
| Support | N shows "search ranks completion among mechanics-matched levels"; at least one of R and I1 does; no evidence agent is void | IEEE Transactions on Games; JAIR instead if all three evidence agents show it |
| Refute | N is not void and Support does not hold; read as "on these 26 games the search score did not rank completion above chance at the registered level among levels whose games have the same mechanics score" | this repository and a preprint on Zenodo |
| Void | N is void, two of the three evidence agents are void, the study is void, or the pilot gate stopped the study | this repository and a preprint on Zenodo, reported as void |

[Decision 8: whether the Support row keeps "at least one of R and I1" now that N and R agree on 99.2% of development units.]

## The header and Section 13

The header lists these changes as decisions of [date], each with its reason; Section 13 stays empty, since they are written into v1 before the tag.
