# 跨库鉴定基准(ECOSTRESS + RELAB → CRAMM)

> 日期:2026-09-28 | 脚本:`docs/crosslib_benchmark.py`(可重复执行) | 规则库:rf.json 77 规则 | RELAB 池:`relab_selection.csv`(R1-R9) | ECOSTRESS 池:mineral ∩ (vswir|all),排重审计零同源

## 方法

- 每条库谱滤波至 0.38–2.55 µm 窗口(有效点 ≥100 且覆盖 0.5–2.45 µm),直接以原生网格送入 `MicaEngine.classify_spectrum`(bp = 局部步长),参考库按同一网格高斯重采样(引擎编译缓存,同仪器网格只算一次)。
- **族级评分**:77 条规则手工映射到族集合(纯规则=单族,混合规则=组分族集合,植被/水/雪=other;映射表存档于脚本 `RULE_FAMILY`)。Top-1 hit = 头名规则族集合 ⊇ 真值族;Top-5 hit = 前 5 名族集合之并 ⊇ 真值族。
- 混淆矩阵仅统计头名为纯规则者;混合规则头名单列;other 规则命中矿物谱记虚警(miss)。
- ECOSTRESS 名称无法唯一归族的记录进 OOD 池,只统计 Top-1 规则分布(虚警画像)。
- 族内 Top-1 miss 生成特征诊断 PDF(`crosslib_diag/`,每腿上限 100 份)。

## 总体结果

| 腿 | 族内光谱 | Top-1 | Top-5 | 标本级 Top-1 | 头名:纯/混合/other/无触发 |
|---|---|---|---|---|---|
| RELAB | 551 | 0.711 | 0.771 | 0.732 (508 标本) | 371 / 107 / 5 / 68 |
| ECOSTRESS | 172 | 0.884 | 0.971 | 0.946 (37 标本) | 139 / 30 / 1 / 2 |

- 混合规则头名:RELAB 命中 64/107,ECOSTRESS 命中 22/30(真值 ∈ 混合组分集合,判 hit——库谱本身是单矿物,混合规则头名提示该矿物与混合参照谱形相似,应视为**弱鉴定**)。

## RELAB 腿 · 分族结果

| 族 | n | Top-1 | Top-1 acc | Top-5 acc |
|---|---|---|---|---|
| smectite | 143 | 115 | 0.804 | 0.895 |
| carbonate-other | 58 | 0 | 0.000 | 0.000 |
| serpentine | 57 | 44 | 0.772 | 0.912 |
| calcite | 47 | 42 | 0.894 | 0.915 |
| gypsum | 41 | 41 | 1.000 | 1.000 |
| jarosite | 39 | 35 | 0.897 | 0.897 |
| dolomite | 38 | 28 | 0.737 | 0.737 |
| chlorite | 30 | 21 | 0.700 | 0.767 |
| siderite | 25 | 10 | 0.400 | 0.640 |
| kaolinite | 21 | 21 | 1.000 | 1.000 |
| tremolite | 13 | 11 | 0.846 | 0.846 |
| alunite | 12 | 6 | 0.500 | 0.500 |
| talc | 10 | 9 | 0.900 | 0.900 |
| illite | 7 | 1 | 0.143 | 0.429 |
| pyrophyllite | 3 | 3 | 1.000 | 1.000 |
| epidote | 2 | 1 | 0.500 | 1.000 |
| muscovite | 2 | 1 | 0.500 | 0.500 |
| opal | 2 | 2 | 1.000 | 1.000 |
| buddingtonite | 1 | 1 | 1.000 | 1.000 |

### RELAB 混淆(纯规则头名)

| 真值 → 预测族 | 次数 |
|---|---|
| smectite → smectite | 106 |
| serpentine → serpentine | 44 |
| calcite → calcite | 42 |
| gypsum → gypsum | 41 |
| jarosite → jarosite | 34 |
| chlorite → chlorite | 20 |
| carbonate-other → dolomite | 17 ✗ |
| dolomite → dolomite | 15 |
| kaolinite → kaolinite | 14 |
| alunite → alunite | 4 |
| illite → muscovite | 4 ✗ |
| chlorite → serpentine | 4 ✗ |
| alunite → jarosite | 4 ✗ |
| smectite → muscovite | 3 ✗ |
| pyrophyllite → pyrophyllite | 2 |
| opal → opal | 2 |
| carbonate-other → serpentine | 2 ✗ |
| buddingtonite → buddingtonite | 1 |
| siderite → calcite | 1 ✗ |
| calcite → dolomite | 1 ✗ |
| tremolite → dolomite | 1 ✗ |
| epidote → chlorite | 1 ✗ |
| muscovite → muscovite | 1 |
| illite → smectite | 1 ✗ |
| epidote → epidote | 1 |
| jarosite → alunite | 1 ✗ |
| illite → illite | 1 |
| smectite → dolomite | 1 ✗ |
| siderite → chalcedony | 1 ✗ |
| carbonate-other → calcite | 1 ✗ |

## ECOSTRESS 腿 · 分族结果

