# .mcf 与 rf_splib07.json 差异声明

> 日期：2026-08-31（dry_veg_nongrass 映射更正；illite_gds4 覆盖裁决：BECKb→ASDNGb）｜ 数据：`docs/splib07_selection.json`（逐条 r 值）、`docs/splib07_export_audit.md`（烘焙审计）、`docs/splib07_dualrun_diff.md`（场景双跑）

## 结论

rf_splib07.json 的 **77 条规则同 rf.json 逐比特一致**（诊断特征参数、约束、权重原样继承 .mcf v6a 启用态，核验见 `docs/MCF_vs_rfjson_verification.md`）；差异有两类，均已逐条裁决并记录：

1. **参考光谱来源**：splib06b 记录 → splib07 同名样品记录（53 条唯一实物参考，D1-A 同仪器+同测量类型选谱；1 条裁决覆盖偏离同仪器策略：illite_gds4 改用同样品 ASDNGb 记录以恢复 1.4 µm 带真实数据）；
2. **5 条混合配方改接 AMX 实物记录**：splib07 AMX 系列中与 .mcf 配方同样品同配比的计算混合谱，烘焙后以权重 1.0 别名接入（GDS212/213 先例）——19 条混合配方中 14 条与 rf.json 逐比特一致（12 条线性合成 + 2 条 GDS 别名），5 条为 AMX 别名。

因此 rf_splib07.json **不是**对 .mcf 的逐位保真移植——它是同规则、新参考的 v1.2.0 轨道；rf.json 保持不动，继续作为 .mcf 零差异保真基线。两轨道并存，由 `MicaEngine(rf_path=...)` 选择。

**计数口径**：77 条规则 → 70 条唯一规则面参考（51 条直接引用 + 19 条混合谱；7 条复用——dry_veg_grass/dry_veg_nongrass/calcite/dolomite/serpentine_chrysotile 各 2 规则共享、serpentine_antigorite 3 规则共享）→ 58 条唯一实物记录（51 + 2 条仅经权重 1.0 别名引用的 GDS212/213 + 5 条 AMX 计算混合记录，合成 rec id 90008/90010/90012/90017/90021）。

## 参考谱差异（53 条唯一实物参考）

r = splib07 记录与 06b 原记录在 0.35–2.5 µm 公共网格上的 Pearson 相关（选谱阶段计算，同仪器同测量类型优先）。

