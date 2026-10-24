# Oracle test (EXPLORATORY)

**EXPLORATORY.** Written by scripts/oracle_v2.py from the committed rows and truth tables of study 1 (read-only). Nothing here is registered, nothing here is a claim, and no verdict word below is a registered verdict: where a column says what the study-1 V2 rule would print, it applies a rule registered for study 1's census to a different score, after study 1's outcome was known.

## Inputs and checks

*EXPLORATORY.*
- blob scripts/analyze_common.py: caad22731807db78aff9c92c993a79a63f042ec3 (registered at study-1 prereg-v1.1: caad22731807db78aff9c92c993a79a63f042ec3) match
- blob scripts/analyze_v2.py: 90a849c44e47addd8efdbfa579efdb16288edd50 (registered at study-1 prereg-v1.1: 90a849c44e47addd8efdbfa579efdb16288edd50) match
- truth tables: minigrid 178 ids, 161 confirmatory; procgen 16 games, 14 confirmatory; unparsed truth entries 0
- rows: 10500 files, 10080 confirmatory rows kept, 420 pilot rows skipped
- rows minigrid macro I1: 1610
- rows minigrid macro N: 1610
- rows minigrid macro R: 1610
- rows minigrid raw I1: 1610
- rows minigrid raw N: 1610
- rows minigrid raw R: 1610
- rows procgen center_off I1: 140
- rows procgen center_off N: 140
- rows procgen center_off R: 140
- rows with an error field: 0
- rows short of their budget: 0
- reproduction of study-1 census lines: 20 of 20 identical to docs/tables/v2.json
- bootstrap loop reproduces bootstrap_auroc_ci: 20 of 20 lines
- logistic refit reproduces logistic_fit_predict for B: 20 of 20 lines

## Table 1. Study-1 V2 with the census and with the oracle

*EXPLORATORY.* Census columns: recomputed by study 1's analyze_v2 functions; "v2.json" says whether they equal docs/tables/v2.json of study 1 to four decimals. Oracle columns: the same functions with the truth-table vector A1 to A5. AUROC_B is the study-1 nuisance baseline; it does not depend on the mechanics vector, so it is the same in both. "rule" is the verdict the study-1 V2 rule prints.

