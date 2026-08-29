# splib07 迁移 · 阶段1 选谱表与特征覆盖校验

> 日期：2026-08-29 ｜ 脚本：`docs/_splib07_stage1_selection.py` ｜ 数据：`docs/splib07_selection.json`
> 策略 D1-A：同仪器+同测量类型优先，组内质量最高、r 最高者胜出。
> 覆盖判据（引擎口径）：splib07 记录先按 D2 增补烘焙到 1 nm 主网格（分段线性插值、量程外 NaN、内部删除带线性桥接——烘焙后 Beckman 10 nm 采样的FWHM 窗空洞按构造消失），再与 06b 原始谱一同经引擎 `_resample_` 重采样到真实 EMIT 波段网格；规则特征区间内，splib07 在 06b 非 NaN 的每个 EMIT 波段必须同样非 NaN——继承自 06b 的空洞（删水带等）视为遗产，仅新增空洞判失败。

| splib06b rec | 使用规则 | splib06b 标题 | 选定 splib07 记录 | r | 覆盖 |
|---|---|---|---|---|---|
| 12539 | vegetation_green | Engelmann-Spruce ES-Needls-1 W1R1Fa AREF | `Engelmann-Spruce_ES-Needls-1_ASDFRa_AREF` | 1.0 | ✓ |
| 13411 | vegetation_npv_and_green | Rangeland C04-170 S30% G24%  W1R1Fa AREF | `Rangeland_C04-170_S30%_G24%_ASDFRa_AREF` | 1.0 | ✓ |
| 11541 | snow_melting | Melting_snow mSnw1a          W1R1Fa AREF | `Melting_snow_mSnw01a_ASDFRa_AREF` | 1.0 | ✓ |
| 11589 | snow_slush | Melting_snow mSnw9  (slush)  W1R1Fa AREF | `Melting_snow_mSnw09_(slush)_ASDFRa_AREF` | 1.0 | ✓ |
| 11607 | water | Seawater_Coast_Chl SW1       W1R1Ba AREF | `Seawater_Coast_Chl_SW1_BECKa_AREF` | 1.0 | ✓ |
| 11647 | water_sediment_high | Water+Montmor SWy-2+5.01g/l  W1R1Fa AREF | `Water+Montmor_SWy-2+5.01g-l_ASDFRa_AREF` | 1.0 | ✓ |
| 11629 | water_sediment_low | Water+Montmor SWy-2+0.5g/l   W1R1Fa AREF | `Water+Montmor_SWy-2+0.50g-l_ASDFRa_AREF` | 1.0 | ✓ |
| 12658 | dry_veg_grass, dry_veg_grass_2_3um | Grass_Golden_Dry GDS480      W1R1Fa AREF | `Grass_Golden_Dry_GDS480_ASDFRa_AREF` | 1.0 | ✓ |
| 12794 | dry_veg_nongrass, dry_veg_nongrass_2_3um | Lodgepole-Pine LP-Needles-3  W1R1Fa AREF | `Lodgepole-Pine_LP-Needles-3_ASDFRa_AREF` | 0.8839 | ✓ |
| 6258 | muscovite_lowAl | Muscovite CU93-1 low-Al Phyl W2R4Nb RREF | `Muscovite_CU93-1_low-Al_Phyl_NIC4b_RREF` | 1.0 | ✓ |
| 11117 | muscovite_medAl | Muscovite CU91-250A med Al   W2R4Nb RREF | `Muscovite-medlowAl_CU91-250A_NIC4b_RREF` | 1.0 | ✓ |
| 6348 | muscovite_medhighAl | Muscovite GDS113 Ruby      W9R4Nbbb RREF | `Muscovite_GDS113_Ruby_NIC4aaa_RREF` | 1.0 | ✓ |
| 6394 | muscovite_Fe-rich | Muscovite GDS116 Tanzania  W9R4Naaa RREF | `Muscovite_GDS116_Tanzania_NIC4aaa_RREF` | 1.0 | ✓ |
| 4693 | illite_imt1 | Illite IMt-1.b <2um          W1R1Ba AREF | `Illite_IMt-1.b_lt2um_BECKa_AREF` | 1.0 | ✓ |
| 4625 | illite_gds4 | Illite GDS4 (Marblehead)     W1R1Bb AREF | `Illite_GDS4_Marblehead_BECKb_AREF` | 0.9973 | ✓ |
| 5088 | kaolinite_wxl | Kaolinite CM9              W9R4Nbbb RREF | `Kaolinite_CM9_NIC4bbb_RREF` | 1.0 | ✓ |
| 5167 | kaolinite_pxl | Kaolinite KGa-2 (pxl)      W9R4Nbbb RREF | `Kaolinite_KGa-2_(pxl)_NIC4bbb_RREF` | 1.0 | ✓ |
| 3869 | kaolinite+clay_mica_or_halloysite | Halloysite NMNH106237      W9R4Naaa RREF | `Halloysite_NMNH106237_NIC4aaa_RREF` | 1.0 | ✓ |
| 2872 | kaolinite_or_dickite | Dickite NMNH106242         W5R4Nbb_ RREF | `Dickite_NMNH106242_NIC4bb_RREF` | 1.0 | ✓ |
| 1632 | buddingtonite | Buddingtonite GDS85 D-206    W1R1Bb AREF | `Buddingtonite_GDS85_D-206_BECKb_AREF` | 1.0 | ✓ |
| 10350 | buddingtonite+montmorillonite_mix_intimate | Buddingtnt+Na-Mont CU93-260B W2R4Nb RREF | `Buddingtnt+Na-Mont_CU93-260B_NIC4b_RREF` | 1.0 | ✓ |
| 596 | alunite_K_250C | Alunite GDS96 K  Syn (250C)  W2R4Na RREF | `Alunite_GDS96_K_Syn_(250C)_NIC4a_RREF` | 1.0 | ✓ |
| 655 | alunite_Na_450C | Alunite RES-3 Na Syn (450C)  W2R4Na RREF | `Alunite_RES-3_Na_Syn_(450C)_NIC4a_RREF` | 1.0 | ✓ |
| 7893 | pyrophyllite | Pyrophyllite PYS1A <850um    W2R4Na RREF | `Pyrophyllite_PYS1A_lt850um_NIC4aaa_RREF` | 1.0 | ✓ |
| 4819 | jarosite_Na | Jarosite GDS24 Na          W9R4Nbbb RREF | `Jarosite_GDS24_Na_NIC4bbb_RREF` | 1.0 | ✓ |
| 4875 | jarosite_K | Jarosite GDS99 K 200C Syn    W2R4Na RREF | `Jarosite_GDS99_K_200C_Syn_NIC4aa_RREF` | 0.9827 | ✓ |
| 6200 | montmorillonite_Na | Montmorillonite SWy-1      W9R4Nbcc RREF | `Montmorillonite_SWy-1_NIC4bcc_RREF` | 1.0 | ✓ |
| 6120 | montmorillonite_Ca | Montmorillonite SAz-1      W5R4Nbb_ RREF | `Montmorillonite_SAz-1_NIC4bb_RREF` | 1.0 | ✓ |
| 6772 | nontronite | Nontronite NG-1.b <2um fr  W5R4Nbb_ RREF | `Nontronite_NG-1.b_lt2um_fr_NIC4bb_RREF` | 1.0 | ✓ |
| 3913 | hectorite | Hectorite SHCa-1.Ac-B      W5R4Nbb_ RREF | `Hectorite_SHCa-1.Ac-B_NIC4bb_RREF` | 1.0 | ✓ |
| 3767 | gypsum | Gypsum HS333.3B (Selenite) W9R4Naaa RREF | `Gypsum_HS333.3B_(Selenite)_NIC4aaa_RREF` | 1.0 | ✓ |
| 2047 | chlorite_lowFe | Chlorite SMR-13.a 104-150    W1R1Ba AREF | `Chlorite_SMR-13.a_104-150um_BECKa_AREF` | 1.0 | ✓ |
| 2253 | clinochlore | Clinochlore GDS158 Flagst  W5R4Nbb_ RREF | `Clinochlore_GDS158_Flagstaff_NIC4bb_RREF` | 1.0 | ✓ |
| 2371 | clinochlore_Fe | Clinochlore_Fe SC-CCa-1.a  W5R4Naa_ RREF | `Clinochlore_Fe_SC-CCa-1.a_NIC4aa_RREF` | 1.0 | ✓ |
| 9262 | thuringite | Thuringite SMR-15.c  32um  W5R4Naa_ RREF | `Thuringite_SMR-15.c_32um_NIC4aa_RREF` | 1.0 | ✓ |
| 3152 | epidote | Epidote GDS26.a 75-200um   W9R4Nbbb RREF | `Epidote_GDS26.a_75-200um_NIC4bbb_RREF` | 1.0 | ✓ |
| 10131 | pyrophyllite.5+alunite.5_mix_intimate | Alun366+.50PyroPYS1A GDS222  W1R1Bb AREF | `Alun366+.50PyroPYS1A_GDS222_BECKb_AREF` | 0.9999 | ✓ |
| 10851 | kaolinite+muscovite_mix_intimate | Kaol+Musc_intimate CU93-5C   W1R1Ba AREF | `Kaol+Muscov_intimate_CU93-5C_BECKa_AREF` | 1.0 | ✓ |
| 10930 | kaolinite+smectite_mix_intimate | Kaolin_Smect H89-FR-2 .5K  W5R4Nbb_ RREF | `Kaolin_Smect_H89-FR-2_.5Kao_NIC4bb_RREF` | 1.0 | ✓ |
| 11106 | jarosite+muscovite_mix_intimate | Muscov+Jaros CU93-314 coatng W1R1Bb AREF | `Muscov+Jaros_CU93-314_coatng_BECKb_AREF` | 1.0 | ✓ |
| 10552 | chlorite+muscovite_mix_intimate | Chlorite+Muscovite CU93-65A  W1R1Ba AREF | `Chlorite+Muscovite_CU93-65A_BECKa_AREF` | 1.0 | ✓ |
| 1751 | calcite_abundant, calcite | Calcite WS272                W1R1Ba AREF | `Calcite_WS272_BECKa_AREF` | 0.9999 | ✓ |
| 2986 | dolomite_abundant, dolomite | Dolomite HS102.3B            W1R1Bb AREF | `Dolomite_HS102.3B_BECKb_AREF` | 0.9999 | ✓ |
| 8623 | carbonate_Fe_bearing | Siderite HS271.3B            W1R1Ba AREF | `Siderite_HS271.3B_BECKa_AREF` | 1.0 | ✓ |
| 10466 | calcite.8+montmorilloniteNa.2_mix_intimate | Calcite.80+Mont_Swy-1 GDS212 W1R1Ba AREF | `Calcite.80+Mont_Swy-1_GDS212_BECKa_AREF` | 1.0 | ✓ |
| 10477 | kaolinite.2+calcite.8_mix_intimate | Calcite.80wt+Kaol_CM9 GDS213 W1R1Ba AREF | `Calcite.80wt+Kaol_CM9_GDS213_BECKa_AREF` | 0.9999 | ✓ |
| 1900 | chalcedony | Chalcedony CU91-6A           W1R1Ba AREF | `Chalcedony_CU91-6A_BECKa_AREF` | 1.0 | ✓ |
| 7243 | hydrated_silica | Opal TM8896 (Hyalite)      W5R4Naa_ RREF | `Opal_TM8896_(Hyalite)_NIC4aa_RREF` | 1.0 | ✓ |
| 9744 | tremolite_or_talc | Tremolite HS18.3B          W9R4Nccc RREF | `Tremolite_HS18.3B_NIC4ccc_RREF` | 1.0 | ✓ |
| 9092 | talc_or_tremolite | Talc GDS23 74-250um        W9R4Naaa RREF | `Talc_GDS23_74-250um_NIC4aaa_RREF` | 1.0 | ✓ |
| 1265 | serpentine_antigorite_or_calcite+dolomite, serpentine_antigorite_withironfeat, serpentine_antigorite_withsecondfeat | Antigorite NMNH96917.a >250  W1R1Bb AREF | `Antigorite_NMNH96917.a_gt250_BECKb_AREF` | 1.0 | ✓ |
| 2196 | serpentine_chrysotile, serpentine_chrysotile_withsecondfeat | Chrysotile HS323.1B          W1R1Ba AREF | `Chrysotile_HS323.1B_BECKa_AREF` | 0.9999 | ✓ |
| 9412 | topaz | Topaz HS184.3B               W1R1Bc AREF | `Topaz_HS184.3B_BECKb_AREF` | 0.9996 | ✓ |

唯一实物参考谱 53 条（51 条规则直接引用 + 2 条仅经权重 1.0 混合别名的 GDS212/213）；仪器匹配且特征全覆盖 53 条。规则面口径：77 条规则消费 70 条唯一重采样参考（51 直接 + 19 混合，7 条为复用——6 组共享）。

## 覆盖失败：无

## 合成混合端元检查（17 条线性合成规则）

全部端元均已选定 splib07 记录的规则：17/17

## 逐条裁决

- **dry_veg_nongrass(+_2_3um)**：splib07 LP-Needles-3 sole record r=0.884 (re-measurement) → accept splib07 record; caveat documented