| splib06b rec | splib06b 标题 | 选定 splib07 记录 | r |
|---|---|---|---|
| 12539 | Engelmann-Spruce ES-Needls-1 W1R1Fa AREF | `Engelmann-Spruce_ES-Needls-1_ASDFRa_AREF` | 1.0 |
| 13411 | Rangeland C04-170 S30% G24%  W1R1Fa AREF | `Rangeland_C04-170_S30%_G24%_ASDFRa_AREF` | 1.0 |
| 11541 | Melting_snow mSnw1a          W1R1Fa AREF | `Melting_snow_mSnw01a_ASDFRa_AREF` | 1.0 |
| 11589 | Melting_snow mSnw9  (slush)  W1R1Fa AREF | `Melting_snow_mSnw09_(slush)_ASDFRa_AREF` | 1.0 |
| 11607 | Seawater_Coast_Chl SW1       W1R1Ba AREF | `Seawater_Coast_Chl_SW1_BECKa_AREF` | 1.0 |
| 11647 | Water+Montmor SWy-2+5.01g/l  W1R1Fa AREF | `Water+Montmor_SWy-2+5.01g-l_ASDFRa_AREF` | 1.0 |
| 11629 | Water+Montmor SWy-2+0.5g/l   W1R1Fa AREF | `Water+Montmor_SWy-2+0.50g-l_ASDFRa_AREF` | 1.0 |
| 12658 | Grass_Golden_Dry GDS480      W1R1Fa AREF | `Grass_Golden_Dry_GDS480_ASDFRa_AREF` | 1.0 |
| 12794 | Lodgepole-Pine LP-Needles-3  W1R1Fa AREF | `Lodgepole-Pine_LP-Needles-2_ASDFRa_AREF` | 1.0 |
| 6258 | Muscovite CU93-1 low-Al Phyl W2R4Nb RREF | `Muscovite_CU93-1_low-Al_Phyl_NIC4b_RREF` | 1.0 |
| 11117 | Muscovite CU91-250A med Al   W2R4Nb RREF | `Muscovite-medlowAl_CU91-250A_NIC4b_RREF` | 1.0 |
| 6348 | Muscovite GDS113 Ruby      W9R4Nbbb RREF | `Muscovite_GDS113_Ruby_NIC4aaa_RREF` | 1.0 |
| 6394 | Muscovite GDS116 Tanzania  W9R4Naaa RREF | `Muscovite_GDS116_Tanzania_NIC4aaa_RREF` | 1.0 |
| 4693 | Illite IMt-1.b <2um          W1R1Ba AREF | `Illite_IMt-1.b_lt2um_BECKa_AREF` | 1.0 |
| 4625 | Illite GDS4 (Marblehead)     W1R1Bb AREF | `Illite_GDS4_Marblehead_ASDNGb_AREF` | 0.9708 |
| 5088 | Kaolinite CM9              W9R4Nbbb RREF | `Kaolinite_CM9_NIC4bbb_RREF` | 1.0 |
| 5167 | Kaolinite KGa-2 (pxl)      W9R4Nbbb RREF | `Kaolinite_KGa-2_(pxl)_NIC4bbb_RREF` | 1.0 |
| 3869 | Halloysite NMNH106237      W9R4Naaa RREF | `Halloysite_NMNH106237_NIC4aaa_RREF` | 1.0 |
| 2872 | Dickite NMNH106242         W5R4Nbb_ RREF | `Dickite_NMNH106242_NIC4bb_RREF` | 1.0 |
| 1632 | Buddingtonite GDS85 D-206    W1R1Bb AREF | `Buddingtonite_GDS85_D-206_BECKb_AREF` | 1.0 |
| 10350 | Buddingtnt+Na-Mont CU93-260B W2R4Nb RREF | `Buddingtnt+Na-Mont_CU93-260B_NIC4b_RREF` | 1.0 |
| 596 | Alunite GDS96 K  Syn (250C)  W2R4Na RREF | `Alunite_GDS96_K_Syn_(250C)_NIC4a_RREF` | 1.0 |
| 655 | Alunite RES-3 Na Syn (450C)  W2R4Na RREF | `Alunite_RES-3_Na_Syn_(450C)_NIC4a_RREF` | 1.0 |
| 7893 | Pyrophyllite PYS1A <850um    W2R4Na RREF | `Pyrophyllite_PYS1A_lt850um_NIC4aaa_RREF` | 1.0 |
| 4819 | Jarosite GDS24 Na          W9R4Nbbb RREF | `Jarosite_GDS24_Na_NIC4bbb_RREF` | 1.0 |
| 4875 | Jarosite GDS99 K 200C Syn    W2R4Na RREF | `Jarosite_GDS99_K_200C_Syn_NIC4aa_RREF` | 0.9827 |
| 6200 | Montmorillonite SWy-1      W9R4Nbcc RREF | `Montmorillonite_SWy-1_NIC4bcc_RREF` | 1.0 |
| 6120 | Montmorillonite SAz-1      W5R4Nbb_ RREF | `Montmorillonite_SAz-1_NIC4bb_RREF` | 1.0 |
| 6772 | Nontronite NG-1.b <2um fr  W5R4Nbb_ RREF | `Nontronite_NG-1.b_lt2um_fr_NIC4bb_RREF` | 1.0 |
| 3913 | Hectorite SHCa-1.Ac-B      W5R4Nbb_ RREF | `Hectorite_SHCa-1.Ac-B_NIC4bb_RREF` | 1.0 |
| 3767 | Gypsum HS333.3B (Selenite) W9R4Naaa RREF | `Gypsum_HS333.3B_(Selenite)_NIC4aaa_RREF` | 1.0 |
| 2047 | Chlorite SMR-13.a 104-150    W1R1Ba AREF | `Chlorite_SMR-13.a_104-150um_BECKa_AREF` | 1.0 |
| 2253 | Clinochlore GDS158 Flagst  W5R4Nbb_ RREF | `Clinochlore_GDS158_Flagstaff_NIC4bb_RREF` | 1.0 |
| 2371 | Clinochlore_Fe SC-CCa-1.a  W5R4Naa_ RREF | `Clinochlore_Fe_SC-CCa-1.a_NIC4aa_RREF` | 1.0 |
| 9262 | Thuringite SMR-15.c  32um  W5R4Naa_ RREF | `Thuringite_SMR-15.c_32um_NIC4aa_RREF` | 1.0 |
| 3152 | Epidote GDS26.a 75-200um   W9R4Nbbb RREF | `Epidote_GDS26.a_75-200um_NIC4bbb_RREF` | 1.0 |
| 10131 | Alun366+.50PyroPYS1A GDS222  W1R1Bb AREF | `Alun366+.50PyroPYS1A_GDS222_BECKb_AREF` | 0.9999 |
| 10851 | Kaol+Musc_intimate CU93-5C   W1R1Ba AREF | `Kaol+Muscov_intimate_CU93-5C_BECKa_AREF` | 1.0 |
| 10930 | Kaolin_Smect H89-FR-2 .5K  W5R4Nbb_ RREF | `Kaolin_Smect_H89-FR-2_.5Kao_NIC4bb_RREF` | 1.0 |
| 11106 | Muscov+Jaros CU93-314 coatng W1R1Bb AREF | `Muscov+Jaros_CU93-314_coatng_BECKb_AREF` | 1.0 |
| 10552 | Chlorite+Muscovite CU93-65A  W1R1Ba AREF | `Chlorite+Muscovite_CU93-65A_BECKa_AREF` | 1.0 |
| 1751 | Calcite WS272                W1R1Ba AREF | `Calcite_WS272_BECKa_AREF` | 0.9999 |
| 2986 | Dolomite HS102.3B            W1R1Bb AREF | `Dolomite_HS102.3B_BECKb_AREF` | 0.9999 |
| 8623 | Siderite HS271.3B            W1R1Ba AREF | `Siderite_HS271.3B_BECKa_AREF` | 1.0 |
| 10466 | Calcite.80+Mont_Swy-1 GDS212 W1R1Ba AREF | `Calcite.80+Mont_Swy-1_GDS212_BECKa_AREF` | 1.0 |
| 10477 | Calcite.80wt+Kaol_CM9 GDS213 W1R1Ba AREF | `Calcite.80wt+Kaol_CM9_GDS213_BECKa_AREF` | 0.9999 |
| 1900 | Chalcedony CU91-6A           W1R1Ba AREF | `Chalcedony_CU91-6A_BECKa_AREF` | 1.0 |
| 7243 | Opal TM8896 (Hyalite)      W5R4Naa_ RREF | `Opal_TM8896_(Hyalite)_NIC4aa_RREF` | 1.0 |
| 9744 | Tremolite HS18.3B          W9R4Nccc RREF | `Tremolite_HS18.3B_NIC4ccc_RREF` | 1.0 |
| 9092 | Talc GDS23 74-250um        W9R4Naaa RREF | `Talc_GDS23_74-250um_NIC4aaa_RREF` | 1.0 |
| 1265 | Antigorite NMNH96917.a >250  W1R1Bb AREF | `Antigorite_NMNH96917.a_gt250_BECKb_AREF` | 1.0 |
| 2196 | Chrysotile HS323.1B          W1R1Ba AREF | `Chrysotile_HS323.1B_BECKa_AREF` | 0.9999 |
| 9412 | Topaz HS184.3B               W1R1Bc AREF | `Topaz_HS184.3B_BECKb_AREF` | 0.9996 |

