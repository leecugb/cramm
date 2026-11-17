# 跨库验证失败光谱清单(Top-1 miss,2026-09-08,1.5.0 引擎复测版)

> 鉴定腿 miss = Top-1 族级未命中(含无触发/混合头名/虚警);化学腿失败 = 产品未触发(center=0)。
> 逐谱诊断 PDF 见 docs/crosslib_diag/(仅纯规则/混合误判有特征可绘,共 105 份)。

## RELAB 腿:155/551 Top-1 miss

### calcite(59 miss)

- `c1hm01` Calcite- HYD-BLT-1a → 纯规则误判:头名 `dolomite_abundant`(fit 0.9726) [Top-5 命中],诊断 relab_c1hm01.pdf
- `c1sh02` 2502 Magnesite → 纯规则误判:头名 `dolomite`(fit 0.7187),诊断 relab_c1sh02.pdf
- `c1sh03` 2506 Magnesite → 纯规则误判:头名 `dolomite_abundant`(fit 0.7733),诊断 relab_c1sh03.pdf
- `c1sh19` 2507 Magnesite → 纯规则误判:头名 `dolomite_abundant`(fit 0.7171),诊断 relab_c1sh19.pdf
- `c1sh20` 4506 Smithsonite → 无触发:无触发
- `cbcc06` Magnesite → 纯规则误判:头名 `dolomite`(fit 0.7727),诊断 relab_cbcc06.pdf
- `c1be223` Magnesite- MGC → 无触发:无触发
- `c1be224` Magnesite- MGC → 无触发:无触发
- `c1be225` Magnesite- MGC → 无触发:无触发
- `c1be226` Magnesite- MGC → 纯规则误判:头名 `dolomite`(fit 0.6827),诊断 relab_c1be226.pdf
- `c1be227` Magnesite- MGC → 无触发:无触发
- `c1be228` Magnesite- MGC → 纯规则误判:头名 `dolomite`(fit 0.6803),诊断 relab_c1be228.pdf
- `c1be229` Magnesite- MGC → 纯规则误判:头名 `dolomite`(fit 0.6893),诊断 relab_c1be229.pdf
- `c1be230` Magnesite- MGC → 纯规则误判:头名 `dolomite`(fit 0.6926),诊断 relab_c1be230.pdf
- `c1be231` Magnesite- MGC → 无触发:无触发
- `c1be44` Magnesite (CC-06B) → 纯规则误判:头名 `dolomite`(fit 0.7376),诊断 relab_c1be44.pdf
- `c1jb825` C1: Mg Calcite (25C) → 无触发:无触发
- `c1jb826` C2: Mg Calcite (35C) → 无触发:无触发
- `c1jb827` C3: Mg Calcite (35C) → 无触发:无触发
- `c1jb946a` Brumado Bahia Magnesite → 纯规则误判:头名 `dolomite_abundant`(fit 0.6573),诊断 relab_c1jb946a.pdf
- `c1jb946b` Brumado Bahia Magnesite → 纯规则误判:头名 `dolomite_abundant`(fit 0.6477),诊断 relab_c1jb946b.pdf
- `c1jb946c` Brumado Bahia Magnesite → 无触发:无触发
- `c1jb946d` Brumado Bahia Magnesite → 无触发:无触发
- `c1jb946e` Brumado Bahia Magnesite → 纯规则误判:头名 `dolomite_abundant`(fit 0.6604),诊断 relab_c1jb946e.pdf
- `c1zl08` Magnesite <212 um → 无触发:无触发
- `c2jb946a` Brumado Bahia Magnesite → 纯规则误判:头名 `dolomite_abundant`(fit 0.6500),诊断 relab_c2jb946a.pdf
- `c2jb946b` Brumado Bahia Magnesite → 纯规则误判:头名 `dolomite_abundant`(fit 0.6477),诊断 relab_c2jb946b.pdf
- `cabe256` Magnesite- MGC → 无触发:无触发
- `cacb06` Magnesite- CRB106 → 纯规则误判:头名 `dolomite_abundant`(fit 0.7535),诊断 relab_cacb06.pdf
- `cacb13` Manganocalcite- CRB113 → 无触发:无触发
- `cacb14` Magnesite- CRB114 → 纯规则误判:头名 `serpentine_chrysotile_withsecondfeat`(fit 0.9745) [Top-5 命中],诊断 relab_cacb14.pdf
- `cacb28` Hydromagnesite- CRB208 → 无触发:无触发
- `cacb35` Hydromagnesite- CRB215 → 无触发:无触发
- `cacb36` Hydromagnesite- CRB216 → 无触发:无触发
- `cacb49` Hydromagnesite- CRB315 → 纯规则误判:头名 `serpentine_chrysotile`(fit 0.7038) [Top-5 命中],诊断 relab_cacb49.pdf
- `cacb68` Rhodochrosite- CRB142 → 无触发:无触发
- `cacb70` Magnesite- CRB144 → 纯规则误判:头名 `dolomite_abundant`(fit 0.6578),诊断 relab_cacb70.pdf
- `cacb72` Gaspeite- CRB147 → 无触发:无触发
- `cacb77` Hydrocalcite- CRB800 → 无触发:无触发
- `cacb78` Monohydrocalcite- CRB801 → 无触发:无触发
- `cbbe256` Magnesite- MGC → 无触发:无触发
- `cbcb06` Magnesite- CRB106 → 纯规则误判:头名 `dolomite_abundant`(fit 0.7474),诊断 relab_cbcb06.pdf
- `cbcb28` Hydromagnesite- CRB208 → 无触发:无触发
- `cbcb35` Hydromagnesite- CRB215 → 无触发:无触发
- `ccbe256` Magnesite- MGC → 无触发:无触发
- `cdbe256` Magnesite- MGC → 无触发:无触发
- `cebe256` Magnesite- MGC → 无触发:无触发
- `cfbe256` Magnesite- MGC → 无触发:无触发
- `cgbe256` Magnesite- MGC → 无触发:无触发
- `chbe256` Magnesite- MGC → 无触发:无触发
- `cibe256` Magnesite- MGC → 无触发:无触发
- `cjbe256` Magnesite- MGC → 无触发:无触发
- `ckbe256` Magnesite- MGC → 无触发:无触发
- `clbe256` Magnesite- MGC → 无触发:无触发
- `cmbe256` Magnesite- MGC → 无触发:无触发
- `cnbe256` Magnesite- MGC → 无触发:无触发
- `cobe256` Magnesite- MGC → 无触发:无触发
- `cpbe256` Magnesite- MGC → 无触发:无触发
- `cqbe256` Magnesite- MGC → 无触发:无触发

