# .mcf 与 rf.json 一致性核验报告

> 核验脚本:[verify_mcf_rfjson.py](verify_mcf_rfjson.py)(可重复执行)
> 对象:`D:\mcf\mica_cmds_group2_hymap2_2014_v6a_FOR_RELEASE.mcf`(USGS 2014 v6a, 2-µm, HyMap 126ch)vs `cramm/data/rf.json`

## 结论

**全部启用配置零不一致。** rf.json 是 .mcf 的忠实移植,差异仅有三类设计性偏离(见 §3)。

| 核验维度 | 规模 | 结果 |
|---|---|---|
| A 条目集合(OUTPUT_NAME) | 77 = 77,双向差集为空 | ✅ |
| B 诊断特征:权重 / 连续统端点 / 拟合与深度约束 | 142 个特征 | ✅ 全一致 |
| B 连续统约束 8 槽(left/mean/right min-max, ratio min-max) | 1,136 槽 | ✅ 全一致(-99.99↔null,别名已解析) |
| C NOT 特征引用(端点按 14 条全局库展开 + fit/绝对/相对深度约束) | 80 处 | ✅ 全一致(5 处相对深度约束 → rf `not_relative_features` 独立列表存储) |
| D 材料级 WEIGHTED_FIT_DEPTH_CONSTRAINTS | 77 × 4 值 | ✅ 全一致 |
| E 参考光谱身份 | 64 条纯谱规则 | ✅ 同一样品(6 条经人工复核,见 §2) |
| G 类别颜色表(mica_colors_*.txt ↔ color_table.json) | 77 = 77 | ✅ RGB 逐值一致 |
| 特征权重和 = 1 | 77 条 | ✅ |

**未移植的 .mcf 头部参数**(传感器绑定,按设计由 CRAMM 运行时契约替代):
`SCALEFACTOR_OBSERVED`(HyMap ×20000 整数缩放)、`DELETED_CHANNELS`(21 个坏波段)、`WAVELENGTHS`(HyMap 波长文件)→ 统一由 `(w, bp, chanels)` 波段配置契约在读取器层处理;`FILE_DN_COLORS`/`NODATA_VALUE_IMAGE`/`CHECK_SIGNS_OF_DEPTHS`/`TETRACORDER_OPTIONS` 为 IDL 运行参数,Python 实现无对应需求。

## 1. .mcf 中被注释禁用、rf.json 正确未收录的配置

- 2 个诊断特征(`;FEATURE_TYPE: Diagnostic`):`jarosite+muscovite_mix_intimate`、`clinochlore_Fe.3+muscovite.7` 各 1 个
- 3 个 NOT 特征块(`;NOT_FEATURE_ID: 15`,超出全局库 14 条范围):`calcite.8+montmorilloniteNa.2_mix_intimate`、`calcite.25+montmorilloniteCa.75`、`calcite.25+montmorilloniteNa.75`

即 USGS 在 v6a 中关闭了这些滤波器,rf.json 与"启用态"一致。

## 2. 自动匹配器标记、人工复核确认为同一样品的 6 条

| 规则 | .mcf 标题 | rf.json 标题 | 复核结论 |
|---|---|---|---|
| chlorite_lowFe | Chlorite SMR-13.a 104-150 **W5R4Naa_** | Chlorite SMR-13.a 104-150 **W1R1Ba** | 同一样品,**测量记录不同**(Nicolet vs Beckman 光束条件),重采样后差异极小 |
| illite_imt1 | IMt-1.bIllite(CMS)<2umGrnPowder1838 | Illite IMt-1.b <2um W1R1Ba | 同一 CMS 标样 |
| pyrophyllite.5+alunite.5 | GDS222 aluniteWNS366+pyrophPYS1A | Alun366+.50PyroPYS1A GDS222 | 同一 GDS222 实物混合样 |
| serpentine_antigorite ×3 | NMNH96917**A** Antigorite>250um | Antigorite NMNH96917**.a** >250 | 同一样品(记录后缀写法差异) |

## 3. 设计性差异(有意为之,非错误)

### 3.1 混合物:实物混合光谱 → 端元线性合成(13 条)
.mcf 指向 splib06b 中的实物混合物光谱(AMX/GDS 系列);CRAMM 改为端元线性合成(`mix_*` + `mixtures` 权重表),换取传感器无关的运行时重采样。其中:
- `calcite.8+montmorilloniteNa.2`(GDS212)与 `kaolinite.2+calcite.8`(GDS213):CRAMM 直接引用同一实物谱 ×1.0,**完全等价**;
- ⚠️ `kaolinite.5+muscoviteMedAl.5` 与 `alunite.5+kaolinite.5`:mcf 实物谱用 **KGa-1**(结晶好)高岭石,CRAMM 合成用 **KGa-2 (pxl)**(结晶差)——端元替换,2.17/2.21µm 双峰锐度不同,是有意的参考谱选择差异,论文中应注明。

### 3.2 CRAMM 纯新增(.mcf 中不存在)
- **吸收中心仲裁窗口 `absorption_center_range`**:4 条白云母规则(medhighAl [2.195,2.20] / medAl [2.20,2.206] / lowAl [2.206,2.210] / Fe-rich [2.210,2.220] µm,互不重叠、无缝拼接)
- **深度比约束 `max_depth_ratio_feat1_over_feat0`**:9 条规则(白云母×4 = 0.6,伊利石×2 = 0.6,高岭石-白云母混合×3 = 0.4)
- **参考样本结构式标注 `structural_formula` / `structural_formula_tier`**:4 条规则(muscovite_medhighAl=GDS113、muscovite_Fe-rich=GDS116、illite_gds4=GDS4 为 A 级湿法双价态;illite_imt1=IMt-1 为 B 级全铁约定),来源为 14 样本白云母族成分-带位标定数据集(O=11 无水基);纯元数据,不参与分类计算

### 3.3 参考光谱寻址方式
.mcf 指向 HyMap 预卷积库记录(换传感器需重建整套库);rf.json 指向原始 splib06b 记录 + `wavelength_map` 波长轴记录(53 条映射,4 种仪器网格),运行时高斯核重采样 → 传感器无关。

## 4. 复现

```
cd D:\CRAMM
python docs/verify_mcf_rfjson.py
```
输出:`不一致项` 中除 §2 的 6 条样品标题假阴性外应为空。