53 条中 51 条 r≥0.99（绝大多数 ≥0.9995）；最低为 illite_gds4（GDS4，r=0.9708）与 jarosite_K（GDS99，r=0.9827），均为 splib07 重测差异，裁决接受。**2026-08-31 更正（一）**：dry_veg_nongrass（rec 12794）曾按名称精确匹配误选 splib07 LP-Needles-3（r=0.8839）——该记录实为 USGS 新测的健康绿叶谱；06b 'LP-Needles-3' 的真正对应是 splib07 **LP-Needles-2**（编号重排，r=0.999995），已更正映射并重建 v07 黄金基线。**2026-08-31 更正（二）**：illite_gds4（rec 4625）原按同仪器策略选 Illite_GDS4_Marblehead_BECKb_AREF（r=0.9973），但 splib07 删除了其 1.35–1.42 µm 水汽吸收带（06b 有 100 个有效采样，BECKb 仅剩 5 个，npz 中线性桥接）；裁决改用同样品全覆盖记录 **Illite_GDS4_Marblehead_ASDNGb_AREF**（1.4 µm 带 101 个真实采样、整数 nm 网格恒等烘焙，全段 r=0.9708）——规则特征窗（2.2/2.35 µm）内两记录与 06b 几乎重合，分类行为影响可忽略，已重建 v07 黄金基线。