| suite | condition | subset | agent | role | n | pos | census AUROC | census CI | census BA | census rule | v2.json | oracle AUROC | oracle CI | oracle BA | oracle rule | AUROC_B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| minigrid | macro | primary | I1 | evidence | 83 | 61 | 0.7187 | [0.5902, 0.8298] | 0.5838 | neither | same | 0.6967 | [0.6356, 0.7583] | 0.6967 | neither | 0.8413 |
| minigrid | macro | primary | N | instrument check | 112 | 100 | 0.6613 | [0.5049, 0.7941] | 0.5700 | neither | same | 0.5617 | [0.4289, 0.6667] | 0.5617 | FAIL | 0.8725 |
| minigrid | macro | primary | R | evidence | 112 | 101 | 0.6985 |  | 0.5693 | VOID | same | 0.5527 |  | 0.5527 | VOID | 0.8515 |
| minigrid | macro | primary, D9b included | I1 | evidence | 112 | 61 | 0.7719 | [0.6840, 0.8529] | 0.5968 | reported, not tested | same | 0.6281 | [0.5507, 0.7030] | 0.6281 | reported, not tested | 0.8734 |
| minigrid | macro | all games | I1 | evidence | 161 | 61 | 0.7517 | [0.6764, 0.8223] | 0.6016 | reported, not tested | same | 0.6617 | [0.5974, 0.7266] | 0.6617 | reported, not tested | 0.7562 |
| minigrid | macro | all games | N | instrument check | 161 | 100 | 0.6352 | [0.5514, 0.7114] | 0.5700 | reported, not tested | same | 0.6286 | [0.5811, 0.6764] | 0.6286 | reported, not tested | 0.5752 |
| minigrid | macro | all games | R | evidence | 161 | 101 | 0.6434 | [0.5609, 0.7208] | 0.5693 | reported, not tested | same | 0.6269 | [0.5789, 0.6751] | 0.6269 | reported, not tested | 0.5589 |
| minigrid | raw | primary | I1 | evidence | 98 | 71 | 0.5370 | [0.4324, 0.6410] | 0.5070 | FAIL | same | 0.6690 | [0.6119, 0.7244] | 0.5000 | neither | 0.8534 |
| minigrid | raw | primary | N | instrument check | 155 | 130 | 0.5255 | [0.4320, 0.6156] | 0.5038 | FAIL | same | 0.5477 | [0.4677, 0.6143] | 0.5000 | FAIL | 0.6202 |
| minigrid | raw | primary | R | evidence | 155 | 126 | 0.5224 | [0.4330, 0.6096] | 0.5040 | FAIL | same | 0.5594 | [0.4843, 0.6203] | 0.5000 | FAIL | 0.6561 |
| minigrid | raw | primary, D9b included | I1 | evidence | 155 | 71 | 0.6258 | [0.5405, 0.7065] | 0.5070 | reported, not tested | same | 0.6273 | [0.5632, 0.6894] | 0.5000 | reported, not tested | 0.8184 |
| minigrid | raw | all games | I1 | evidence | 161 | 71 | 0.6069 | [0.5235, 0.6926] | 0.5070 | reported, not tested | same | 0.6301 | [0.5694, 0.6905] | 0.5000 | reported, not tested | 0.8086 |
| minigrid | raw | all games | N | instrument check | 161 | 130 | 0.4772 | [0.3829, 0.5696] | 0.5038 | reported, not tested | same | 0.5593 | [0.4907, 0.6192] | 0.5000 | reported, not tested | 0.6036 |
| minigrid | raw | all games | R | evidence | 161 | 126 | 0.4805 | [0.3919, 0.5687] | 0.5040 | reported, not tested | same | 0.5683 | [0.5033, 0.6264] | 0.5000 | reported, not tested | 0.6472 |
| procgen | center_off | all | I1 | evidence | 14 | 6 | 0.6458 | [0.3333, 0.9445] | 0.5000 | FAIL | same | 0.7917 | [0.5222, 1.0000] | 0.5833 | neither | 0.5104 |
| procgen | center_off | all | N | instrument check | 14 | 9 | 0.7222 | [0.5000, 0.9333] | 0.5000 | neither | same | 0.7556 | [0.5000, 0.9583] | 0.5556 | neither | 0.5667 |
| procgen | center_off | all | R | evidence | 14 | 9 | 0.7222 | [0.5000, 0.9333] | 0.5000 | neither | same | 0.7556 | [0.5000, 0.9583] | 0.5556 | neither | 0.5667 |
| procgen | center_off | in_range | I1 | evidence | 9 | 4 | 0.8750 | [0.5000, 1.0000] | 0.5000 | neither | same | 0.8250 | [0.4375, 1.0000] | 0.6250 | neither | 0.4750 |
| procgen | center_off | in_range | N | instrument check | 9 | 5 | 0.8000 | [0.5000, 1.0000] | 0.5000 | neither | same | 0.7250 | [0.3750, 1.0000] | 0.6000 | neither | 0.7000 |
| procgen | center_off | in_range | R | evidence | 9 | 5 | 0.8000 | [0.5000, 1.0000] | 0.5000 | neither | same | 0.7250 | [0.3750, 1.0000] | 0.6000 | neither | 0.7000 |

Suite lines that the study-1 rule would print for the oracle (EXPLORATORY):

- minigrid macro primary: not failed (decided by I1 alone)
- minigrid macro primary, D9b included: reported, not tested
- minigrid macro all games: reported, not tested
- minigrid raw primary: not failed (decided by R and I1)
- minigrid raw primary, D9b included: reported, not tested
- minigrid raw all games: reported, not tested
- procgen center_off all: not failed (decided by R and I1)
- procgen center_off in_range: not failed (decided by R and I1)

## Table 2. One-feature search scores

*EXPLORATORY.* AUROC of each feature, negated (a larger search predicts no completion), with its 95% bootstrap interval; the intervals are computed on every line, void or not, on the same resamples as the oracle. N states and N actions are taken from N's rows, whatever the line's agent; on N's own lines they describe the same runs as the outcome and are circular. An AUROC below 0.5 means the feature runs the other way.

