# splib07 迁移 · 阶段2 导出审计

> 日期：2026-08-31（AMX17 重接 NIC4b 后重烘）｜ 脚本：`docs/_splib07_stage2_export.py` ｜ 产物：`cramm/data/rf07_spectra.npz`
> 审计口径：原生有效样本 vs 1 nm 主网格烘焙谱，分别经引擎 `_resample_` 重采样到真实 EMIT 网格后比较。
> NIC4 ~0.93 nm→1 nm 轻微降采样的影响即体现在 max|Δ| 列；filled = 烘焙按构造填掉的 FWHM 空洞（遗产改善）；new holes 必须为 0。
> 记录构成：53 条选谱参考 + 5 条 AMX 计算混合记录（90008+ 合成 rec id，权重 1.0 别名接入）= 58 条。

| 记录 | 传感器 | r | max\|Δ\| | 填洞数 | 新增空洞 |
|---|---|---|---|---|---|
| `Engelmann-Spruce_ES-Needls-1_ASDFRa_AREF` | ASDFR | 1.000000 | 8.23e-08 | 0 | 0 |
| `Rangeland_C04-170_S30%_G24%_ASDFRa_AREF` | ASDFR | 0.999985 | 4.94e-03 | 29 | 0 |
| `Melting_snow_mSnw01a_ASDFRa_AREF` | ASDFR | 1.000000 | 5.54e-08 | 0 | 0 |
| `Melting_snow_mSnw09_(slush)_ASDFRa_AREF` | ASDFR | 1.000000 | 3.79e-05 | 0 | 0 |
| `Seawater_Coast_Chl_SW1_BECKa_AREF` | BECK | 0.999991 | 1.99e-04 | 19 | 0 |
| `Water+Montmor_SWy-2+5.01g-l_ASDFRa_AREF` | ASDFR | 1.000000 | 2.48e-08 | 0 | 0 |
| `Water+Montmor_SWy-2+0.50g-l_ASDFRa_AREF` | ASDFR | 1.000000 | 3.26e-09 | 0 | 0 |
| `Grass_Golden_Dry_GDS480_ASDFRa_AREF` | ASDFR | 1.000000 | 3.14e-08 | 0 | 0 |
| `Lodgepole-Pine_LP-Needles-2_ASDFRa_AREF` | ASDFR | 1.000000 | 6.77e-08 | 0 | 0 |
| `Muscovite_CU93-1_low-Al_Phyl_NIC4b_RREF` | NIC4 | 0.999998 | 6.04e-04 | 0 | 0 |
| `Muscovite-medlowAl_CU91-250A_NIC4b_RREF` | NIC4 | 0.999995 | 9.12e-04 | 0 | 0 |
| `Muscovite_GDS113_Ruby_NIC4aaa_RREF` | NIC4 | 0.999992 | 9.79e-04 | 0 | 0 |
| `Muscovite_GDS116_Tanzania_NIC4aaa_RREF` | NIC4 | 0.999997 | 6.64e-04 | 0 | 0 |
| `Illite_IMt-1.b_lt2um_BECKa_AREF` | BECK | 0.999918 | 5.95e-03 | 19 | 0 |
| `Illite_GDS4_Marblehead_ASDNGb_AREF` | ASDNG | 1.000000 | 4.00e-08 | 0 | 0 |
| `Kaolinite_CM9_NIC4bbb_RREF` | NIC4 | 0.999989 | 4.27e-03 | 0 | 0 |
| `Kaolinite_KGa-2_(pxl)_NIC4bbb_RREF` | NIC4 | 0.999992 | 3.54e-03 | 0 | 0 |
| `Halloysite_NMNH106237_NIC4aaa_RREF` | NIC4 | 0.999996 | 3.06e-03 | 0 | 0 |
| `Dickite_NMNH106242_NIC4bb_RREF` | NIC4 | 0.999988 | 3.07e-03 | 0 | 0 |
| `Buddingtonite_GDS85_D-206_BECKb_AREF` | BECK | 0.999905 | 7.17e-03 | 19 | 0 |
| `Buddingtnt+Na-Mont_CU93-260B_NIC4b_RREF` | NIC4 | 0.999996 | 9.96e-04 | 0 | 0 |
| `Alunite_GDS96_K_Syn_(250C)_NIC4a_RREF` | NIC4 | 0.999987 | 2.95e-03 | 0 | 0 |
| `Alunite_RES-3_Na_Syn_(450C)_NIC4a_RREF` | NIC4 | 0.999955 | 8.54e-03 | 0 | 0 |
| `Pyrophyllite_PYS1A_lt850um_NIC4aaa_RREF` | NIC4 | 0.999968 | 7.14e-03 | 0 | 0 |
| `Jarosite_GDS24_Na_NIC4bbb_RREF` | NIC4 | 0.999996 | 9.66e-04 | 0 | 0 |
| `Jarosite_GDS99_K_200C_Syn_NIC4aa_RREF` | NIC4 | 0.999996 | 2.14e-03 | 0 | 0 |
| `Montmorillonite_SWy-1_NIC4bcc_RREF` | NIC4 | 0.999995 | 7.64e-04 | 0 | 0 |
| `Montmorillonite_SAz-1_NIC4bb_RREF` | NIC4 | 0.999995 | 1.20e-03 | 0 | 0 |
| `Nontronite_NG-1.b_lt2um_fr_NIC4bb_RREF` | NIC4 | 0.999993 | 5.15e-04 | 0 | 0 |
| `Hectorite_SHCa-1.Ac-B_NIC4bb_RREF` | NIC4 | 0.999989 | 9.88e-04 | 0 | 0 |
| `Gypsum_HS333.3B_(Selenite)_NIC4aaa_RREF` | NIC4 | 0.999996 | 9.41e-04 | 0 | 0 |
| `Chlorite_SMR-13.a_104-150um_BECKa_AREF` | BECK | 0.999797 | 2.08e-02 | 19 | 0 |
| `Clinochlore_GDS158_Flagstaff_NIC4bb_RREF` | NIC4 | 0.999995 | 7.36e-04 | 0 | 0 |
| `Clinochlore_Fe_SC-CCa-1.a_NIC4aa_RREF` | NIC4 | 0.999999 | 8.72e-04 | 0 | 0 |
| `Thuringite_SMR-15.c_32um_NIC4aa_RREF` | NIC4 | 0.999999 | 1.04e-03 | 0 | 0 |
| `Epidote_GDS26.a_75-200um_NIC4bbb_RREF` | NIC4 | 0.999987 | 3.48e-03 | 0 | 0 |
| `Alun366+.50PyroPYS1A_GDS222_BECKb_AREF` | BECK | 0.999459 | 4.28e-02 | 19 | 0 |
| `Kaol+Muscov_intimate_CU93-5C_BECKa_AREF` | BECK | 0.999832 | 1.29e-02 | 19 | 0 |
| `Kaolin_Smect_H89-FR-2_.5Kao_NIC4bb_RREF` | NIC4 | 0.999994 | 9.69e-04 | 0 | 0 |
| `Muscov+Jaros_CU93-314_coatng_BECKb_AREF` | BECK | 0.999850 | 8.51e-03 | 19 | 0 |
| `Chlorite+Muscovite_CU93-65A_BECKa_AREF` | BECK | 0.999773 | 9.96e-03 | 19 | 0 |
| `Calcite_WS272_BECKa_AREF` | BECK | 0.999240 | 1.61e-02 | 19 | 0 |
| `Dolomite_HS102.3B_BECKb_AREF` | BECK | 0.999174 | 2.05e-02 | 19 | 0 |
| `Siderite_HS271.3B_BECKa_AREF` | BECK | 0.999980 | 4.99e-03 | 21 | 0 |
| `Calcite.80+Mont_Swy-1_GDS212_BECKa_AREF` | BECK | 0.999324 | 1.22e-02 | 19 | 0 |
| `Calcite.80wt+Kaol_CM9_GDS213_BECKa_AREF` | BECK | 0.999497 | 3.21e-02 | 19 | 0 |
| `Chalcedony_CU91-6A_BECKa_AREF` | BECK | 0.999857 | 1.04e-02 | 19 | 0 |
| `Opal_TM8896_(Hyalite)_NIC4aa_RREF` | NIC4 | 0.999994 | 6.97e-04 | 0 | 0 |
| `Tremolite_HS18.3B_NIC4ccc_RREF` | NIC4 | 0.999944 | 4.36e-03 | 0 | 0 |
| `Talc_GDS23_74-250um_NIC4aaa_RREF` | NIC4 | 0.999968 | 4.11e-03 | 0 | 0 |
| `Antigorite_NMNH96917.a_gt250_BECKb_AREF` | BECK | 0.999756 | 1.68e-02 | 19 | 0 |
| `Chrysotile_HS323.1B_BECKa_AREF` | BECK | 0.999032 | 1.80e-02 | 19 | 0 |
| `Topaz_HS184.3B_BECKb_AREF` | BECK | 0.996156 | 1.03e-01 | 19 | 0 |
| `Calcite.5+Dolomite.5_AMX8_ASDNGb_AREF` | ASDNG | 1.000000 | 4.51e-08 | 0 | 0 |
| `Dolomite.5+Ca-Mont.5_AMX10_ASDNGb_AREF` | ASDNG | 1.000000 | 6.71e-08 | 0 | 0 |
| `Dolomite.5+Na-Mont.5_AMX21_ASDNGb_AREF` | ASDNG | 1.000000 | 6.20e-08 | 0 | 0 |
| `Kaol_Wxl+0.5Musc_Ruby_AMX12_NIC4a_AREF` | NIC4 | 0.999994 | 2.26e-03 | 0 | 0 |
| `Pyrophyl.25+wxlKaol.75_AMX17_NIC4b_AREF` | NIC4 | 0.999992 | 2.65e-03 | 0 | 0 |

