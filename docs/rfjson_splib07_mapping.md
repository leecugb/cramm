# rf.json 参考光谱 ↔ splib07 样本映射清单

> 生成日期：2026-08-29 ｜ 生成脚本：`docs/_map_rf_to_splib07_step2.py`
> 左侧为 CRAMM rf.json 规则（参考谱来自 splib06b，记录号 + 标题）；右侧为 splib07 中同样品名的全部记录。
> splib06b 与 splib07 是两套独立库：同名样品是同一物理样品的重测/再收录，记录并非逐条对应。

| rf.json 规则 | splib06b 记录 | splib06b 标题 | splib07 对应记录 |
|---|---|---|---|
| vegetation_green | 12539 | Engelmann-Spruce ES-Needls-1 W1R1Fa AREF | `Engelmann-Spruce_ES-Needls-1` ASDFRa AREF |
| vegetation_npv_and_green | 13411 | Rangeland C04-170 S30% G24%  W1R1Fa AREF | `Rangeland_C04-170_S30%_G24%` ASDFRa AREF |
| snow_melting | 11541 | Melting_snow mSnw1a          W1R1Fa AREF | `Melting_snow_mSnw01a+0.5_veg` ASDFRa AREF<br>`Melting_snow_mSnw01a` ASDFRa AREF |
| snow_slush | 11589 | Melting_snow mSnw9  (slush)  W1R1Fa AREF | `Melting_snow_mSnw09+0.5_veg` ASDFRa AREF<br>`Melting_snow_mSnw09_(slush)` ASDFRa AREF |
| water | 11607 | Seawater_Coast_Chl SW1       W1R1Ba AREF | `Seawater_Coast_Chl_SW1` BECKa AREF |
| water_sediment_high | 11647 | Water+Montmor SWy-2+5.01g/l  W1R1Fa AREF | `Water+Montmor_SWy-2+0.50g-l` ASDFRa AREF<br>`Water+Montmor_SWy-2+1.67g-l` ASDFRa AREF<br>`Water+Montmor_SWy-2+16.5g-l` ASDFRa AREF<br>`Water+Montmor_SWy-2+5.01g-l` ASDFRa AREF |
| water_sediment_low | 11629 | Water+Montmor SWy-2+0.5g/l   W1R1Fa AREF | `Water+Montmor_SWy-2+0.50g-l` ASDFRa AREF<br>`Water+Montmor_SWy-2+1.67g-l` ASDFRa AREF<br>`Water+Montmor_SWy-2+16.5g-l` ASDFRa AREF<br>`Water+Montmor_SWy-2+5.01g-l` ASDFRa AREF |
| dry_veg_grass | 12658 | Grass_Golden_Dry GDS480      W1R1Fa AREF | `Grass_Golden_Dry_GDS480` ASDFRa AREF |
| dry_veg_grass_2_3um | 12658 | Grass_Golden_Dry GDS480      W1R1Fa AREF | `Grass_Golden_Dry_GDS480` ASDFRa AREF |
| dry_veg_nongrass | 12794 | Lodgepole-Pine LP-Needles-3  W1R1Fa AREF | `Lodgepole-Pine_LP-Needles-3` ASDFRa AREF |
| dry_veg_nongrass_2_3um | 12794 | Lodgepole-Pine LP-Needles-3  W1R1Fa AREF | `Lodgepole-Pine_LP-Needles-3` ASDFRa AREF |
| muscovite_lowAl | 6258 | Muscovite CU93-1 low-Al Phyl W2R4Nb RREF | `Muscovite_CU93-1_low-Al_Phyl` NIC4b RREF |
| muscovite_medAl | 11117 | Muscovite CU91-250A med Al   W2R4Nb RREF | `Muscovite-medlowAl_CU91-250A` ASDFRb AREF<br>`Muscovite-medlowAl_CU91-250A` ASDNGb AREF<br>`Muscovite-medlowAl_CU91-250A` NIC4b RREF<br>`Kaol.5+MuscCU91-250A_AMX13` ASDNGb AREF<br>`Kaol.5+MuscCU91-250A_AMX13` BECKb AREF<br>`Kaol.5+MuscCU91-250A_AMX13` NIC4b AREF<br>`Alunite.5+MuscCU91-250A_AMX4` ASDNGa AREF<br>`Alunite.5+MuscCU91-250A_AMX4` BECKa AREF |
| muscovite_medhighAl | 6348 | Muscovite GDS113 Ruby      W9R4Nbbb RREF | `Muscovite_GDS113_Ruby` ASDNGa AREF<br>`Muscovite_GDS113_Ruby` BECKa AREF<br>`Muscovite_GDS113_Ruby` NIC4aaa RREF<br>`Muscovite_GDS113a_Ruby` ASDNGa AREF |
| muscovite_Fe-rich | 6394 | Muscovite GDS116 Tanzania  W9R4Naaa RREF | `Muscovite_GDS116_Tanzania` ASDNGa AREF<br>`Muscovite_GDS116_Tanzania` BECKa AREF<br>`Muscovite_GDS116_Tanzania` NIC4aaa RREF<br>`Muscovite_GDS116a_Tanzania` ASDNGa AREF |
| illite_imt1 | 4693 | Illite IMt-1.b <2um          W1R1Ba AREF | `Illite_IMt-1.a` ASDNGb AREF<br>`Illite_IMt-1.a` BECKb AREF<br>`Illite_IMt-1.a` NIC4bb RREF<br>`Illite_IMt-1.b_lt2um` ASDNGa AREF<br>`Illite_IMt-1.b_lt2um` BECKa AREF<br>`Illite_IMt-1.b_lt2um` NIC4aa RREF |
| illite_gds4 | 4625 | Illite GDS4 (Marblehead)     W1R1Bb AREF | `Illite_GDS4_Marblehead` ASDNGb AREF<br>`Illite_GDS4_Marblehead` BECKb AREF<br>`Illite_GDS4_Marblehead` NIC4bb RREF<br>`Illite_GDS4.2_Marblehead` ASDNGb AREF |
| kaolinite_wxl | 5088 | Kaolinite CM9              W9R4Nbbb RREF | `Kaolinite_CM9` ASDNGb AREF<br>`Calcite.80wt+Kaol_CM9_GDS213` ASDNGa AREF<br>`Kaolinite_CM9` BECKb AREF<br>`Calcite.80wt+Kaol_CM9_GDS213` BECKa AREF<br>`Kaolinite_CM9` NIC4bbb RREF<br>`Kaolinite_CM9` NIC4b RREF |
| kaolinite_pxl | 5167 | Kaolinite KGa-2 (pxl)      W9R4Nbbb RREF | `Kaolinite_KGa-2_(pxl)` ASDNGb AREF<br>`Kaolinite_KGa-2_(pxl)` BECKb AREF<br>`Kaolinite_KGa-2_(pxl)` NIC4bbb RREF<br>`Kaolinite_KGa-2_(pxl)` NIC4b RREF |
| kaolinite+clay_mica_or_halloysite | 3869 | Halloysite NMNH106237      W9R4Naaa RREF | `Halloysite_NMNH106237` ASDNGa AREF<br>`Halloysite_NMNH106237` BECKa AREF<br>`Halloysite_NMNH106237` NIC4aaa RREF<br>`Halloysite_NMNH106237` NIC4a RREF |
| kaolinite_or_dickite | 2872 | Dickite NMNH106242         W5R4Nbb_ RREF | `Dickite_NMNH106242` ASDNGb AREF<br>`Dickite_NMNH106242` BECKb AREF<br>`Dickite_NMNH106242` NIC4bb RREF<br>`Dickite_NMNH106242` NIC4b RREF |
| buddingtonite | 1632 | Buddingtonite GDS85 D-206    W1R1Bb AREF | `Buddingtonite_GDS85_D-206` BECKb AREF |
| buddingtonite+montmorillonite_mix_intimate | 10350 | Buddingtnt+Na-Mont CU93-260B W2R4Nb RREF | `Buddingtnt+Na-Mont_CU93-260B` NIC4b RREF |
| alunite_K_250C | 596 | Alunite GDS96 K  Syn (250C)  W2R4Na RREF | `Alunite_GDS96_K_Syn_(250C)` NIC4a RREF |
| alunite_Na_450C | 655 | Alunite RES-3 Na Syn (450C)  W2R4Na RREF | `Alunite_RES-3_Na_Syn_(450C)` NIC4a RREF |
| pyrophyllite | 7893 | Pyrophyllite PYS1A <850um    W2R4Na RREF | `Pyrophyllite_PYS1A_gt250um` ASDNGa AREF<br>`Pyrophyllite_PYS1A_lt5um` ASDNGa AREF<br>`Pyrophyllite_PYS1A_lt850um` ASDNGa AREF<br>`Pyrophyllite_PYS1A_fine_gr` BECKa AREF<br>`Pyrophyllite_PYS1A_lt850um` BECKa AREF<br>`Pyrophyllite_PYS1A_fine_gr` NIC4aaa RREF<br>`Pyrophyllite_PYS1A_lt850um` NIC4aaa RREF<br>`Pyrophyllite_PYS1A_lt850um` NIC4a RREF<br>`Alun366+.50PyroPYS1A_GDS222` BECKb AREF |
| pyrophyllite.25+kaolinite.75 | mix_7737 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| jarosite_Na | 4819 | Jarosite GDS24 Na          W9R4Nbbb RREF | `Jarosite_GDS24_Na` BECKb AREF<br>`Jarosite_GDS24_Na` NIC4bbb RREF |
| jarosite_K | 4875 | Jarosite GDS99 K 200C Syn    W2R4Na RREF | `Jarosite_GDS99_K_200C_Syn` BECKa AREF<br>`Jarosite_GDS99_K_200C_Syn` NIC4aa RREF<br>`Jarosite_GDS99_K_200C_Syn` NIC4a RREF |
| montmorillonite_Na | 6200 | Montmorillonite SWy-1      W9R4Nbcc RREF | `Montmorillonite_SWy-1` ASDNGb AREF<br>`Montmorillonite_SWy-1` BECKb AREF<br>`Montmorillonite_SWy-1` NIC4bcc RREF |
| montmorillonite_Ca | 6120 | Montmorillonite SAz-1      W5R4Nbb_ RREF | `Montmorillonite_SAz-1` ASDNGb AREF<br>`Montmorillonite_SAz-1` BECKb AREF<br>`Montmorillonite_SAz-1` NIC4bb RREF |
| nontronite | 6772 | Nontronite NG-1.b <2um fr  W5R4Nbb_ RREF | `Nontronite_NG-1.a` ASDNGb AREF<br>`Nontronite_NG-1.a` BECKb AREF<br>`Nontronite_NG-1.a` NIC4cd RREF<br>`Nontronite_NG-1.b_lt2um_fr` BECKb AREF<br>`Nontronite_NG-1.b_lt2um_fr` NIC4bb RREF |
| hectorite | 3913 | Hectorite SHCa-1.Ac-B      W5R4Nbb_ RREF | `Hectorite_SHCa-1` ASDNGc AREF<br>`Hectorite_SHCa-1` BECKc AREF<br>`Hectorite_SHCa-1.Ac-B` BECKb AREF<br>`Hectorite_SHCa-1.Ac-B` NIC4bb RREF |
| gypsum | 3767 | Gypsum HS333.3B (Selenite) W9R4Naaa RREF | `Gypsum_HS333.3B_(Selenite)` ASDFRa AREF<br>`Gypsum_HS333.3B_(Selenite)` ASDNGa AREF<br>`Gypsum_HS333.3B_(Selenite)` BECKa AREF<br>`Gypsum_HS333.3B_(Selenite)` NIC4aaa RREF |
| gypsum.6+montmorilloniteNa.4 | mix_7723 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| chlorite_lowFe | 2047 | Chlorite SMR-13.a 104-150    W1R1Ba AREF | `Chlorite_SMR-13.a_104-150um` BECKa AREF<br>`Chlorite_SMR-13.a_104-150um` NIC4aa RREF<br>`Chlorite_SMR-13.a_104-150um` NIC4a RREF<br>`Chlorite_SMR-13.b_60-104um` BECKa AREF<br>`Chlorite_SMR-13.c_45-60um` BECKa AREF<br>`Chlorite_SMR-13.c_45-60um` NIC4aa RREF<br>`Chlorite_SMR-13.d_30-45um` BECKa AREF<br>`Chlorite_SMR-13.d_30-45um` NIC4aa RREF<br>`Chlorite_SMR-13.e_lt30um` BECKb AREF<br>`Chlorite_SMR-13.e_lt30um` NIC4bb RREF |
| clinochlore | 2253 | Clinochlore GDS158 Flagst  W5R4Nbb_ RREF | `Clinochlore_GDS158_Flagstaff` ASDNGb AREF<br>`Clinochlore_GDS158_Flagstaff` BECKb AREF<br>`Clinochlore_GDS158_Flagstaff` NIC4bb RREF |
| clinochlore_Fe | 2371 | Clinochlore_Fe SC-CCa-1.a  W5R4Naa_ RREF | `Clinochlore_Fe_SC-CCa-1.a` BECKa AREF<br>`Clinochlore_Fe_SC-CCa-1.b` BECKa AREF<br>`Clinochlore_Fe_SC-CCa-1.c` BECKa AREF<br>`Clinochlore_Fe_SC-CCa-1.a` NIC4aa RREF<br>`Clinochlore_Fe_SC-CCa-1.b` NIC4aa RREF<br>`Clinochlore_Fe_SC-CCa-1.c` NIC4aa RREF |
| thuringite | 9262 | Thuringite SMR-15.c  32um  W5R4Naa_ RREF | `Thuringite_SMR-15.a_115um` BECKb AREF<br>`Thuringite_SMR-15.a_115um` NIC4bc RREF<br>`Thuringite_SMR-15.b_80um` BECKa AREF<br>`Thuringite_SMR-15.b_80um` NIC4aa RREF<br>`Thuringite_SMR-15.b_80um` NIC4a RREF<br>`Thuringite_SMR-15.c_32um` NIC4aa RREF<br>`Thuringite_SMR-15.d_lt30um` BECKa AREF<br>`Thuringite_SMR-15.d_lt30um` NIC4aa RREF |
| epidote | 3152 | Epidote GDS26.a 75-200um   W9R4Nbbb RREF | `Epidote_GDS26.a_75-200um` ASDNGb AREF<br>`Epidote_GDS26.a_75-200um` BECKb AREF<br>`Epidote_GDS26.a_75-200um` NIC4bbb RREF<br>`Epidote_GDS26.b_lt75um` ASDNGb AREF<br>`Epidote_GDS26.b_lt75um` BECKb AREF |
| pyrophyllite.5+alunite.5_mix_intimate | 10131 | Alun366+.50PyroPYS1A GDS222  W1R1Bb AREF | `Alun366+.50PyroPYS1A_GDS222` BECKb AREF |
| alunite.5+kaolinite.5 | mix_7703 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| alunite.25+kaolinite.75 | mix_7707 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| kaolinite.5+muscoviteMedAl.5 | mix_7741 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| kaolinite.5+muscoviteMedhighAl.5 | mix_7745 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| kaolinite+muscovite_mix_intimate | 10851 | Kaol+Musc_intimate CU93-5C   W1R1Ba AREF | `Kaol+Muscov_intimate_CU93-5C` ASDNGa AREF<br>`Kaol+Muscov_intimate_CU93-5C` BECKa AREF |
| kaolinite+smectite_mix_intimate | 10930 | Kaolin_Smect H89-FR-2 .5K  W5R4Nbb_ RREF | `Kaolin_Smect_H89-FR-2_.5Kaol` BECKb AREF<br>`Kaolin_Smect_H89-FR-2_.5Kao` NIC4bb RREF |
| jarosite+muscovite_mix_intimate | 11106 | Muscov+Jaros CU93-314 coatng W1R1Bb AREF | `Muscov+Jaros_CU93-314_coatng` ASDNGb AREF<br>`Muscov+Jaros_CU93-314_coatng` BECKb AREF |
| chlorite+muscovite_mix_intimate | 10552 | Chlorite+Muscovite CU93-65A  W1R1Ba AREF | `Chlorite+Muscovite_CU93-65A` ASDNGa AREF<br>`Chlorite+Muscovite_CU93-65A` BECKa AREF |
| clinochlore_Fe.3+muscovite.7 | mix_7749 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| calcite_abundant | 1751 | Calcite WS272                W1R1Ba AREF | `Calcite_WS272` ASDNGa AREF<br>`Calcite_WS272` BECKa AREF<br>`Calcite_WS272` NIC4aaa RREF |
| calcite | 1751 | Calcite WS272                W1R1Ba AREF | `Calcite_WS272` ASDNGa AREF<br>`Calcite_WS272` BECKa AREF<br>`Calcite_WS272` NIC4aaa RREF |
| dolomite_abundant | 2986 | Dolomite HS102.3B            W1R1Bb AREF | `Dolomite_HS102.3B` ASDNGb AREF<br>`Dolomite_HS102.3B` BECKb AREF<br>`Dolomite_HS102.3B` NIC4bbb RREF |
| dolomite | 2986 | Dolomite HS102.3B            W1R1Bb AREF | `Dolomite_HS102.3B` ASDNGb AREF<br>`Dolomite_HS102.3B` BECKb AREF<br>`Dolomite_HS102.3B` NIC4bbb RREF |
| calcite.5+dolomite.5 | mix_7821 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| carbonate_Fe_bearing | 8623 | Siderite HS271.3B            W1R1Ba AREF | `Siderite_HS271.3B` ASDFRa AREF<br>`Siderite_HS271.3B` ASDNGa AREF<br>`Siderite_HS271.3B` BECKa AREF<br>`Siderite_HS271.3B` NIC4aa RREF |
| calcite.18+dolomite.22+montmorilloniteNa.6 | mix_7781 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| calcite.18+dolomite.22+montmorilloniteCa.6 | mix_7811 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| calcite.8+montmorilloniteNa.2_mix_intimate | mix_7785 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| calcite.25+montmorilloniteCa.75 | mix_7787 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| calcite.25+montmorilloniteNa.75 | mix_7791 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| calcite.5+muscoviteMedHiAl.5 | mix_7795 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| calcite.5+muscoviteMedAl.5 | mix_7799 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| calcite.3+muscoviteLowAl.7 | mix_7803 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| dolomite.5+montmorilloniteNa.5 | mix_7711 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| dolomite.5+montmorilloniteCa.5 | mix_7715 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| kaolinite.2+calcite.8_mix_intimate | mix_7807 | 合成混合（rf.json 内置，无 splib06b 记录） | —（合成） |
| chalcedony | 1900 | Chalcedony CU91-6A           W1R1Ba AREF | `Chalcedony_CU91-6A` ASDNGa AREF<br>`Chalcedony_CU91-6A` BECKa AREF<br>`Chalcedony_CU91-6A_XRD` NIC4aa RREF |
| hydrated_silica | 7243 | Opal TM8896 (Hyalite)      W5R4Naa_ RREF | `Opal_TM8896_(Hyalite)` ASDNGa AREF<br>`Opal_TM8896_(Hyalite)` BECKa AREF<br>`Opal_TM8896_(Hyalite)` NIC4aa RREF |
| tremolite_or_talc | 9744 | Tremolite HS18.3B          W9R4Nccc RREF | `Tremolite_HS18.3B` ASDFRc AREF<br>`Tremolite_HS18.3B` NIC4ccc RREF |
| talc_or_tremolite | 9092 | Talc GDS23 74-250um        W9R4Naaa RREF | `Talc_GDS23` ASDNGa AREF<br>`Talc_GDS23_74-250um_fr` BECKa AREF<br>`Talc_GDS23_74-250um` NIC4aaa RREF |
| serpentine_antigorite_or_calcite+dolomite | 1265 | Antigorite NMNH96917.a >250  W1R1Bb AREF | `Antigorite_NMNH96917.a_gt250` ASDNGb AREF<br>`Antigorite_NMNH96917.a_gt250` BECKb AREF<br>`Antigorite_NMNH96917.a_gt250` NIC4bb RREF<br>`Antigorite_NMNH96917.b_165um` ASDNGb AREF<br>`Antigorite_NMNH96917.b_165um` BECKb AREF<br>`Antigorite_NMNH96917.b_165` NIC4bb RREF<br>`Antigorite_NMNH96917.c_120um` BECKb AREF<br>`Antigorite_NMNH96917.c_120` NIC4bb RREF<br>`Antigorite_NMNH96917.d_70um` BECKb AREF<br>`Antigorite_NMNH96917.d_70um` NIC4bb RREF<br>`Antigorite_NMNH96917.e_32um` BECKb AREF<br>`Antigorite_NMNH96917.e_32um` NIC4bb RREF<br>`Antigorite_NMNH96917.f_lt30um` BECKb AREF |
| serpentine_chrysotile | 2196 | Chrysotile HS323.1B          W1R1Ba AREF | `Chrysotile_HS323.1B` ASDNGa AREF<br>`Chrysotile_HS323.1B` BECKa AREF |
| serpentine_antigorite_withironfeat | 1265 | Antigorite NMNH96917.a >250  W1R1Bb AREF | `Antigorite_NMNH96917.a_gt250` ASDNGb AREF<br>`Antigorite_NMNH96917.a_gt250` BECKb AREF<br>`Antigorite_NMNH96917.a_gt250` NIC4bb RREF<br>`Antigorite_NMNH96917.b_165um` ASDNGb AREF<br>`Antigorite_NMNH96917.b_165um` BECKb AREF<br>`Antigorite_NMNH96917.b_165` NIC4bb RREF<br>`Antigorite_NMNH96917.c_120um` BECKb AREF<br>`Antigorite_NMNH96917.c_120` NIC4bb RREF<br>`Antigorite_NMNH96917.d_70um` BECKb AREF<br>`Antigorite_NMNH96917.d_70um` NIC4bb RREF<br>`Antigorite_NMNH96917.e_32um` BECKb AREF<br>`Antigorite_NMNH96917.e_32um` NIC4bb RREF<br>`Antigorite_NMNH96917.f_lt30um` BECKb AREF |
| serpentine_chrysotile_withsecondfeat | 2196 | Chrysotile HS323.1B          W1R1Ba AREF | `Chrysotile_HS323.1B` ASDNGa AREF<br>`Chrysotile_HS323.1B` BECKa AREF |
| serpentine_antigorite_withsecondfeat | 1265 | Antigorite NMNH96917.a >250  W1R1Bb AREF | `Antigorite_NMNH96917.a_gt250` ASDNGb AREF<br>`Antigorite_NMNH96917.a_gt250` BECKb AREF<br>`Antigorite_NMNH96917.a_gt250` NIC4bb RREF<br>`Antigorite_NMNH96917.b_165um` ASDNGb AREF<br>`Antigorite_NMNH96917.b_165um` BECKb AREF<br>`Antigorite_NMNH96917.b_165` NIC4bb RREF<br>`Antigorite_NMNH96917.c_120um` BECKb AREF<br>`Antigorite_NMNH96917.c_120` NIC4bb RREF<br>`Antigorite_NMNH96917.d_70um` BECKb AREF<br>`Antigorite_NMNH96917.d_70um` NIC4bb RREF<br>`Antigorite_NMNH96917.e_32um` BECKb AREF<br>`Antigorite_NMNH96917.e_32um` NIC4bb RREF<br>`Antigorite_NMNH96917.f_lt30um` BECKb AREF |
| topaz | 9412 | Topaz HS184.3B               W1R1Bc AREF | `Topaz_HS184.3B` ASDFRb AREF<br>`Topaz_HS184.3B` ASDNGb AREF<br>`Topaz_HS184.3B` BECKb AREF<br>`Topaz_HS184.3B` NIC4bc RREF |