| 族 | n | Top-1 | Top-1 acc | Top-5 acc |
|---|---|---|---|---|
| chlorite | 24 | 23 | 0.958 | 1.000 |
| calcite | 18 | 18 | 1.000 | 1.000 |
| jarosite | 18 | 16 | 0.889 | 1.000 |
| smectite | 16 | 14 | 0.875 | 1.000 |
| epidote | 15 | 11 | 0.733 | 0.933 |
| dolomite | 12 | 12 | 1.000 | 1.000 |
| tremolite | 12 | 10 | 0.833 | 0.833 |
| gypsum | 7 | 7 | 1.000 | 1.000 |
| siderite | 6 | 2 | 0.333 | 1.000 |
| topaz | 6 | 6 | 1.000 | 1.000 |
| talc | 6 | 5 | 0.833 | 0.833 |
| muscovite | 6 | 4 | 0.667 | 0.833 |
| serpentine | 6 | 4 | 0.667 | 1.000 |
| kaolinite | 6 | 6 | 1.000 | 1.000 |
| alunite | 6 | 6 | 1.000 | 1.000 |
| pyrophyllite | 3 | 3 | 1.000 | 1.000 |
| buddingtonite | 3 | 3 | 1.000 | 1.000 |
| illite | 2 | 2 | 1.000 | 1.000 |

### ECOSTRESS 混淆(纯规则头名)

| 真值 → 预测族 | 次数 |
|---|---|
| chlorite → chlorite | 23 |
| calcite → calcite | 17 |
| jarosite → jarosite | 16 |
| smectite → smectite | 14 |
| dolomite → dolomite | 12 |
| epidote → epidote | 11 |
| gypsum → gypsum | 7 |
| topaz → topaz | 6 |
| kaolinite → kaolinite | 5 |
| muscovite → muscovite | 4 |
| serpentine → serpentine | 4 |
| pyrophyllite → pyrophyllite | 3 |
| buddingtonite → buddingtonite | 3 |
| alunite → alunite | 3 |
| serpentine → dolomite | 2 ✗ |
| illite → illite | 2 |
| epidote → chlorite | 2 ✗ |
| jarosite → smectite | 2 ✗ |
| chlorite → serpentine | 1 ✗ |
| muscovite → smectite | 1 ✗ |
| epidote → calcite | 1 ✗ |

## ECOSTRESS OOD 池(族外虚警画像)

- OOD 光谱 685 条(网格不合格跳过 1 条),其中 **427 条无任何规则触发**(引擎事实拒识,占 62.3%)。其余矿物的 Top-1 规则分布如下,用于评估误吸收风险。

| Top-1 规则 | 次数 |
|---|---|
| calcite | 28 |
| montmorillonite_Na | 26 |
| kaolinite+smectite_mix_intimate | 20 |
| muscovite_medhighAl | 18 |
| pyrophyllite.25+kaolinite.75 | 14 |
| buddingtonite+montmorillonite_mix_intimate | 14 |
| calcite.5+dolomite.5 | 14 |
| dolomite | 11 |
| carbonate_Fe_bearing | 10 |
| dry_veg_grass_2_3um | 10 |
| jarosite+muscovite_mix_intimate | 8 |
| chalcedony | 8 |
| tremolite_or_talc | 6 |
| montmorillonite_Ca | 5 |
| nontronite | 5 |
| buddingtonite | 5 |
| hectorite | 5 |
| epidote | 5 |
| dry_veg_nongrass_2_3um | 4 |
| clinochlore_Fe.3+muscovite.7 | 4 |
| vegetation_npv_and_green | 4 |
| talc_or_tremolite | 4 |
| snow_melting | 3 |
| jarosite_Na | 3 |
| dry_veg_nongrass | 3 |
| dolomite_abundant | 3 |
| gypsum | 2 |
| calcite.25+montmorilloniteCa.75 | 2 |
| chlorite_lowFe | 2 |
| hydrated_silica | 1 |
| clinochlore | 1 |
| clinochlore_Fe | 1 |
| serpentine_antigorite_or_calcite+dolomite | 1 |
| serpentine_antigorite_withsecondfeat | 1 |
| dry_veg_grass | 1 |
| serpentine_antigorite_withironfeat | 1 |
| water_sediment_low | 1 |
| kaolinite_wxl | 1 |
| serpentine_chrysotile_withsecondfeat | 1 |
| calcite.25+montmorilloniteNa.75 | 1 |
| kaolinite+clay_mica_or_halloysite | 1 |

## 备注

- 两腿的族真值粒度均为族;RELAB 真值来源 subtype>name>group(见 `relab_selection.md`),ECOSTRESS 为名称正则唯一命中。
- `carbonate_Fe_bearing` 映射为 {siderite, dolomite}:Fe 碳酸盐通用规则,菱铁矿与铁白云石(ankerite→dolomite 族)均为合法命中。
- `hydrated_silica` 映射为 {opal}(水合二氧化硅);`tremolite_or_talc`/`talc_or_tremolite` 为 {tremolite, talc} 双族规则。
- 诊断 PDF 的文件名对应 `crosslib_benchmark.csv` 的 `diag_pdf` 列;无规则触发(no_fire)的 miss 没有特征可绘,不生成 PDF。
