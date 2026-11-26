# Wavelength-arbitration production statistics

Scene: `EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc` (1280x1242)
Method: production rf.json (all windows) vs the same rules with every `absorption_center_range` stripped (pure argmax MICA); every NUM diff is a production flip by `_reassign_by_absorption_center`.
Runtime: windowed 358.7s, pure-argmax 251.9s (n_workers=4; wall times are machine-load dependent). These are production-census timings, not controlled benchmark measurements; `docs/benchmark.json` does not archive a separate windowed-versus-pure comparison.

**Total flips: 63032**

## muscovite family

| rule | window | winners (A) | flips in | flips out | center range (um) |
|---|---|---|---|---|---|
| muscovite_lowAl | [2.206, 2.21] | 54707 | 37981 | 7155 | [2.20035, 2.21378] |
| muscovite_medAl | [2.2, 2.206] | 174549 | 2136 | 38182 | [2.19949, 2.20992] |
| muscovite_medhighAl | [2.195, 2.2] | 1595 | 200 | 1473 | [2.19485, 2.20774] |
| muscovite_Fe-rich | [2.21, 2.22] | 11935 | 6506 | 13 | [2.20764, 2.22006] |
| illite_imt1 | - | 633 | 0 | 0 | [2.20646, 2.21812] |
| illite_gds4 | - | 235 | 0 | 0 | [2.20547, 2.22408] |
| kaolinite.5+muscoviteMedAl.5 | - | 638 | 0 | 0 | [2.20130, 2.20816] |
| kaolinite.5+muscoviteMedhighAl.5 | - | 95 | 0 | 0 | [2.20094, 2.20794] |
| kaolinite+muscovite_mix_intimate | - | 3932 | 0 | 0 | [2.20305, 2.21172] |
| clinochlore_Fe.3+muscovite.7 | - | 643612 | 0 | 0 | [2.18932, 2.25503] |
| calcite.5+muscoviteMedHiAl.5 | - | 636 | 0 | 0 | [2.18805, 2.20782] |
| calcite.5+muscoviteMedAl.5 | - | 30909 | 0 | 0 | [2.18837, 2.20998] |
| calcite.3+muscoviteLowAl.7 | - | 63587 | 0 | 0 | [2.19123, 2.22567] |

flip pairs (pure-argmax attribution -> arbitrated attribution):
- muscovite_medAl -> muscovite_lowAl: 37968
- muscovite_lowAl -> muscovite_Fe-rich: 6492
- muscovite_medhighAl -> muscovite_medAl: 1473
- muscovite_lowAl -> muscovite_medAl: 663
- muscovite_medAl -> muscovite_medhighAl: 200
- muscovite_medAl -> muscovite_Fe-rich: 14
- muscovite_Fe-rich -> muscovite_lowAl: 13

## chlorite family

| rule | window | winners (A) | flips in | flips out | center range (um) |
|---|---|---|---|---|---|
| chlorite_lowFe | [2.245, 2.248] | 133 | 133 | 0 | [2.24469, 2.24853] |
| clinochlore | [2.248, 2.252] | 13790 | 706 | 15405 | [2.24313, 2.25749] |
| clinochlore_Fe | [2.252, 2.256] | 16964 | 15172 | 804 | [2.24905, 2.25718] |
| thuringite | [2.256, 2.266] | 198 | 198 | 0 | [2.25570, 2.26350] |

flip pairs (pure-argmax attribution -> arbitrated attribution):
- clinochlore -> clinochlore_Fe: 15172
- clinochlore_Fe -> clinochlore: 706
- clinochlore -> chlorite_lowFe: 133
- clinochlore -> thuringite: 100
- clinochlore_Fe -> thuringite: 98

## carbonate family

| rule | window | winners (A) | flips in | flips out | center range (um) |
|---|---|---|---|---|---|
| calcite_abundant | [2.334, 2.35] | 5 | 0 | 0 | [2.33744, 2.33889] |
| calcite | [2.334, 2.35] | 37270 | 0 | 0 | [2.30149, 2.35240] |
| dolomite_abundant | [2.308, 2.328] | 13594 | 0 | 0 | [2.31243, 2.32864] |
| dolomite | [2.308, 2.328] | 26085 | 0 | 0 | [2.27947, 2.32923] |
| carbonate_Fe_bearing | - | 1718 | 0 | 0 | [2.31531, 2.35009] |
| calcite.5+dolomite.5 | - | 68206 | 0 | 0 | [2.29991, 2.34436] |

no flips involving this family.

## sanity

flips not involving any arbitrated family: 0 (must be 0)

## configuration note (2026-11-16)

This archived census and the current-tier carbonate result reported in README
belong to different arbitration configurations. The 63,032 total above covers
muscovite and chlorite only. A separate current-tier run reports 1,599
plain-tier calcite→dolomite flips, zero reverse flips and zero abundant-tier
flips. The two records are reported separately and are not summed. The older
"no flips involving this family" line is therefore scoped to this archived
configuration, not to the current per-tier behavior.

## lowFe window update (2026-11-18)

The archived chlorite census above used lowFe `[2.245, 2.248)`, including the
133 clinochlore→lowFe changes. The current rule extends only the lower bound
to `[2.244, 2.248)`. The archived counts must not be presented as the new
configuration's result; new synthetic or scene counts are reported separately.
Under the current engine, a controlled full-scene comparison gives 135
clinochlore→lowFe changes with the old lower bound and 146 with the new one,
so the window extension adds exactly 11 changes and no other label changes.
Two of the eleven target refits initially fell just below 2.244 µm; the
post-refit target-window guard now falls back to their pre-reassignment
centers without changing the labels.

## carbonate verification (2026-11-19)

A current-engine controlled scene audit independently reproduces 1,599
plain-tier calcite→dolomite changes with zero reverse, abundant-tier,
cross-tier or non-carbonate changes. All 1,599 target dolomite rules pass
full constraints and all refitted centers are consistent with the target
window. No post-refit fallback is required. See
`output/carbonate_arbitration_scene_v1/summary.json` and
`refit_verification.csv`.
