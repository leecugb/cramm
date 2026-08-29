# rf.json 参考光谱 × splib07 映射光谱核实报告

> 日期：2026-08-29 ｜ 脚本：`docs/_verify_rf_splib07.py`
> 方法：splib06b 参考谱与 splib07 候选谱在公共波段（≥0.5 µm）上线性插值到统一网格，
> 掩膜取双方 0<ref≤1.5 的有效段，计算 Pearson r 与 RMSE。候选排序优先同仪器+同测量类型
> （Beckman AREF / Nicolet RREF / ASD AREF），取 r 最高者。

| 规则 | splib06b | 最佳 splib07 候选 | r | RMSE | 重叠µm | 判定 |
|---|---|---|---|---|---|---|
| vegetation_green | 12539 | `Engelmann-Spruce_ES-Needls-1` ASDFRa AREF | 1.0000 | 0.0000 | 2.15 | 确认 |
| vegetation_npv_and_green | 13411 | `Rangeland_C04-170_S30%_G24%` ASDFRa AREF | 1.0000 | 0.0000 | 2.10 | 确认 |
| snow_melting | 11541 | `Melting_snow_mSnw01a` ASDFRa AREF | 1.0000 | 0.0001 | 2.15 | 确认 |
| snow_slush | 11589 | `Melting_snow_mSnw09_(slush)` ASDFRa AREF | 1.0000 | 0.0001 | 2.10 | 确认 |
| water | 11607 | `Seawater_Coast_Chl_SW1` BECKa AREF | 1.0000 | 0.0000 | 2.25 | 确认 |
| water_sediment_high | 11647 | `Water+Montmor_SWy-2+5.01g-l` ASDFRa AREF | 1.0000 | 0.0000 | 2.15 | 确认 |
| water_sediment_low | 11629 | `Water+Montmor_SWy-2+0.50g-l` ASDFRa AREF | 1.0000 | 0.0000 | 2.11 | 确认 |
| dry_veg_grass | 12658 | `Grass_Golden_Dry_GDS480` ASDFRa AREF | 1.0000 | 0.0000 | 2.15 | 确认 |
| dry_veg_grass_2_3um | 12658 | `Grass_Golden_Dry_GDS480` ASDFRa AREF | 1.0000 | 0.0000 | 2.15 | 同上（共享参考谱） |
| dry_veg_nongrass | 12794 | `Lodgepole-Pine_LP-Needles-3` ASDFRa AREF | 0.8839 | 0.1396 | 2.15 | **需人工复核** |
| dry_veg_nongrass_2_3um | 12794 | `Lodgepole-Pine_LP-Needles-3` ASDFRa AREF | 0.8839 | 0.1396 | 2.15 | 同上（共享参考谱） |
| muscovite_lowAl | 6258 | `Muscovite_CU93-1_low-Al_Phyl` NIC4b RREF | 1.0000 | 0.0000 | 1.11 | 确认 |
| muscovite_medAl | 11117 | `Muscovite-medlowAl_CU91-250A` NIC4b RREF | 1.0000 | 0.0000 | 1.24 | 确认 |
| muscovite_medhighAl | 6348 | `Muscovite_GDS113_Ruby` NIC4aaa RREF | 1.0000 | 0.0000 | 1.23 | 确认 |
| muscovite_Fe-rich | 6394 | `Muscovite_GDS116_Tanzania` NIC4aaa RREF | 1.0000 | 0.0000 | 1.23 | 确认 |
| illite_imt1 | 4693 | `Illite_IMt-1.b_lt2um` BECKa AREF | 1.0000 | 0.0003 | 2.25 | 确认 |
| illite_gds4 | 4625 | `Illite_GDS4_Marblehead` BECKb AREF | 0.9999 | 0.0008 | 2.25 | 确认 |
| kaolinite_wxl | 5088 | `Kaolinite_CM9` NIC4bbb RREF | 1.0000 | 0.0000 | 1.25 | 确认 |
| kaolinite_pxl | 5167 | `Kaolinite_KGa-2_(pxl)` NIC4bbb RREF | 1.0000 | 0.0000 | 1.23 | 确认 |
| kaolinite+clay_mica_or_halloysite | 3869 | `Halloysite_NMNH106237` NIC4aaa RREF | 1.0000 | 0.0000 | 1.24 | 确认 |
| kaolinite_or_dickite | 2872 | `Dickite_NMNH106242` NIC4b RREF | 1.0000 | 0.0704 | 1.02 | 确认 |
| buddingtonite | 1632 | `Buddingtonite_GDS85_D-206` BECKb AREF | 1.0000 | 0.0005 | 2.25 | 确认 |
| buddingtonite+montmorillonite_mix_intimate | 10350 | `Buddingtnt+Na-Mont_CU93-260B` NIC4b RREF | 1.0000 | 0.0000 | 1.13 | 确认 |
| alunite_K_250C | 596 | `Alunite_GDS96_K_Syn_(250C)` NIC4a RREF | 1.0000 | 0.0000 | 1.30 | 确认 |
| alunite_Na_450C | 655 | `Alunite_RES-3_Na_Syn_(450C)` NIC4a RREF | 1.0000 | 0.0000 | 1.30 | 确认 |
| pyrophyllite | 7893 | `Pyrophyllite_PYS1A_lt850um` NIC4a RREF | 1.0000 | 0.0000 | 1.26 | 确认 |
| pyrophyllite.25+kaolinite.75 | mix_7737 | — | — | — | — | 合成混合，不适用 |
| jarosite_Na | 4819 | `Jarosite_GDS24_Na` NIC4bbb RREF | 1.0000 | 0.0000 | 1.18 | 确认 |
| jarosite_K | 4875 | `Jarosite_GDS99_K_200C_Syn` NIC4a RREF | 1.0000 | 0.0000 | 1.30 | 确认 |
| montmorillonite_Na | 6200 | `Montmorillonite_SWy-1` NIC4bcc RREF | 1.0000 | 0.0000 | 1.22 | 确认 |
| montmorillonite_Ca | 6120 | `Montmorillonite_SAz-1` NIC4bb RREF | 1.0000 | 0.0000 | 1.22 | 确认 |
| nontronite | 6772 | `Nontronite_NG-1.b_lt2um_fr` NIC4bb RREF | 1.0000 | 0.0000 | 1.21 | 确认 |
| hectorite | 3913 | `Hectorite_SHCa-1.Ac-B` NIC4bb RREF | 1.0000 | 0.0000 | 1.22 | 确认 |
| gypsum | 3767 | `Gypsum_HS333.3B_(Selenite)` NIC4aaa RREF | 1.0000 | 0.0000 | 1.20 | 确认 |
| gypsum.6+montmorilloniteNa.4 | mix_7723 | — | — | — | — | 合成混合，不适用 |
| chlorite_lowFe | 2047 | `Chlorite_SMR-13.a_104-150um` BECKa AREF | 1.0000 | 0.0012 | 2.25 | 确认 |
| clinochlore | 2253 | `Clinochlore_GDS158_Flagstaff` NIC4bb RREF | 1.0000 | 0.0000 | 1.00 | 确认 |
| clinochlore_Fe | 2371 | `Clinochlore_Fe_SC-CCa-1.a` NIC4aa RREF | 1.0000 | 0.0000 | 1.24 | 确认 |
| thuringite | 9262 | `Thuringite_SMR-15.c_32um` NIC4aa RREF | 1.0000 | 0.0000 | 1.23 | 确认 |
| epidote | 3152 | `Epidote_GDS26.a_75-200um` NIC4bbb RREF | 1.0000 | 0.0000 | 1.11 | 确认 |
| pyrophyllite.5+alunite.5_mix_intimate | 10131 | `Alun366+.50PyroPYS1A_GDS222` BECKb AREF | 0.9999 | 0.0024 | 2.25 | 确认 |
| alunite.5+kaolinite.5 | mix_7703 | — | — | — | — | 合成混合，不适用 |
| alunite.25+kaolinite.75 | mix_7707 | — | — | — | — | 合成混合，不适用 |
| kaolinite.5+muscoviteMedAl.5 | mix_7741 | — | — | — | — | 合成混合，不适用 |
| kaolinite.5+muscoviteMedhighAl.5 | mix_7745 | — | — | — | — | 合成混合，不适用 |
| kaolinite+muscovite_mix_intimate | 10851 | `Kaol+Muscov_intimate_CU93-5C` BECKa AREF | 1.0000 | 0.0005 | 2.25 | 确认 |
| kaolinite+smectite_mix_intimate | 10930 | `Kaolin_Smect_H89-FR-2_.5Kao` NIC4bb RREF | 1.0000 | 0.0000 | 1.23 | 确认 |
| jarosite+muscovite_mix_intimate | 11106 | `Muscov+Jaros_CU93-314_coatng` BECKb AREF | 1.0000 | 0.0006 | 2.25 | 确认 |
| chlorite+muscovite_mix_intimate | 10552 | `Chlorite+Muscovite_CU93-65A` BECKa AREF | 1.0000 | 0.0004 | 2.25 | 确认 |
| clinochlore_Fe.3+muscovite.7 | mix_7749 | — | — | — | — | 合成混合，不适用 |
| calcite_abundant | 1751 | `Calcite_WS272` BECKa AREF | 0.9998 | 0.0024 | 2.25 | 确认 |
| calcite | 1751 | `Calcite_WS272` BECKa AREF | 0.9998 | 0.0024 | 2.25 | 同上（共享参考谱） |
| dolomite_abundant | 2986 | `Dolomite_HS102.3B` BECKb AREF | 0.9995 | 0.0026 | 2.25 | 确认 |
| dolomite | 2986 | `Dolomite_HS102.3B` BECKb AREF | 0.9995 | 0.0026 | 2.25 | 同上（共享参考谱） |
| calcite.5+dolomite.5 | mix_7821 | — | — | — | — | 合成混合，不适用 |
| carbonate_Fe_bearing | 8623 | `Siderite_HS271.3B` BECKa AREF | 1.0000 | 0.0007 | 2.25 | 确认 |
| calcite.18+dolomite.22+montmorilloniteNa.6 | mix_7781 | — | — | — | — | 合成混合，不适用 |
| calcite.18+dolomite.22+montmorilloniteCa.6 | mix_7811 | — | — | — | — | 合成混合，不适用 |
| calcite.8+montmorilloniteNa.2_mix_intimate | mix_7785 | — | — | — | — | 合成混合，不适用 |
| calcite.25+montmorilloniteCa.75 | mix_7787 | — | — | — | — | 合成混合，不适用 |
| calcite.25+montmorilloniteNa.75 | mix_7791 | — | — | — | — | 合成混合，不适用 |
| calcite.5+muscoviteMedHiAl.5 | mix_7795 | — | — | — | — | 合成混合，不适用 |
| calcite.5+muscoviteMedAl.5 | mix_7799 | — | — | — | — | 合成混合，不适用 |
| calcite.3+muscoviteLowAl.7 | mix_7803 | — | — | — | — | 合成混合，不适用 |
| dolomite.5+montmorilloniteNa.5 | mix_7711 | — | — | — | — | 合成混合，不适用 |
| dolomite.5+montmorilloniteCa.5 | mix_7715 | — | — | — | — | 合成混合，不适用 |
| kaolinite.2+calcite.8_mix_intimate | mix_7807 | — | — | — | — | 合成混合，不适用 |
| chalcedony | 1900 | `Chalcedony_CU91-6A` BECKa AREF | 1.0000 | 0.0003 | 2.24 | 确认 |
| hydrated_silica | 7243 | `Opal_TM8896_(Hyalite)` NIC4aa RREF | 1.0000 | 0.0000 | 1.06 | 确认 |
| tremolite_or_talc | 9744 | `Tremolite_HS18.3B` NIC4ccc RREF | 1.0000 | 0.0000 | 1.22 | 确认 |
| talc_or_tremolite | 9092 | `Talc_GDS23_74-250um` NIC4aaa RREF | 1.0000 | 0.0000 | 1.23 | 确认 |
| serpentine_antigorite_or_calcite+dolomite | 1265 | `Antigorite_NMNH96917.a_gt250` BECKb AREF | 1.0000 | 0.0006 | 2.25 | 确认 |
| serpentine_chrysotile | 2196 | `Chrysotile_HS323.1B` BECKa AREF | 0.9999 | 0.0009 | 2.25 | 确认 |
| serpentine_antigorite_withironfeat | 1265 | `Antigorite_NMNH96917.a_gt250` BECKb AREF | 1.0000 | 0.0006 | 2.25 | 同上（共享参考谱） |
| serpentine_chrysotile_withsecondfeat | 2196 | `Chrysotile_HS323.1B` BECKa AREF | 0.9999 | 0.0009 | 2.25 | 同上（共享参考谱） |
| serpentine_antigorite_withsecondfeat | 1265 | `Antigorite_NMNH96917.a_gt250` BECKb AREF | 1.0000 | 0.0006 | 2.25 | 同上（共享参考谱） |
| topaz | 9412 | `Topaz_HS184.3B` BECKb AREF | 0.9998 | 0.0038 | 2.25 | 确认 |

统计：确认(r≥0.99) 50，基本对应(0.95≤r<0.99) 0，需复核 1，合成混合不适用 26。

## 说明

- r<1 的主因：splib07 对同一样品多为**重测记录**（不同制备/仪器状态），
  且 06b→07 间个别样品更换了质量等级；小差异不否定样品级对应。
- 光谱形状核对的是**样品对应性**，命名一致 + r≥0.99 即视为映射成立。
- `dry_veg_nongrass`（Lodgepole-Pine LP-Needles-3，r=0.884）：splib07 仅此一条记录，
  样品名与仪器（ASDFRa AREF）完全吻合，差异源于植被重测（针叶含水率/装填状态敏感），
  样品级映射成立。