### smectite(28 miss)

- `c1gr24` Nontronite- GKL-HH43 → 无触发:无触发
- `c1jb123s` Montmorillonite 123-s → 混合规则头名:头名 `tremolite_or_talc`(fit 0.8507) [Top-5 命中],诊断 relab_c1jb123s.pdf
- `c1sa51` Saponite → 混合规则头名:头名 `talc_or_tremolite`(fit 0.8740),诊断 relab_c1sa51.pdf
- `c1be23` Nontronite- Nau-2 → 植被/水/雪虚警:头名 `vegetation_green`(fit 0.8203) [Top-5 命中],诊断 relab_c1be23.pdf
- `c1gr21` Nontronite- GKL-G45 → 无触发:无触发
- `c1gr22` Nontronite- GKL-SW32 → 无触发:无触发
- `c1jb761a` Ferrosaponite GDS604B → 混合规则头名:头名 `tremolite_or_talc`(fit 0.7915) [Top-5 命中],诊断 relab_c1jb761a.pdf
- `c1jb761b` Ferrosaponite GDS604B → 混合规则头名:头名 `tremolite_or_talc`(fit 0.8105) [Top-5 命中],诊断 relab_c1jb761b.pdf
- `c1jb768` Hectorite from San Bernardino Co. → 无触发:无触发
- `c1jb885` Hectorite 49-5103 by Will Gates → 无触发:无触发
- `c1jb892` Will Gates #7 montmorillonite from 130E Arumpo → 纯规则误判:头名 `muscovite_Fe-rich`(fit 0.9240) [Top-5 命中],诊断 relab_c1jb892.pdf
- `c1jb919b` Beidellite sample #34 purified by Will Gates >125 um → 纯规则误判:头名 `muscovite_medhighAl`(fit 0.6427),诊断 relab_c1jb919b.pdf
- `c1jb923b` Beidellite sample #38 purified by Will Gates >125 um → 纯规则误判:头名 `muscovite_Fe-rich`(fit 0.9217) [Top-5 命中],诊断 relab_c1jb923b.pdf
- `c1jbb84a` Saponite SapCap-1 → 混合规则头名:头名 `talc_or_tremolite`(fit 0.9112) [Top-5 命中],诊断 relab_c1jbb84a.pdf
- `c1jbb84b` Saponite SapCap-1 → 混合规则头名:头名 `talc_or_tremolite`(fit 0.9230) [Top-5 命中],诊断 relab_c1jbb84b.pdf
- `c1jbb84c` Saponite SapCap-1 → 混合规则头名:头名 `talc_or_tremolite`(fit 0.9307) [Top-5 命中],诊断 relab_c1jbb84c.pdf
- `c1jbf41a` Green smectite → 混合规则头名:头名 `tremolite_or_talc`(fit 0.7954) [Top-5 命中],诊断 relab_c1jbf41a.pdf
- `c1jbf43a` Beige smectite → 纯规则误判:头名 `dolomite`(fit 0.7190),诊断 relab_c1jbf43a.pdf
- `c1jbf45b` Saponite PP#2 (JB1545b) → 混合规则头名:头名 `talc_or_tremolite`(fit 0.9094) [Top-5 命中],诊断 relab_c1jbf45b.pdf
- `c1jbf45c` Saponite PP#2 (JB1545c) → 混合规则头名:头名 `talc_or_tremolite`(fit 0.9225) [Top-5 命中],诊断 relab_c1jbf45c.pdf
- `c1jbf92a` Fe-saponite-rich soil (JB1592a) → 无触发:无触发
- `c1jbf92b` Fe-saponite-rich soil (JB1592b) → 植被/水/雪虚警:头名 `dry_veg_nongrass_2_3um`(fit 0.6408),诊断 relab_c1jbf92b.pdf
- `c1jbf92c` Fe-saponite-rich soil (JB1592c) → 植被/水/雪虚警:头名 `vegetation_npv_and_green`(fit 0.6735),诊断 relab_c1jbf92c.pdf
- `c1jm74` Nontronite- Nau-2 → 植被/水/雪虚警:头名 `vegetation_green`(fit 0.8307),诊断 relab_c1jm74.pdf
- `c1jm75` Saponite → 混合规则头名:头名 `talc_or_tremolite`(fit 0.8928),诊断 relab_c1jm75.pdf
- `c1jm77` Beidellite- SBId-1 → 混合规则头名:头名 `kaolinite.5+muscoviteMedAl.5`(fit 0.9137) [Top-5 命中],诊断 relab_c1jm77.pdf
- `c1rm145` Possible saponite <45 um → 无触发:无触发
- `c1zl11` Smectite <212 um → 无触发:无触发

