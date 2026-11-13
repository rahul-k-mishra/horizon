# Decisions before the tag

Written 13 November 2026 for Rahul Kumar Mishra, to be answered before anything is registered. Each item can be answered in a word or two. The reasoning is in docs/design/STAGE_E_OPTIONS.md; the registration text that follows from the recommended answers is in docs/PREREG_stage_e_draft.md and docs/DESIGN_stage_e_draft.md. Nothing has been adopted. All MiniGrid/BabyAI figures are EXPLORATORY development data, never evidence for the claim, and each names the committed log it comes from.

## Where things stand, in five lines

1. Stage D is complete: 1,560 search units on 156 MiniGrid/BabyAI games (logs/dev_reading.log).
2. The registered contrast, search AUROC minus mechanics AUROC on 26 GVGAI games, has a smallest detectable difference of 0.51 (logs/sdd.log). If the true difference equals the development one (0.0818 for N), the registered test finds it with probability 0.0345 to 0.0517; power 0.80 would need 475 to 887 games (logs/stage_e_diagnosis.log, Section 1). No change of threshold or agents fixes that; the number of games is the limit.
3. The 25% capped-share rule would void every search measure on the development data (31.2% capped), yet capping costs the state-count AUROC almost nothing: 0.7115 to 0.7158 for N at every ceiling from 10,000 to 5,000,000 states (logs/stage_e_diagnosis.log, Section 3).
4. The fewest actions to a win ranks completion well even among games with the same mechanics score: AUROC 0.8277 for N, 0.8487 for I1 (Section 7). A test on those pairs has power 0.75 for N at the registered level on 26 games, if the confirmatory AUROC is near the development one (Section 6).
5. Stage E, a repeat of the development search that records when the first win is seen, is running (28 sessions, about 6.7 days, logs/make_stage_e_manifest.log). It is needed to pick the ceiling C with its effect on the development counts known.

## The decisions

**1. Which path?**
A stop and report what is known; B register as drafted (d = 0.51); C as drafted with the cap rule repaired; D smaller claim on all pairs; E smaller claim on pairs of games with the same mechanics score; F a much larger suite; G edited games that switch predicates on and off.
Counts: B and C have power 0.03 to 0.12 at the development difference; E has 0.75 at 98.33% and 0.87 at 95% for N with L_C; D 0.88 and 0.95 (logs/stage_e_diagnosis.log, Sections 1 and 6). F and G have no cost estimate.
Recommended: **E**.
Answer: ________

**2. Primary search score: the fewest actions to a win within C states (L_C), or the state count (H_C)?**
Counts, same-mechanics pairs, N: L 0.8277 against H_C 0.6321 on development data; power 0.75 against 0.31 (Sections 6 and 7). H_C is the construct v0 named ("number of reachable states"); L is already a v0 secondary measure.
Recommended: **L_C**.
Answer: ________

**3. Which pairs does the primary test compare: games with the same mechanics score, or all games?**
Same-mechanics pairs answer "does search predict completion where mechanics cannot tell levels apart". All pairs answer only "does search predict completion". Power for N with L_C: 0.75 against 0.88.
Recommended: **same mechanics score**.
Answer: ________

**4. The ceiling C (states seen before the search stops).**
To be chosen when the stage E reading is committed (logs/stage_e_reading.log prints, for C = 10,000, 100,000, 300,000, 1,000,000 and 2,000,000, the units determined, the share beyond C and every AUROC). A smaller C makes the GVGAI search cheaper and more levels "beyond C".
Recommended now: **1,000,000, to confirm or change after the stage E reading**.
Answer: ________

**5. Replace the 25% capped-share void rule by censoring at C, with a score void only if more than 10% of levels cannot reach C or complete?**
Counts: under v0 every search measure is void on the development data; under censoring at C of 3,000,000 or less, 0 of 1,560 units are excluded for the state count (Section 3).
Recommended: **yes**.
Answer: ________

**6. Drop the effective-horizon bound?**
Counts: AUROC 0.5164 for N on the 893 units where it exists; missing on 42.8% (logs/dev_reading.log).
Recommended: **drop**.
Answer: ________

**7. The v0 contrast (search AUROC minus mechanics AUROC): keep as a registered secondary estimate with d = 0.51 beside it, or drop?**
Recommended: **keep as secondary**, so the original question is still reported, with its limit stated.
Answer: ________

**8. The agents and the Support rule.**
N and R give the same outcome on 99.2% of development units; N and I1 on 74.9% (Section 4). Under "N, and at least one of R and I1", R carries the second condition almost whenever N meets the first. Options: keep as drafted; require N and I1; N alone at 95%. Your decision of 25 October kept the three-agent family and rejected a single primary agent.
Recommended: **keep as drafted, and state the agreement of N and R as a registered limit**.
Answer: ________

**9. Keep the AUROC floor of 0.70 in the verdict?**
Counts: for N, same-mechanics L_C, 0.76 of simulated studies clear both the floor and the 98.33% interval (logs/stage_e_diagnosis.log, Section 6: "both at 98.33% 0.7615").
Recommended: **keep**.
Answer: ________

**10. Search the four GVGAI pilot games (bait, labyrinthdual, rivers, watergame; 20 levels) before the tag?**
This is the only way to learn, before C is fixed, how many GVGAI levels show a win within C states; box-pushing games may show none. It needs the GVGAI search job, which must be built before the tag anyway. The pilot games never enter a confirmatory analysis (docs/PREREG.md, Section 4).
Recommended: **yes**.
Answer: ________

**11. Report the primary score against the nuisance baseline (area, action count, colour count) as a registered secondary comparison?**
Counts: for I1 the in-sample baseline ranks development completion at 0.7522 against the state count's 0.6919 (logs/dev_reading.log).
Recommended: **yes**.
Answer: ________

**12. State the power of the primary test in the registration, as v0 states d for the contrast?**
The stage E reading prints it for every C (Section 4 of its log).
Recommended: **yes**.
Answer: ________

## Still open from earlier sessions

**13. The hand check of the truth tables (gate G4): made by you, or the generator's automated checks alone?** (docs/STATE.md, amendment h). G4 as drafted requires the hand check. Recommended: **by you**, with scripts/handcheck_app.py. Answer: ________

**14. The Kaggle image for the confirmatory code tag** (amendment u): the image of every stage D session, gcr.io/kaggle-images/python@sha256:17b2fc7f27c25c6c2fd4230ec8e66097ab2b89fc88e1e4d6f338b72e1ee0bc3e, or another. Recommended: **the stage D image, if Kaggle still runs it then**. Answer: ________

## What happens after the answers

If the answers follow the recommendations: when stage E is done, its reading is committed; the drafts are written into docs/PREREG.md and docs/DESIGN.md with your dates; then the GVGAI adapter, search job, agent copies and analysis script are built and tested, the pilot games are searched (if 10 is yes), C is confirmed, and you create the tag.