## AMX 计算混合记录（5 条别名）

5 条 .mcf 混合配方在 splib07 有同样品同配比的 AMX 预计算面积混合记录，烘焙后以权重 1.0 别名接入（见阶段 1 选别与 `docs/MCF_vs_rf07_diff.md`）。AMX 由 USGS 用其自择端元记录预先计算，与本表端元的数值加权和存在有界差异：

| mix_id | 规则 | AMX 记录 | r(v07 合成) | max\|Δ\| | r(06b 合成) |
|---|---|---|---|---|---|
| mix_7821 | calcite.5+dolomite.5 | `Calcite.5+Dolomite.5_AMX8_ASDNGb_AREF` | 0.9944 | 0.0636 | 0.9946 |
| mix_7715 | dolomite.5+montmorilloniteCa.5 | `Dolomite.5+Ca-Mont.5_AMX10_ASDNGb_AREF` | 0.9655 | 0.0667 | 0.9653 |
| mix_7711 | dolomite.5+montmorilloniteNa.5 | `Dolomite.5+Na-Mont.5_AMX21_ASDNGb_AREF` | 0.9618 | 0.0695 | 0.9616 |
| mix_7745 | kaolinite.5+muscoviteMedhighAl.5 | `Kaol_Wxl+0.5Musc_Ruby_AMX12_NIC4a_AREF` | 1.0 | 0.0189 | 1.0 |
| mix_7737 | pyrophyllite.25+kaolinite.75 | `Pyrophyl.25+wxlKaol.75_AMX17_NIC4b_AREF` | 1.0 | 0.034 | 1.0 |