### siderite(15 miss)

- `c1gr03` Siderite → 纯规则误判:头名 `calcite`(fit 0.9633) [Top-5 命中],诊断 relab_c1gr03.pdf
- `c1jb287` Siderite → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9786) [Top-5 命中],诊断 relab_c1jb287.pdf
- `c1sh05` 6515b Siderite → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9598),诊断 relab_c1sh05.pdf
- `cbcc07` Siderite → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9791),诊断 relab_cbcc07.pdf
- `c1jbe62a` Antigonish Co. siderite → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9800) [Top-5 命中],诊断 relab_c1jbe62a.pdf
- `c1jbe62b` Antigonish Co. siderite → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9832) [Top-5 命中],诊断 relab_c1jbe62b.pdf
- `c1jbe62c` Antigonish Co. siderite → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9816),诊断 relab_c1jbe62c.pdf
- `c1jbe62d` Antigonish Co. siderite → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9775),诊断 relab_c1jbe62d.pdf
- `c1jbe62e` Antigonish Co. siderite → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9736),诊断 relab_c1jbe62e.pdf
- `c1jbe62f` Antigonish Co. siderite → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9652),诊断 relab_c1jbe62f.pdf
- `c1zl15` Siderite <212 um → 无触发:无触发
- `cacb67` Siderite- CRB141 → 纯规则误判:头名 `chalcedony`(fit 0.7425),诊断 relab_cacb67.pdf
- `cacb69` Siderite- CRB143 → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9780) [Top-5 命中],诊断 relab_cacb69.pdf
- `cacb71` Siderite- CRB145 → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9810) [Top-5 命中],诊断 relab_cacb71.pdf
- `cacb73` Siderite- CRB148 → 植被/水/雪虚警:头名 `dry_veg_grass_2_3um`(fit 0.8350),诊断 relab_cacb73.pdf

