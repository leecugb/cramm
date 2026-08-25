# Wavelength-arbitration production statistics

Scene: `EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc` (1280x1242)
Method: production rf.json (all windows) vs the same rules with every `absorption_center_range` stripped (pure argmax MICA); every NUM diff is a production flip by `_reassign_by_absorption_center`.
Runtime: windowed 59.8s, pure-argmax 60.0s (n_workers=4).

**Total flips: 62128**

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
| chlorite_lowFe | [2.245, 2.248] | 50 | 50 | 0 | [2.24469, 2.24725] |
| clinochlore | [2.247, 2.252] | 13756 | 286 | 15019 | [2.24313, 2.26245] |
| clinochlore_Fe | [2.251, 2.25549] | 17279 | 14969 | 286 | [2.24905, 2.26346] |

flip pairs (pure-argmax attribution -> arbitrated attribution):
- clinochlore -> clinochlore_Fe: 14969
- clinochlore_Fe -> clinochlore: 286
- clinochlore -> chlorite_lowFe: 50

## carbonate family

| rule | window | winners (A) | flips in | flips out | center range (um) |
|---|---|---|---|---|---|
| calcite_abundant | [2.334, 2.35] | 5 | 0 | 0 | [2.33744, 2.33889] |
| calcite | [2.334, 2.35] | 37270 | 0 | 0 | [2.30149, 2.35240] |
| dolomite_abundant | [2.308, 2.328] | 13594 | 0 | 0 | [2.31243, 2.32864] |
| dolomite | [2.308, 2.328] | 26085 | 0 | 0 | [2.27947, 2.32923] |
| carbonate_Fe_bearing | - | 1718 | 0 | 0 | [2.31531, 2.35009] |

no flips involving this family.

## sanity

flips not involving any arbitrated family: 0 (must be 0)