## 完整性核验

- 整数 nm 对齐记录（ASD 1 nm 表；BECK 10 nm 采样点亦落在整数 nm）烘焙为恒等拷贝，回读 max|diff| = 0.000e+00（要求 ≤1e-12）
- 非对齐记录（NIC4 ~0.93 nm）采样点回读差为构造性插值误差，最大 1.603e-02（`Alun366+.50PyroPYS1A_GDS222_BECKb_AREF`）——非完整性问题，其引擎侧影响见上表 max|Δ| 列

## 对 D2 增补“上采样无损”论断的修正

无损证明仅对线性插值型重采样成立。引擎 `_resample_` 是按 FWHM 窗内样本做高斯加权平均（权重按窗内样本归一），粗采样窗内仅 1–2 个样本时其加权均值 ≠ 稠密插值样本的加权均值（≈真卷积）。因此 BECK 10 nm→1 nm 烘焙**改变**高斯核重采样结果：EMIT 网格上 max|Δ| 普遍 ≤2e-2，最大 1.03e-1（Topaz_HS184.3B，2.0–2.16 µm 陡沿，r=0.9962）。烘焙谱更接近真实仪器卷积，但与现行 06b 粗采样口径存在有界行为差——列入阶段 4 双跑仲裁。

NIC4 降采样最大偏差：8.54e-03（`Alunite_RES-3_Na_Syn_(450C)_NIC4a_RREF`，r=0.999955）