| suite | condition | subset | agent | n | oracle AUROC | area | actions | colours | N_states | N_actions |
|---|---|---|---|---|---|---|---|---|---|---|
| minigrid | macro | primary | I1 | 83 | 0.6967 [0.6356, 0.7583] | 0.8666 [0.7711, 0.9380] | 0.5101 [0.4486, 0.5593] | 0.6218 [0.4953, 0.7423] | 0.8826 [0.7747, 0.9674] | 0.8674 [0.7649, 0.9449] |
| minigrid | macro | primary | N | 112 | 0.5617 [0.4289, 0.6667] | 0.7262 [0.5501, 0.8663] | 0.3850 [0.2405, 0.5101] | 0.5312 [0.3371, 0.7044] | 0.6925 [0.4544, 0.9050] | 1.0000 [1.0000, 1.0000] |
| minigrid | macro | primary | R | 112 | 0.5527 [0.4122, 0.6636] | 0.7840 [0.6538, 0.8942] | 0.4239 [0.2904, 0.5207] | 0.5653 [0.3714, 0.7457] | 0.7511 [0.5207, 0.9478] | 0.9950 [0.9844, 1.0000] |
| minigrid | macro | primary, D9b included | I1 | 112 | 0.6281 [0.5507, 0.7030] | 0.8454 [0.7635, 0.9152] | 0.5230 [0.4872, 0.5606] | 0.4789 [0.3664, 0.5848] | 0.8531 [0.7723, 0.9162] | 0.8145 [0.7296, 0.8857] |
| minigrid | macro | all games | I1 | 161 | 0.6617 [0.5974, 0.7266] | 0.6918 [0.6065, 0.7717] | 0.5278 [0.4992, 0.5629] | 0.4618 [0.3608, 0.5650] | 0.8865 [0.8312, 0.9335] | 0.8974 [0.8455, 0.9418] |
| minigrid | macro | all games | N | 161 | 0.6286 [0.5811, 0.6764] | 0.4484 [0.3625, 0.5363] | 0.4854 [0.4522, 0.5138] | 0.4441 [0.3561, 0.5293] | 0.7974 [0.7192, 0.8638] | 1.0000 [1.0000, 1.0000] |
| minigrid | macro | all games | R | 161 | 0.6269 [0.5789, 0.6751] | 0.4578 [0.3717, 0.5441] | 0.4982 [0.4674, 0.5253] | 0.4525 [0.3640, 0.5388] | 0.8113 [0.7387, 0.8747] | 0.9950 [0.9845, 1.0000] |
| minigrid | raw | primary | I1 | 98 | 0.6690 [0.6119, 0.7244] | 0.8498 [0.7507, 0.9294] | 0.5097 [0.4607, 0.5493] | 0.6390 [0.5146, 0.7593] | 0.8472 [0.7494, 0.9281] | 0.8558 [0.7646, 0.9304] |
| minigrid | raw | primary | N | 155 | 0.5477 [0.4677, 0.6143] | 0.6817 [0.5934, 0.7684] | 0.4954 [0.4499, 0.5269] | 0.5177 [0.4177, 0.6291] | 0.9068 [0.8265, 0.9690] | 1.0000 [1.0000, 1.0000] |
| minigrid | raw | primary | R | 155 | 0.5594 [0.4843, 0.6203] | 0.6890 [0.5941, 0.7724] | 0.4986 [0.4586, 0.5278] | 0.5112 [0.4141, 0.6087] | 0.9193 [0.8515, 0.9737] | 0.9880 [0.9702, 1.0000] |
| minigrid | raw | primary, D9b included | I1 | 155 | 0.6273 [0.5632, 0.6894] | 0.7884 [0.7161, 0.8595] | 0.5222 [0.4963, 0.5526] | 0.4623 [0.3660, 0.5585] | 0.8460 [0.7797, 0.9062] | 0.8536 [0.7924, 0.9093] |
| minigrid | raw | all games | I1 | 161 | 0.6301 [0.5694, 0.6905] | 0.7631 [0.6875, 0.8348] | 0.5226 [0.4959, 0.5540] | 0.4557 [0.3600, 0.5498] | 0.8385 [0.7716, 0.8976] | 0.8629 [0.8032, 0.9154] |
| minigrid | raw | all games | N | 161 | 0.5593 [0.4907, 0.6192] | 0.6112 [0.5086, 0.7091] | 0.4993 [0.4615, 0.5261] | 0.4764 [0.3797, 0.5759] | 0.8498 [0.7558, 0.9291] | 1.0000 [1.0000, 1.0000] |
| minigrid | raw | all games | R | 161 | 0.5683 [0.5033, 0.6264] | 0.6265 [0.5299, 0.7208] | 0.5016 [0.4663, 0.5271] | 0.4755 [0.3832, 0.5720] | 0.8686 [0.7838, 0.9407] | 0.9893 [0.9721, 1.0000] |
| procgen | center_off | all | I1 | 14 | 0.7917 [0.5222, 1.0000] | 0.5000 [0.5000, 0.5000] | 0.5000 [0.5000, 0.5000] | 0.4896 [0.1500, 0.8574] | 0.8750 [0.6250, 1.0000] | 0.9167 [0.7143, 1.0000] |
| procgen | center_off | all | N | 14 | 0.7556 [0.5000, 0.9583] | 0.5000 [0.5000, 0.5000] | 0.5000 [0.5000, 0.5000] | 0.4333 [0.1250, 0.7500] | 0.9778 [0.8750, 1.0000] | 1.0000 [1.0000, 1.0000] |
| procgen | center_off | all | R | 14 | 0.7556 [0.5000, 0.9583] | 0.5000 [0.5000, 0.5000] | 0.5000 [0.5000, 0.5000] | 0.4333 [0.1250, 0.7500] | 0.9778 [0.8750, 1.0000] | 1.0000 [1.0000, 1.0000] |
| procgen | center_off | in_range | I1 | 9 | 0.8250 [0.4375, 1.0000] | 0.5000 [0.5000, 0.5000] | 0.5000 [0.5000, 0.5000] | 0.5250 [0.0000, 1.0000] | 0.9500 [0.7143, 1.0000] | 1.0000 [1.0000, 1.0000] |
| procgen | center_off | in_range | N | 9 | 0.7250 [0.3750, 1.0000] | 0.5000 [0.5000, 0.5000] | 0.5000 [0.5000, 0.5000] | 0.7000 [0.2778, 1.0000] | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] |
| procgen | center_off | in_range | R | 9 | 0.7250 [0.3750, 1.0000] | 0.5000 [0.5000, 0.5000] | 0.5000 [0.5000, 0.5000] | 0.7000 [0.2778, 1.0000] | 1.0000 [1.0000, 1.0000] | 1.0000 [1.0000, 1.0000] |

