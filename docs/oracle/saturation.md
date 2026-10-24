# How the perfect separations of the oracle test arise (EXPLORATORY)

**EXPLORATORY.** Written by scripts/oracle_sat.py from docs/oracle/oracle_v2.json and the study-1 rows. Nothing here is registered and nothing here is a claim.

## Checks

*EXPLORATORY.*
- oracle_v2.json lines: 20
- rows: 10500 files, 10080 confirmatory rows kept, 420 pilot rows skipped
- consistency with oracle_v2.json: 2017 of 2017 games agree on 20 of 20 lines
- saturated items: 41 on 11 lines; lines also separated by the majority censoring flag alone: 8

## Table 1. The pre-run number

*EXPLORATORY.* AUROC of the three features known before any agent runs, each alone (a larger value predicts no completion) and together in oracle_v2's logistic model, in-sample and leave-one-game-out. "constant" names a feature with one value on every game of the line.

| suite | condition | subset | agent | n | pos | area | actions | colours | B in-sample | B leave-one-out | constant |
|---|---|---|---|---|---|---|---|---|---|---|---|
| minigrid | macro | primary | I1 | 83 | 61 | 0.8666 | 0.5101 | 0.6218 | 0.8413 | 0.7757 |  |
| minigrid | macro | primary | N | 112 | 100 | 0.7262 | 0.3850 | 0.5312 | 0.8725 | 0.8217 |  |
| minigrid | macro | primary | R | 112 | 101 | 0.7840 | 0.4239 | 0.5653 | 0.8515 | 0.7912 |  |
| minigrid | macro | primary, D9b included | I1 | 112 | 61 | 0.8454 | 0.5230 | 0.4789 | 0.8734 | 0.8422 |  |
| minigrid | macro | all games | I1 | 161 | 61 | 0.6918 | 0.5278 | 0.4618 | 0.7562 | 0.7320 |  |
| minigrid | macro | all games | N | 161 | 100 | 0.4484 | 0.4854 | 0.4441 | 0.5752 | 0.5092 |  |
| minigrid | macro | all games | R | 161 | 101 | 0.4578 | 0.4982 | 0.4525 | 0.5589 | 0.4620 |  |
| minigrid | raw | primary | I1 | 98 | 71 | 0.8498 | 0.5097 | 0.6390 | 0.8534 | 0.7606 |  |
| minigrid | raw | primary | N | 155 | 130 | 0.6817 | 0.4954 | 0.5177 | 0.6202 | 0.5025 |  |
| minigrid | raw | primary | R | 155 | 126 | 0.6890 | 0.4986 | 0.5112 | 0.6561 | 0.5569 |  |
| minigrid | raw | primary, D9b included | I1 | 155 | 71 | 0.7884 | 0.5222 | 0.4623 | 0.8184 | 0.7976 |  |
| minigrid | raw | all games | I1 | 161 | 71 | 0.7631 | 0.5226 | 0.4557 | 0.8086 | 0.7879 |  |
| minigrid | raw | all games | N | 161 | 130 | 0.6112 | 0.4993 | 0.4764 | 0.6036 | 0.4973 |  |
| minigrid | raw | all games | R | 161 | 126 | 0.6265 | 0.5016 | 0.4755 | 0.6472 | 0.5592 |  |
| procgen | center_off | all | I1 | 14 | 6 | 0.5000 | 0.5000 | 0.4896 | 0.5104 | 0.0000 | area, actions |
| procgen | center_off | all | N | 14 | 9 | 0.5000 | 0.5000 | 0.4333 | 0.5667 | 0.2667 | area, actions |
| procgen | center_off | all | R | 14 | 9 | 0.5000 | 0.5000 | 0.4333 | 0.5667 | 0.2667 | area, actions |
| procgen | center_off | in_range | I1 | 9 | 4 | 0.5000 | 0.5000 | 0.5250 | 0.4750 | 0.0000 | area, actions |
| procgen | center_off | in_range | N | 9 | 5 | 0.5000 | 0.5000 | 0.7000 | 0.7000 | 0.0000 | area, actions |
| procgen | center_off | in_range | R | 9 | 5 | 0.5000 | 0.5000 | 0.7000 | 0.7000 | 0.0000 | area, actions |

