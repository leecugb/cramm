# .mcf 与 rf_splib07.json 差异声明

> 日期：2026-08-29 ｜ 数据：`docs/splib07_selection.json`（逐条 r 值）、`docs/splib07_export_audit.md`（烘焙审计）、`docs/splib07_dualrun_diff.md`（场景双跑）

## 结论

rf_splib07.json 的 **77 条规则与 19 条混合配方同 rf.json 逐比特一致**（诊断特征参数、约束、权重原样继承 .mcf v6a 启用态，核验见 `docs/MCF_vs_rfjson_verification.md`）；唯一差异是**参考光谱来源**：splib06b 记录 → splib07 同名样品记录（53 条唯一实物参考，D1-A 同仪器+同测量类型选谱）。

因此 rf_splib07.json **不是**对 .mcf 的逐位保真移植——它是同规则、新参考的 v1.2.0 轨道；rf.json 保持不动，继续作为 .mcf 零差异保真基线。两轨道并存，由 `MicaEngine(rf_path=...)` 选择。

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
| 12794 | Lodgepole-Pine LP-Needles-3  W1R1Fa AREF | `Lodgepole-Pine_LP-Needles-3_ASDFRa_AREF` | 0.8839 |
| 6258 | Muscovite CU93-1 low-Al Phyl W2R4Nb RREF | `Muscovite_CU93-1_low-Al_Phyl_NIC4b_RREF` | 1.0 |
| 11117 | Muscovite CU91-250A med Al   W2R4Nb RREF | `Muscovite-medlowAl_CU91-250A_NIC4b_RREF` | 1.0 |
| 6348 | Muscovite GDS113 Ruby      W9R4Nbbb RREF | `Muscovite_GDS113_Ruby_NIC4aaa_RREF` | 1.0 |
| 6394 | Muscovite GDS116 Tanzania  W9R4Naaa RREF | `Muscovite_GDS116_Tanzania_NIC4aaa_RREF` | 1.0 |
| 4693 | Illite IMt-1.b <2um          W1R1Ba AREF | `Illite_IMt-1.b_lt2um_BECKa_AREF` | 1.0 |
| 4625 | Illite GDS4 (Marblehead)     W1R1Bb AREF | `Illite_GDS4_Marblehead_BECKb_AREF` | 0.9973 |
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

53 条中 51 条 r≥0.99（绝大多数 ≥0.9995）；最低为 dry_veg_nongrass（LP-Needles-3，r=0.8839）——splib07 仅存重测记录，裁决接受并在此声明（同 `docs/rfjson_splib07_verification.md`）。

## 混合谱处理

- **17 条线性合成规则**：不烘焙——引擎在传感器网格重采样端元后才加权合成（`get_resample` 既有顺序），v07 轨道沿用同一口径，端元换为新参考即自动重算，无第二套插值代码。
- **2 条权重 1.0 别名规则**（`calcite.8+montmorilloniteNa.2_mix_intimate`→GDS212、`kaolinite.2+calcite.8_mix_intimate`→GDS213）：直接引用 splib07 同名**实测**物理混合记录。

## 行为差异实证

1. **烘焙口径**（`docs/splib07_export_audit.md`）：1 nm 主网格分段线性烘焙对 ASD/整数对齐记录为逐位恒等；高斯核重采样下 BECK 10 nm→1 nm 稠密化**非无损**（EMIT 网格 max|Δ| 普遍 ≤2e-2，最大 1.03e-1 于 Topaz 陡沿，r≥0.996），NIC4 ~0.93→1 nm 降采样最大 8.5e-3。烘焙同时按构造消除 BECK 粗采样的 FWHM 窗空洞（遗产空洞填平，新增空洞为 0）。
2. **场景双跑**（`docs/splib07_dualrun_diff.md`，EMIT 全场景 1,589,760 像元）：分类图差异 mus 1.43% / chl 0.005% / cal 0.078%；吸收中心连续层 Δ 中位数=0（max 1.9 nm mus / 14 nm cal）；96.6% 的 mus 图新增像元是方解石+蒙脱石混合→方解石+白云母混合的族间仲裁边缘漂移。差异有界、可归因。

## 既有结论不变

- `docs/MCF_vs_rfjson_verification.md` 的全部结论绑定 rf.json，不受本轨道影响；
- 黄金基线双轨独立：`tests/golden_arrays.npz`（legacy）与 `tests/golden_arrays_v07.npz`（v07）。