### serpentine(13 miss)

- `c1cr02` Cronstedtite → 无触发:无触发
- `chpo84` Serpentine separate <250 um → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.8995) [Top-5 命中],诊断 relab_chpo84.pdf
- `c1sp07` 30 serpentine → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9041) [Top-5 命中],诊断 relab_c1sp07.pdf
- `c1sp09` K-185/1 serpentine → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9161) [Top-5 命中],诊断 relab_c1sp09.pdf
- `c1sr91` Serpentine #2370 Vial S Starndard target material 125-250 um → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9158) [Top-5 命中],诊断 relab_c1sr91.pdf
- `c2sr31` Serpentine #3362 shocked at 22.0 GPa → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9176) [Top-5 命中],诊断 relab_c2sr31.pdf
- `c2sr32` Serpentine #3363 shocked at 30.0 GPa → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9298) [Top-5 命中],诊断 relab_c2sr32.pdf
- `c2sr34` Serpentine #3367 shocked at 38.8 GPa → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9186) [Top-5 命中],诊断 relab_c2sr34.pdf
- `c2sr35` Serpentine #3368 shocked at 41.4 GPa → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9516) [Top-5 命中],诊断 relab_c2sr35.pdf
- `cabe01` Berthierine- BER101 → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.7706),诊断 relab_cabe01.pdf
- `cabe02` Berthierine- BER102 → 混合规则头名:头名 `carbonate_Fe_bearing`(fit 0.8355),诊断 relab_cabe02.pdf
- `cacr21` Cronstedtite- CRO101 → 无触发:无触发
- `cacr22` Cronstedtite- CRO102 → 无触发:无触发

### dolomite(10 miss)

- `c1mg56` BE-21 → 无触发:无触发
- `c1mg57` BE-46-50 → 无触发:无触发
- `c1mg60` LV-46-50 → 无触发:无触发
- `c1mg61` LV-56-60 → 无触发:无触发
- `c1mg62` LV-64-69 → 无触发:无触发
- `c1mg63` BZ(3,4,5) → 无触发:无触发
- `c1mg64` Coorong → 无触发:无触发
- `c1mg65` LFP-6-11 → 无触发:无触发
- `c1mg66` LFP-31-37 → 无触发:无触发
- `cacb01` Ankerite- CRB101 → 无触发:无触发

### chlorite(9 miss)

- `c1xt14` Chlorite → 纯规则误判:头名 `serpentine_antigorite_withironfeat`(fit 0.9253),诊断 relab_c1xt14.pdf
- `c2cl14` Chlorite → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9239) [Top-5 命中],诊断 relab_c2cl14.pdf
- `c2xt14` Chlorite → 纯规则误判:头名 `serpentine_antigorite_withironfeat`(fit 0.9246),诊断 relab_c2xt14.pdf
- `c1ch16` Chamosite- CHM102 → 混合规则头名:头名 `carbonate_Fe_bearing`(fit 0.8908),诊断 relab_c1ch16.pdf
- `c1ea25a` Clinochlore- CLI102 → 纯规则误判:头名 `serpentine_chrysotile`(fit 0.8413),诊断 relab_c1ea25a.pdf
- `c1jb737` Clinochlore WC → 纯规则误判:头名 `serpentine_antigorite_withironfeat`(fit 0.9644) [Top-5 命中],诊断 relab_c1jb737.pdf
- `cach15` Chamosite- CHM101 → 无触发:无触发
- `cach16` Chamosite- CHM102 → 混合规则头名:头名 `carbonate_Fe_bearing`(fit 0.8620),诊断 relab_cach16.pdf
- `cach17` Chamosite- CHM103 → 无触发:无触发

### illite(6 miss)