## Table 2. The censoring flag alone

*EXPLORATORY.* A game is flagged when more than half of N's seeds ("majority") or at least one of N's seeds ("any") never ended level 1 within the 20,000-action budget. "separates" = the flagged games are exactly the non-completing games of the line's agent.

| suite | condition | subset | agent | n | pos | majority flagged | majority separates | majority AUROC | any flagged | any separates | any AUROC |
|---|---|---|---|---|---|---|---|---|---|---|---|
| minigrid | macro | primary | I1 | 83 | 61 | 7 | no | 0.5972 | 23 | no | 0.8372 |
| minigrid | macro | primary | N | 112 | 100 | 12 | yes | 1.0000 | 30 | no | 0.9100 |
| minigrid | macro | primary | R | 112 | 101 | 12 | no | 0.9950 | 30 | no | 0.9059 |
| minigrid | macro | primary, D9b included | I1 | 112 | 61 | 12 | no | 0.5816 | 30 | no | 0.6861 |
| minigrid | macro | all games | I1 | 161 | 61 | 61 | no | 0.7786 | 79 | no | 0.8158 |
| minigrid | macro | all games | N | 161 | 100 | 61 | yes | 1.0000 | 79 | no | 0.9100 |
| minigrid | macro | all games | R | 161 | 101 | 61 | no | 0.9950 | 79 | no | 0.9059 |
| minigrid | raw | primary | I1 | 98 | 71 | 6 | no | 0.5856 | 32 | no | 0.8881 |
| minigrid | raw | primary | N | 155 | 130 | 25 | yes | 1.0000 | 62 | no | 0.8577 |
| minigrid | raw | primary | R | 155 | 126 | 25 | no | 0.9098 | 62 | no | 0.8690 |
| minigrid | raw | primary, D9b included | I1 | 155 | 71 | 25 | no | 0.6358 | 62 | no | 0.7651 |
| minigrid | raw | all games | I1 | 161 | 71 | 31 | no | 0.6596 | 68 | no | 0.7770 |
| minigrid | raw | all games | N | 161 | 130 | 31 | yes | 1.0000 | 68 | no | 0.8577 |
| minigrid | raw | all games | R | 161 | 126 | 31 | no | 0.9246 | 68 | no | 0.8690 |
| procgen | center_off | all | I1 | 14 | 6 | 5 | no | 0.8125 | 7 | no | 0.7917 |
| procgen | center_off | all | N | 14 | 9 | 5 | yes | 1.0000 | 7 | no | 0.8889 |
| procgen | center_off | all | R | 14 | 9 | 5 | yes | 1.0000 | 7 | no | 0.8889 |
| procgen | center_off | in_range | I1 | 9 | 4 | 4 | no | 0.9000 | 5 | no | 0.7750 |
| procgen | center_off | in_range | N | 9 | 5 | 4 | yes | 1.0000 | 5 | no | 0.9000 |
| procgen | center_off | in_range | R | 9 | 5 | 4 | yes | 1.0000 | 5 | no | 0.9000 |

## Table 3. Every feature and model at AUROC 1.0000

*EXPLORATORY.* Values of the completing and the non-completing games (every value up to 20 games, else a summary; all values in saturation.json). Features: raw values, a smaller value predicting completion. Models: fitted probabilities, a larger one predicting completion. Overlap: completing games inside the non-completing range / non-completing games inside the completing range. Gap: distance between the two ranges in the predicting direction (positive = no overlap). "at budget": non-completing games whose median N actions is the 20,000-action budget, i.e. the censoring value.