## Table 3. Paired difference, feature minus oracle

*EXPLORATORY.* AUROC(feature) minus AUROC(oracle S) on the same games, with the 95% percentile interval of the difference over the same 2,000 resamples.

| suite | condition | subset | agent | area | actions | colours | N_states | N_actions |
|---|---|---|---|---|---|---|---|---|
| minigrid | macro | primary | I1 | 0.1699 [0.0632, 0.2648] | -0.1867 [-0.2755, -0.1041] | -0.0749 [-0.1824, 0.0274] | 0.1859 [0.0559, 0.2906] | 0.1706 [0.0511, 0.2706] |
| minigrid | macro | primary | N | 0.1646 [-0.0653, 0.3842] | -0.1767 [-0.3775, 0.0261] | -0.0304 [-0.2724, 0.2113] | 0.1308 [-0.1674, 0.4226] | 0.4383 [0.3333, 0.5711] |
| minigrid | macro | primary | R | 0.2313 [0.0405, 0.4245] | -0.1287 [-0.3309, 0.0661] | 0.0126 [-0.2392, 0.2469] | 0.1985 [-0.1034, 0.4725] | 0.4424 [0.3316, 0.5832] |
| minigrid | macro | primary, D9b included | I1 | 0.2173 [0.1191, 0.3113] | -0.1051 [-0.1927, -0.0134] | -0.1491 [-0.2557, -0.0536] | 0.2250 [0.1185, 0.3244] | 0.1864 [0.0761, 0.2911] |
| minigrid | macro | all games | I1 | 0.0301 [-0.0757, 0.1361] | -0.1339 [-0.2111, -0.0579] | -0.1999 [-0.2832, -0.1116] | 0.2248 [0.1408, 0.3063] | 0.2357 [0.1550, 0.3122] |
| minigrid | macro | all games | N | -0.1802 [-0.2821, -0.0793] | -0.1432 [-0.2015, -0.0857] | -0.1845 [-0.2686, -0.1000] | 0.1688 [0.0799, 0.2514] | 0.3714 [0.3236, 0.4189] |
| minigrid | macro | all games | R | -0.1691 [-0.2715, -0.0674] | -0.1287 [-0.1883, -0.0686] | -0.1744 [-0.2569, -0.0918] | 0.1844 [0.0979, 0.2657] | 0.3682 [0.3198, 0.4158] |
| minigrid | raw | primary | I1 | 0.1808 [0.0688, 0.2797] | -0.1594 [-0.2376, -0.0890] | -0.0300 [-0.1462, 0.0858] | 0.1781 [0.0704, 0.2723] | 0.1868 [0.0814, 0.2770] |
| minigrid | raw | primary | N | 0.1340 [0.0137, 0.2672] | -0.0523 [-0.1392, 0.0408] | -0.0300 [-0.1411, 0.0894] | 0.3591 [0.2514, 0.4605] | 0.4523 [0.3857, 0.5323] |
| minigrid | raw | primary | R | 0.1296 [0.0142, 0.2487] | -0.0608 [-0.1381, 0.0206] | -0.0482 [-0.1541, 0.0596] | 0.3599 [0.2712, 0.4512] | 0.4286 [0.3659, 0.5046] |
| minigrid | raw | primary, D9b included | I1 | 0.1610 [0.0608, 0.2593] | -0.1051 [-0.1768, -0.0318] | -0.1651 [-0.2475, -0.0833] | 0.2186 [0.1397, 0.2998] | 0.2263 [0.1463, 0.3074] |
| minigrid | raw | all games | I1 | 0.1329 [0.0383, 0.2348] | -0.1075 [-0.1797, -0.0379] | -0.1744 [-0.2548, -0.0915] | 0.2084 [0.1252, 0.2885] | 0.2328 [0.1557, 0.3102] |
| minigrid | raw | all games | N | 0.0519 [-0.0853, 0.1828] | -0.0600 [-0.1363, 0.0163] | -0.0829 [-0.1914, 0.0338] | 0.2904 [0.1746, 0.4069] | 0.4407 [0.3808, 0.5093] |
| minigrid | raw | all games | R | 0.0583 [-0.0631, 0.1786] | -0.0667 [-0.1366, 0.0045] | -0.0927 [-0.1943, 0.0117] | 0.3003 [0.1923, 0.4064] | 0.4211 [0.3596, 0.4870] |
| procgen | center_off | all | I1 | -0.2917 [-0.5000, -0.0222] | -0.2917 [-0.5000, -0.0222] | -0.3021 [-0.6354, -0.0208] | 0.0833 [-0.0833, 0.2728] | 0.1250 [-0.0750, 0.3542] |
| procgen | center_off | all | N | -0.2556 [-0.4583, 0.0000] | -0.2556 [-0.4583, 0.0000] | -0.3222 [-0.6639, 0.0208] | 0.2222 [0.0417, 0.4583] | 0.2444 [0.0417, 0.5000] |
| procgen | center_off | all | R | -0.2556 [-0.4583, 0.0000] | -0.2556 [-0.4583, 0.0000] | -0.3222 [-0.6639, 0.0208] | 0.2222 [0.0417, 0.4583] | 0.2444 [0.0417, 0.5000] |
| procgen | center_off | in_range | I1 | -0.3250 [-0.5000, 0.0625] | -0.3250 [-0.5000, 0.0625] | -0.3000 [-0.6250, 0.0000] | 0.1250 [0.0000, 0.4444] | 0.1750 [0.0000, 0.5625] |
| procgen | center_off | in_range | N | -0.2250 [-0.5000, 0.1250] | -0.2250 [-0.5000, 0.1250] | -0.0250 [-0.3229, 0.3500] | 0.2750 [0.0000, 0.6250] | 0.2750 [0.0000, 0.6250] |
| procgen | center_off | in_range | R | -0.2250 [-0.5000, 0.1250] | -0.2250 [-0.5000, 0.1250] | -0.0250 [-0.3229, 0.3500] | 0.2750 [0.0000, 0.6250] | 0.2750 [0.0000, 0.6250] |