- `c1cy12` Illite - 1Md → 纯规则误判:头名 `muscovite_lowAl`(fit 0.9672) [Top-5 命中],诊断 relab_c1cy12.pdf
- `c1cy13` Illite -2M → 纯规则误判:头名 `muscovite_medhighAl`(fit 0.9786),诊断 relab_c1cy13.pdf
- `c2pi10` Illite → 纯规则误判:头名 `muscovite_lowAl`(fit 0.9365) [Top-5 命中],诊断 relab_c2pi10.pdf
- `c5pi10` Illite → 纯规则误判:头名 `montmorillonite_Ca`(fit 0.9081),诊断 relab_c5pi10.pdf
- `cairon` Illite → 无触发:无触发
- `c1jbf94` illite (JB1594) → 纯规则误判:头名 `muscovite_medhighAl`(fit 0.9848),诊断 relab_c1jbf94.pdf

### alunite(6 miss)

- `c1lh52` PP-01 <500 um → 无触发:无触发
- `casf21` SPT107 → 纯规则误判:头名 `jarosite_Na`(fit 0.9936),诊断 relab_casf21.pdf
- `casf22` SPT108 → 纯规则误判:头名 `jarosite_Na`(fit 0.9941),诊断 relab_casf22.pdf
- `casf27` SPT113 → 纯规则误判:头名 `jarosite_Na`(fit 0.9711),诊断 relab_casf27.pdf
- `casf28` SPT114A → 无触发:无触发
- `casf29` SPT115 → 纯规则误判:头名 `jarosite_K`(fit 0.9914),诊断 relab_casf29.pdf

### jarosite(4 miss)

- `c1jb715` Jarosite- T14: (NaH3)(FeAl2)(SO4)2(OH)6 → 混合规则头名:头名 `kaolinite+smectite_mix_intimate`(fit 0.8240),诊断 relab_c1jb715.pdf
- `c1jb719` Jarosite- T8: (KH3)(Fe0.5Al2.5)(SO4)2(OH)6 → 混合规则头名:头名 `pyrophyllite.25+kaolinite.75`(fit 0.8194),诊断 relab_c1jb719.pdf
- `c1jb720` Jarosite- T10: (KH3)(FeAl2)(SO4)2(OH)6 → 混合规则头名:头名 `kaolinite+smectite_mix_intimate`(fit 0.8504),诊断 relab_c1jb720.pdf
- `c1jb724` Jarosite- NAJ2-3: (Na0.6H3O0.4)(Fe0.3Al1.7)(SO4)2(OH)6 → 纯规则误判:头名 `alunite_Na_450C`(fit 0.9080),诊断 relab_c1jb724.pdf

### tremolite(2 miss)

- `c1rk95` Actinolite #5 → 纯规则误判:头名 `dolomite_abundant`(fit 0.6696),诊断 relab_c1rk95.pdf
- `c1rk97` Actinolite #7 → 无触发:无触发

### talc(1 miss)

- `c1pt12` Talc-1 → 无触发:无触发

### epidote(1 miss)

- `c1rs38` Epidote → 纯规则误判:头名 `clinochlore_Fe`(fit 0.9755) [Top-5 命中],诊断 relab_c1rs38.pdf

### muscovite(1 miss)

- `c1sh47` Muscovite → 混合规则头名:头名 `serpentine_antigorite_or_calcite+dolomite`(fit 0.6973),诊断 relab_c1sh47.pdf

## ECOSTRESS 腿:20/172 Top-1 miss

### siderite(4 miss)

- `mineral.carbonate.none.coarse.vswir.c-9a.jpl.beckman.spectrum` Siderite Fe^2+CO_3 → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9797) [Top-5 命中],诊断 eco_mineral.carbonate.none.coarse.vswir.c-9a.jpl.beckman.spectrum.pdf
- `mineral.carbonate.none.coarse.vswir.c-9a.jpl.perkin.spectrum` Siderite Fe^2+CO_3 → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9752) [Top-5 命中],诊断 eco_mineral.carbonate.none.coarse.vswir.c-9a.jpl.perkin.spectrum.pdf
- `mineral.carbonate.none.medium.vswir.c-9a.jpl.beckman.spectrum` Siderite Fe^2+CO_3 → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9832) [Top-5 命中],诊断 eco_mineral.carbonate.none.medium.vswir.c-9a.jpl.beckman.spectrum.pdf
- `mineral.carbonate.none.medium.vswir.c-9a.jpl.perkin.spectrum` Siderite Fe^2+CO_3 → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9777) [Top-5 命中],诊断 eco_mineral.carbonate.none.medium.vswir.c-9a.jpl.perkin.spectrum.pdf