| suite | condition | subset | agent | item | completing | not completing | overlap | gap | at budget |
|---|---|---|---|---|---|---|---|---|---|
| minigrid | macro | primary | N | N_actions | n 100: min 4.0000, median 316.7500, max 18124.0 | 20000.0, 20000.0, 20000.0, 20000.0, 20000.0, 20000.0, 20000.0, 20000.0, 20000.0, 20000.0, 20000.0, 20000.0 | 0 / 0 | 1876.0 | 12 of 12 |
| minigrid | macro | primary | N | Nsearch in-sample | n 100: min 0.9998, median 1.0000, max 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 0.9997 |  |
| minigrid | macro | primary | N | Nsearch leave-one-out | n 100: min 0.0052, median 1.0000, max 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 0.0052 |  |
| minigrid | macro | primary | N | search5 in-sample | n 100: min 0.9998, median 1.0000, max 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0001, 0.0001 | 0 / 0 | 0.9997 |  |
| minigrid | macro | primary | R | Nsearch in-sample | n 101: min 0.3826, median 1.0000, max 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0485, 0.0485, 0.1839, 0.3389 | 0 / 0 | 0.0437 |  |
| minigrid | macro | primary | R | search5 in-sample | n 101: min 0.9970, median 1.0000, max 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0001, 0.0001, 0.0004, 0.0030 | 0 / 0 | 0.9940 |  |
| minigrid | macro | all games | N | N_actions | n 100: min 4.0000, median 316.7500, max 18124.0 | n 61: min 20000.0, median 20000.0, max 20000.0 | 0 / 0 | 1876.0 | 61 of 61 |
| minigrid | macro | all games | N | Nsearch in-sample | n 100: min 0.9995, median 1.0000, max 1.0000 | n 61: min 0.0000, median 0.0000, max 0.0000 | 0 / 0 | 0.9995 |  |
| minigrid | macro | all games | N | Nsearch leave-one-out | n 100: min 0.0026, median 1.0000, max 1.0000 | n 61: min 0.0000, median 0.0000, max 0.0000 | 0 / 0 | 0.0025 |  |
| minigrid | macro | all games | N | search5 in-sample | n 100: min 0.9996, median 1.0000, max 1.0000 | n 61: min 0.0000, median 0.0000, max 0.0002 | 0 / 0 | 0.9994 |  |
| minigrid | macro | all games | R | Nsearch in-sample | n 101: min 0.2606, median 1.0000, max 1.0000 | n 60: min 0.0000, median 0.0000, max 0.2294 | 0 / 0 | 0.0312 |  |
| minigrid | macro | all games | R | search5 in-sample | n 101: min 0.9603, median 1.0000, max 1.0000 | n 60: min 0.0000, median 0.0000, max 0.0397 | 0 / 0 | 0.9207 |  |
| minigrid | raw | primary | N | N_actions | n 130: min 48.0000, median 599.2500, max 19958.0 | n 25: min 20000.0, median 20000.0, max 20000.0 | 0 / 0 | 42.0000 | 25 of 25 |
| minigrid | raw | primary | N | Nsearch in-sample | n 130: min 0.8135, median 1.0000, max 1.0000 | n 25: min 0.0001, median 0.0029, max 0.0557 | 0 / 0 | 0.7577 |  |
| minigrid | raw | primary | N | search5 in-sample | n 130: min 0.8184, median 1.0000, max 1.0000 | n 25: min 0.0000, median 0.0015, max 0.0521 | 0 / 0 | 0.7663 |  |
| minigrid | raw | all games | N | N_actions | n 130: min 48.0000, median 599.2500, max 19958.0 | n 31: min 20000.0, median 20000.0, max 20000.0 | 0 / 0 | 42.0000 | 31 of 31 |
| minigrid | raw | all games | N | Nsearch in-sample | n 130: min 0.8013, median 1.0000, max 1.0000 | n 31: min 0.0001, median 0.0028, max 0.0604 | 0 / 0 | 0.7408 |  |
| minigrid | raw | all games | N | search5 in-sample | n 130: min 0.8066, median 1.0000, max 1.0000 | n 31: min 0.0000, median 0.0014, max 0.0562 | 0 / 0 | 0.7504 |  |
| procgen | center_off | all | N | N_actions | 42.0000, 110.0000, 901.5000, 1033.0, 1187.0, 1401.5, 6605.0, 8303.5, 9660.0 | 20000.0, 20000.0, 20000.0, 20000.0, 20000.0 | 0 / 0 | 10340.0 | 5 of 5 |
| procgen | center_off | all | N | Nsearch in-sample | 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 1.0000 |  |
| procgen | center_off | all | N | Nsearch leave-one-out | 0.9999, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.1763 | 0 / 0 | 0.8237 |  |
| procgen | center_off | all | N | search5 in-sample | 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 1.0000 |  |
| procgen | center_off | all | N | search5 leave-one-out | 0.4469, 0.9939, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.3518 | 0 / 0 | 0.0951 |  |
| procgen | center_off | all | R | N_actions | 42.0000, 110.0000, 901.5000, 1033.0, 1187.0, 1401.5, 6605.0, 8303.5, 9660.0 | 20000.0, 20000.0, 20000.0, 20000.0, 20000.0 | 0 / 0 | 10340.0 | 5 of 5 |
| procgen | center_off | all | R | Nsearch in-sample | 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 1.0000 |  |
| procgen | center_off | all | R | Nsearch leave-one-out | 0.9999, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.1763 | 0 / 0 | 0.8237 |  |
| procgen | center_off | all | R | search5 in-sample | 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 1.0000 |  |
| procgen | center_off | all | R | search5 leave-one-out | 0.4458, 0.9939, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.3499 | 0 / 0 | 0.0959 |  |
| procgen | center_off | in_range | I1 | N_actions | 42.0000, 110.0000, 901.5000, 8303.5 | 9660.0, 20000.0, 20000.0, 20000.0, 20000.0 | 0 / 0 | 1356.5 | 4 of 5 |
| procgen | center_off | in_range | I1 | Nsearch in-sample | 0.9999, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.0001 | 0 / 0 | 0.9998 |  |
| procgen | center_off | in_range | I1 | search5 in-sample | 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 1.0000 |  |
| procgen | center_off | in_range | N | N_states | 16.0000, 35.0000, 342.0000, 3844.0, 7901.5 | 17138.5, 19554.5, 19604.0, 19688.0 | 0 / 0 | 9237.0 |  |
| procgen | center_off | in_range | N | N_actions | 42.0000, 110.0000, 901.5000, 8303.5, 9660.0 | 20000.0, 20000.0, 20000.0, 20000.0 | 0 / 0 | 10340.0 | 4 of 4 |
| procgen | center_off | in_range | N | Nsearch in-sample | 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 1.0000 |  |
| procgen | center_off | in_range | N | Nsearch leave-one-out | 0.9998, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 0.9998 |  |
| procgen | center_off | in_range | N | search5 in-sample | 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 1.0000 |  |
| procgen | center_off | in_range | R | N_states | 16.0000, 35.0000, 342.0000, 3844.0, 7901.5 | 17138.5, 19554.5, 19604.0, 19688.0 | 0 / 0 | 9237.0 |  |
| procgen | center_off | in_range | R | N_actions | 42.0000, 110.0000, 901.5000, 8303.5, 9660.0 | 20000.0, 20000.0, 20000.0, 20000.0 | 0 / 0 | 10340.0 | 4 of 4 |
| procgen | center_off | in_range | R | Nsearch in-sample | 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 1.0000 |  |
| procgen | center_off | in_range | R | Nsearch leave-one-out | 0.9998, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 0.9998 |  |
| procgen | center_off | in_range | R | search5 in-sample | 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 | 0.0000, 0.0000, 0.0000, 0.0000 | 0 / 0 | 1.0000 |  |