## 混合谱处理

- **12 条线性合成规则**：不烘焙——引擎在传感器网格重采样端元后才加权合成（`get_resample` 既有顺序），v07 轨道沿用同一口径，端元换为新参考即自动重算，无第二套插值代码。
- **2 条权重 1.0 别名规则**（`calcite.8+montmorilloniteNa.2_mix_intimate`→GDS212、`kaolinite.2+calcite.8_mix_intimate`→GDS213）：直接引用 splib07 同名**实测**物理混合记录。
- **5 条 AMX 别名规则**：配方与 splib07 AMX 预计算面积混合记录同样品同配比，烘焙后以权重 1.0 别名接入（合成 rec id 90000+AMX 编号），不再由端元合成。

| mix_id | 规则 | AMX 记录 | r(v07 合成) | max\|Δ\| | r(06b 合成) |
|---|---|---|---|---|---|
| mix_7821 | calcite.5+dolomite.5 | `Calcite.5+Dolomite.5_AMX8_ASDNGb_AREF` | 0.9944 | 0.0636 | 0.9946 |
| mix_7715 | dolomite.5+montmorilloniteCa.5 | `Dolomite.5+Ca-Mont.5_AMX10_ASDNGb_AREF` | 0.9655 | 0.0667 | 0.9653 |
| mix_7711 | dolomite.5+montmorilloniteNa.5 | `Dolomite.5+Na-Mont.5_AMX21_ASDNGb_AREF` | 0.9618 | 0.0695 | 0.9616 |
| mix_7745 | kaolinite.5+muscoviteMedhighAl.5 | `Kaol_Wxl+0.5Musc_Ruby_AMX12_ASDNGa_AREF` | 0.9758 | 0.2074 | 0.9757 |
| mix_7737 | pyrophyllite.25+kaolinite.75 | `Pyrophyl.25+wxlKaol.75_AMX17_ASDNGb_AREF` | 0.9182 | 0.1909 | 0.9181 |

r<1 的原因：AMX 由 USGS 用其自择端元记录预先计算，并非本选谱表端元的数值加权和（对 06b 端元合成同样 r≈0.92–0.99，差异不来自 06b→07 重测）；max\|Δ\| 为 EMIT 网格上与 v07 端元合成谱的最大绝对差。**拒绝的 3 条 AMX 映射**（端元样品与 .mcf 配方不一致，维持端元合成）：AMX3/AMX13 用 KGa-1 ≠ 5167(KGa-2)（mix_7703/mix_7741）；AMX14 用 HS295 ≠ 596(GDS96)（mix_7707）。

## 行为差异实证

1. **烘焙口径**（`docs/splib07_export_audit.md`）：1 nm 主网格分段线性烘焙对 ASD/整数对齐记录为逐位恒等；高斯核重采样下 BECK 10 nm→1 nm 稠密化**非无损**（EMIT 网格 max|Δ| 普遍 ≤2e-2，最大 1.03e-1 于 Topaz 陡沿，r≥0.996），NIC4 ~0.93→1 nm 降采样最大 8.5e-3。烘焙同时按构造消除 BECK 粗采样的 FWHM 窗空洞（遗产空洞填平，新增空洞为 0）。
2. **场景双跑**（`docs/splib07_dualrun_diff.md`，EMIT 全场景 1,589,760 像元）：分类图差异 mus 1.433% / chl 0.006% / cal 0.296%；吸收中心连续层 Δ 中位数=0（max 1.9 nm mus / 24.7 nm cal）；99.3% 的 mus 图新增像元是方解石（+混合）→方解石+白云母混合的族间仲裁边缘漂移；cal 差异放大（0.078%→0.297%）几乎全部是 AMX8/10/21 接入的直接效应（AMX 前后 v07 黄金对比：cal 0.231%）——最大单一迁移为 1,630 个像元由 `dolomite_abundant`翻转至 `calcite.5+dolomite.5` 后、吸收中心按新胜出规则连续统窗口重拟合跨过 2.323 µm bin 界的同族 bin 级平移（AMX8 与端元合成谱中心仅差 +0.3 nm，非参考谱中心漂移）。差异有界、可归因。

## 既有结论不变

- `docs/MCF_vs_rfjson_verification.md` 的全部结论绑定 rf.json，不受本轨道影响；
- 黄金基线双轨独立：`tests/golden_arrays.npz`（legacy）与 `tests/golden_arrays_v07.npz`（v07）。