### epidote(4 miss)

- `mineral.silicate.sorosilicate.coarse.vswir.ss-1a.jpl.beckman.spectrum` Epidote Ca_2(Al,Fe^3+)_3O.SiO_4.Si_2O_7.OH → 纯规则误判:头名 `clinochlore`(fit 0.9577) [Top-5 命中],诊断 eco_mineral.silicate.sorosilicate.coarse.vswir.ss-1a.jpl.beckman.spectrum.pdf
- `mineral.silicate.sorosilicate.coarse.vswir.ss-1a.jpl.perkin.spectrum` Epidote Ca_2(Al,Fe^3+)_3O.SiO_4.Si_2O_7.OH → 纯规则误判:头名 `clinochlore`(fit 0.9623) [Top-5 命中],诊断 eco_mineral.silicate.sorosilicate.coarse.vswir.ss-1a.jpl.perkin.spectrum.pdf
- `mineral.silicate.sorosilicate.fine.vswir.ss-1c.jpl.beckman.spectrum` Epidote Ca_2(Al,Fe^3+)_3O.SiO_4.Si_2O_7.OH → 混合规则头名:头名 `calcite.5+dolomite.5`(fit 0.9053),诊断 eco_mineral.silicate.sorosilicate.fine.vswir.ss-1c.jpl.beckman.spectrum.pdf
- `mineral.silicate.sorosilicate.fine.vswir.ss-1c.jpl.perkin.spectrum` Epidote Ca_2(Al,Fe^3+)_3O.SiO_4.Si_2O_7.OH → 纯规则误判:头名 `calcite`(fit 0.9049) [Top-5 命中],诊断 eco_mineral.silicate.sorosilicate.fine.vswir.ss-1c.jpl.perkin.spectrum.pdf

### tremolite(2 miss)

- `mineral.silicate.inosilicate.coarse.vswir.in-5a.jpl.beckman.spectrum` Tremolite Ca_2(Mg,Fe^2+)_5Si_8O_22(OH)_2 → 植被/水/雪虚警:头名 `dry_veg_nongrass`(fit 0.6717),诊断 eco_mineral.silicate.inosilicate.coarse.vswir.in-5a.jpl.beckman.spectrum.pdf
- `mineral.silicate.inosilicate.coarse.vswir.in-5a.jpl.perkin.spectrum` Tremolite Ca_2(Mg,Fe^2+)_5Si_8O_22(OH)_2 → 无触发:无触发

### serpentine(2 miss)

- `mineral.silicate.phyllosilicate.coarse.vswir.ps-20a.jpl.beckman.spectrum` Serpentine (Mg,Fe^2+,Ni)Si_2O_5(OH)_4 → 纯规则误判:头名 `dolomite_abundant`(fit 0.9626) [Top-5 命中],诊断 eco_mineral.silicate.phyllosilicate.coarse.vswir.ps-20a.jpl.beckman.spectrum.pdf
- `mineral.silicate.phyllosilicate.fine.vswir.ps-20a.jpl.beckman.spectrum` Serpentine (Mg,Fe^2+,Ni)Si_2O_5(OH)_4 → 纯规则误判:头名 `dolomite_abundant`(fit 0.8938) [Top-5 命中],诊断 eco_mineral.silicate.phyllosilicate.fine.vswir.ps-20a.jpl.beckman.spectrum.pdf

### muscovite(2 miss)

- `mineral.silicate.phyllosilicate.fine.vswir.ps-16a.jpl.beckman.spectrum` Muscovite KAl_2(Si_3Al)O_10(OH,F)_2 → 混合规则头名:头名 `kaolinite+smectite_mix_intimate`(fit 0.8990) [Top-5 命中],诊断 eco_mineral.silicate.phyllosilicate.fine.vswir.ps-16a.jpl.beckman.spectrum.pdf
- `mineral.silicate.phyllosilicate.fine.vswir.ps-16a.jpl.perkin.spectrum` Muscovite KAl_2(Si_3Al)O_10(OH,F)_2 → 纯规则误判:头名 `montmorillonite_Na`(fit 0.8617),诊断 eco_mineral.silicate.phyllosilicate.fine.vswir.ps-16a.jpl.perkin.spectrum.pdf

### smectite(2 miss)