统计：58 条规则在 splib07 找到同名样品记录，0 条未找到：

## 备注

- 样品名后缀变体（如 GDS113a、SMR-13.c）是同一样品的不同制备/粒径记录，一并列出。
- splib07 检索用 `name=` 子串匹配；`Clinochlore_Fe_SC-CCa-1.a` 的 sample_id 是 `Fe`，此处按全名子串 `SC-CCa-1` 检索。
- 19 条 `mix_*` 规则为 rf.json 内置线性合成谱，splib07 中无对应物理记录。
- **AMX 系列是计算混合而非实测物理混合**（2026-08-29 元数据核实）：`Kaol.5+MuscCU91-250A_AMX13`、`Alunite.5+MuscCU91-250A_AMX4` 等的 HTMLmetadata 明确标注 `MIXTURE_TYPE: Areal` + `SAMPLE_DESCRIPTION: Calculated areal (linear) mixture ...`，与 rf.json 的 `mix_*` 线性合成谱性质相同，不能作为物理混合 ground truth。注意 AMX13 的高岭石端元是 KGa-1（不是 CM9）、AMX4 的明矾石端元是 HS295.3B。
- 真正意义的实测混合样品是 CU93 系列天然混合岩石（如 `Chlorite+Muscovite_CU93-65A`，`MIXTURE_TYPE: Intimate`，Cuprite Harkless 组天然千枚岩）。