## Table 4. Logistic models, in-sample and leave-one-game-out

*EXPLORATORY.* AUROC of the fitted probabilities. In-sample values favour models with more features; the leave-one-game-out values do not. B = area, actions, colours; Nsearch = N states, N actions; search5 = all five; oracle = A1 to A5 as 0/1 (constant columns dropped).

| suite | condition | subset | agent | n | B in | Nsearch in | search5 in | oracle in | B loo | Nsearch loo | search5 loo | oracle loo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| minigrid | macro | primary | I1 | 83 | 0.8413 | 0.8927 | 0.9001 | 0.7157 | 0.7757 | 0.8234 | 0.8174 | 0.4382 |
| minigrid | macro | primary | N | 112 | 0.8725 | 1.0000 | 1.0000 | 0.6421 | 0.8217 | 1.0000 | 0.9992 | 0.4142 |
| minigrid | macro | primary | R | 112 | 0.8515 | 1.0000 | 1.0000 | 0.6053 | 0.7912 | 0.9865 | 0.9428 | 0.3591 |
| minigrid | macro | primary, D9b included | I1 | 112 | 0.8734 | 0.8447 | 0.8994 | 0.6517 | 0.8422 | 0.7946 | 0.8637 | 0.3870 |
| minigrid | macro | all games | I1 | 161 | 0.7562 | 0.9148 | 0.9485 | 0.6898 | 0.7320 | 0.8834 | 0.9308 | 0.4223 |
| minigrid | macro | all games | N | 161 | 0.5752 | 1.0000 | 1.0000 | 0.6364 | 0.5092 | 1.0000 | 0.9995 | 0.3144 |
| minigrid | macro | all games | R | 161 | 0.5589 | 1.0000 | 1.0000 | 0.6294 | 0.4620 | 0.9875 | 0.9891 | 0.2776 |
| minigrid | raw | primary | I1 | 98 | 0.8534 | 0.8623 | 0.8665 | 0.6849 | 0.7606 | 0.7626 | 0.7642 | 0.3798 |
| minigrid | raw | primary | N | 155 | 0.6202 | 1.0000 | 1.0000 | 0.5498 | 0.5025 | 0.9929 | 0.9923 | 0.1809 |
| minigrid | raw | primary | R | 155 | 0.6561 | 0.9907 | 0.9915 | 0.5602 | 0.5569 | 0.9606 | 0.9581 | 0.1916 |
| minigrid | raw | primary, D9b included | I1 | 155 | 0.8184 | 0.8494 | 0.9002 | 0.6499 | 0.7976 | 0.7936 | 0.8665 | 0.3568 |
| minigrid | raw | all games | I1 | 161 | 0.8086 | 0.8593 | 0.9069 | 0.6531 | 0.7879 | 0.8074 | 0.8754 | 0.3593 |
| minigrid | raw | all games | N | 161 | 0.6036 | 1.0000 | 1.0000 | 0.5605 | 0.4973 | 0.9935 | 0.9931 | 0.1876 |
| minigrid | raw | all games | R | 161 | 0.6472 | 0.9914 | 0.9930 | 0.5717 | 0.5592 | 0.9673 | 0.9651 | 0.1968 |
| procgen | center_off | all | I1 | 14 | 0.5104 | 0.9375 | 0.9375 | 0.8021 | 0.0000 | 0.8542 | 0.7292 | 0.4167 |
| procgen | center_off | all | N | 14 | 0.5667 | 1.0000 | 1.0000 | 0.8333 | 0.2667 | 1.0000 | 1.0000 | 0.5333 |
| procgen | center_off | all | R | 14 | 0.5667 | 1.0000 | 1.0000 | 0.8333 | 0.2667 | 1.0000 | 1.0000 | 0.5333 |
| procgen | center_off | in_range | I1 | 9 | 0.4750 | 1.0000 | 1.0000 | 0.8500 | 0.0000 | 0.9000 | 0.9500 | 0.4500 |
| procgen | center_off | in_range | N | 9 | 0.7000 | 1.0000 | 1.0000 | 0.8500 | 0.0000 | 1.0000 | 0.9500 | 0.5000 |
| procgen | center_off | in_range | R | 9 | 0.7000 | 1.0000 | 1.0000 | 0.8500 | 0.0000 | 1.0000 | 0.9500 | 0.5000 |

## Table 5. What the oracle vector looks like

*EXPLORATORY.* Per suite and condition, over the confirmatory games: how many games have each oracle score S, and how many have P (A2, A3, A4 and A5 all hold).

- minigrid raw: S counts {3: 130, 4: 31}; P holds on 0 of 161
- minigrid macro: S counts {4: 130, 5: 31}; P holds on 31 of 161
- procgen center_off: S counts {2: 5, 3: 6, 4: 2, 5: 1}; P holds on 1 of 14

Per-game values for every line (truth vector, scores, outcome, features, censored seeds) are in docs/oracle/oracle_v2.json, key "lines" -> "per_game".