- `mineral.silicate.phyllosilicate.fine.vswir.ps-24a.jpl.beckman.spectrum` Saponite (Ca/2,Na)_0.33(Mg,Fe^2+)_3(Si,Al)_4O_10(OH)_2.4H_2O → 混合规则头名:头名 `tremolite_or_talc`(fit 0.9578) [Top-5 命中],诊断 eco_mineral.silicate.phyllosilicate.fine.vswir.ps-24a.jpl.beckman.spectrum.pdf
- `mineral.silicate.phyllosilicate.fine.vswir.ps-24a.jpl.perkin.spectrum` Saponite (Ca/2,Na)_0.33(Mg,Fe^2+)_3(Si,Al)_4O_10(OH)_2.4H_2O → 混合规则头名:头名 `talc_or_tremolite`(fit 0.9495) [Top-5 命中],诊断 eco_mineral.silicate.phyllosilicate.fine.vswir.ps-24a.jpl.perkin.spectrum.pdf

### jarosite(2 miss)

- `mineral.sulfate.none.coarse.vswir.so-7a.jpl.perkin.spectrum` Jarosite KFe_3^3+(SO_4)_2(OH)_6 → 纯规则误判:头名 `nontronite`(fit 0.7188) [Top-5 命中],诊断 eco_mineral.sulfate.none.coarse.vswir.so-7a.jpl.perkin.spectrum.pdf
- `mineral.sulfate.none.medium.vswir.so-7a.jpl.perkin.spectrum` Jarosite KFe_3^3+(SO_4)_2(OH)_6 → 纯规则误判:头名 `nontronite`(fit 0.7201) [Top-5 命中],诊断 eco_mineral.sulfate.none.medium.vswir.so-7a.jpl.perkin.spectrum.pdf

### talc(1 miss)

- `mineral.silicate.phyllosilicate.coarse.vswir.ps-14a.jpl.perkin.spectrum` Talc Mg_3Si_4O_10(OH)_2 → 无触发:无触发

### chlorite(1 miss)

- `mineral.silicate.phyllosilicate.fine.vswir.ps-12e.jpl.beckman.spectrum` Chlorite → 纯规则误判:头名 `serpentine_antigorite_withironfeat`(fit 0.9546) [Top-5 命中],诊断 eco_mineral.silicate.phyllosilicate.fine.vswir.ps-12e.jpl.beckman.spectrum.pdf

## 化学腿:产品未触发(center = 0)

- A_muscovite_USGS:22/22 全部触发,无失败
### B_chlorite_USGS(10/44 未触发)

- `splib07a_Clinochlore_GDS159_BECKb_AREF` GDS159(Fe_frac=0.0165944023323789)
- `splib07a_Clinochlore_GDS159_NIC4bb_RREF` GDS159(Fe_frac=0.0165944023323789)
- `splib07a_Clinochlore_NMNH83369_NIC4bbb_RREF` NMNH83369(Fe_frac=0.05301880404278569)
- `splib07a_Clinochlore_NMNH83369_NIC4b_RREF` NMNH83369(Fe_frac=0.05301880404278569)
- `splib07a_Chlorite_SMR-13.e_lt30um_BECKb_AREF` SMR-13(Fe_frac=0.12234429255450854)
- `splib07a_Chlorite_SMR-13.e_lt30um_NIC4bb_RREF` SMR-13(Fe_frac=0.12234429255450854)
- `splib07a_Prochlorite_SMR-14.a_115um_BECKa_AREF` SMR-14(Fe_frac=0.5132932936593981)
- `splib07a_Prochlorite_SMR-14.b_32um_BECKa_AREF` SMR-14(Fe_frac=0.5132932936593981)
- `splib07a_Prochlorite_SMR-14.c_lt30um_BECKa_AREF` SMR-14(Fe_frac=0.5132932936593981)
- `splib07a_Thuringite_SMR-15.d_lt30um_BECKa_AREF` SMR-15(Fe_frac=0.5297960316826019)

### C_RELAB_chlorite(1/4 未触发)

- `c1ch16` Chamosite CHM102(Fe_frac=0.8892)

### C_RELAB_mica(2/2 未触发)

- `c1ea19a` Celadonite CEL101(Al2O3_wt=2.53)
- `c1ea31a` Phlogopite PHL101(Al2O3_wt=13.23)
