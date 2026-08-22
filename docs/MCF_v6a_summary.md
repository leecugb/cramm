# MICA 指挥文件(.mcf)梳理 —— mica_cmds_group2_hymap2_2014_v6a_FOR_RELEASE

> 原件:`D:\mcf\mica_cmds_group2_hymap2_2014_v6a_FOR_RELEASE.mcf`(1973 行,86 KB,USGS 2014 v6a 发布版,group2 = 2-µm 分析,HyMap 126 通道)
>
> **核心结论:CRAMM 的 `rf.json`(77 规则)与该 .mcf 的 `NUM_REFERENCE_ENTRIES: 77` 逐条一一对应(OUTPUT_NAME 集合完全一致),rf.json 是该指挥文件的忠实移植 + CRAMM 扩展。**

## 1. 文件结构(四段式)

### ① 全局参数(头部)
| 指令 | 值 | 含义 |
|---|---|---|
| `FILE_DN_COLORS` | *.txt | 类别颜色表 |
| `SCALEFACTOR_OBSERVED` | 20000 | HyMap 反射率以 ×20000 整数存储,读入需缩放 |
| `SCALEFACTOR_REFERENCE` | 1.0 | 参考库已是浮点反射率 |
| `NODATA_VALUE_IMAGE` | -1 | 影像 NoData |
| `CHECK_SIGNS_OF_DEPTHS` | 1 | 检查深度符号(吸收必须为负向) |
| `TETRACORDER_OPTIONS` | 0 | Tetracorder 兼容开关 |
| `WAVELENGTHS` | splib06b_cv_hymap2_2014_126ch, record 5 | 波长轴 |
| `DELETED_CHANNELS` | 21 个通道号 | 坏波段剔除(↔ CRAMM 的 `bp`/`chanels`) |

### ② 别名(26 个 `ALIAS`)
路径别名(`[splib06b_convolved]`)+ **阈值常量别名**,构成全文件的调参面板:
- 拟合阈值:`[MINFIT]` 0.64、`[MINFIT_WEAKFEAT]` 0.65、`[MINFIT_NOTFEAT]` 0.65、蛇纹石专用 0.64/0.50
- 深度阈值:`[MINDEPTH]` 0.02、单特征 0.01、白云母 2340nm 0.015、明矾石 0.03/0.07…
- 连续统/FD:`[MIN_REFL_MID]` 0.04、植被 0.03、`[MINFD]` 0.025、方解石 0.03、2.3µm 0.045

### ③ 全局 NOT 特征库(14 个)
`NOT_FEATURE_ID` + 参考光谱记录 + `CONTINUUM_ENDPTS`——云杉针叶、白云母 2340nm、明矾石 1440nm、石膏、绿泥+云母、绿帘石、干草/松针 2.1µm 与 2.3µm、方解石 2.15µm、白云石 2.14µm、斜绿泥石 2.26µm。各材料按 ID 引用。

### ④ 参考条目 ×77(主体)
每条:
```
REFERENCE_SPECPR_RECORD: [库别名] 记录号
OUTPUT_NAME: 输出类别名
NUM_FEATURES: <诊断特征数> <NOT特征数>
  FEATURE_TYPE: Diagnostic
  FEATURE_WEIGHT: 权重(各特征权重和=1)
  CONTINUUM_ENDPTS: λ1a λ1b λ2a λ2b      # 左右端点各为小区间,取区间平均抗噪
  CONTINUUM_CONSTRAINTS: 8 槽             # -99.99 = 未启用
  FIT_CONSTRAINTS / DEPTH_CONSTRAINTS min max
  FEATURE_TYPE: Not
  NOT_FEATURE_ID / NOT_FEATURE_FIT_CONSTRAINTS / NOT_FEATURE_ABSOLUTE_DEPTH_CONSTRAINTS
WEIGHTED_FIT_DEPTH_CONSTRAINTS: min_fit min_depth max_depth min_F×D   # 材料级
END_REFERENCE_ENTRY
```
统计:77 条目 = **144 个诊断特征 + 83 处 NOT 特征引用**;70 个唯一参考光谱记录(7 条记录被复用,如不同阈值的方解石)。`NUM_FEATURES` 分布:(2,0)×23、(3,0)×11、(1,2)×9、(2,2)×9…

## 2. 与 CRAMM rf.json 的对应(以 muscovite_lowAl 为例)

| .mcf(HyMap 卷积库) | rf.json(原始 splib06b) |
|---|---|
| record 3164(splib06b_cv_hymap2 副本) | `reflectance_record: 6258` + `wavelength_record: 40`(Nicolet 1.3–5.2µm 网格) |
| `CONTINUUM_ENDPTS 2.1300 2.1650 2.2658 2.2900` | `continuum_endpoints: [2.13, 2.165, 2.2658, 2.29]` 完全一致 |
| `[MIN_REFL_MID]` → 0.04 | `mean_min: 0.04`(别名已解析为数值) |
| `[MINFIT_WEAKFEAT]` → 0.65 | `fit_constraint: 0.65` |
| `[MINDEPTH_MUSCOVITE_2340NM]` → 0.015 | `depth_constraints: [0.015, null]` |
| `WEIGHTED_FIT_DEPTH_CONSTRAINTS [MINFIT] [MINDEPTH] -99.99 [MINFD]` | `min_weighted_fit 0.64 / min_weighted_depth 0.02 / max null / min_fit_depth_product 0.025` |
| —(.mcf 无此概念) | **`absorption_center_range: [2.206, 2.22]`(CRAMM 波长仲裁)** |
| —(.mcf 无此概念) | **`max_depth_ratio_feat1_over_feat0: 0.6`(CRAMM 深度比约束)** |

`-99.99` → `null` 的语义映射贯穿全库。

## 3. 关键架构差异(论文卖点)

**.mcf 模式**:参考库必须**预先卷积到具体传感器**(splib06b_cv_hymap2_2014_126ch 是 HyMap 126 通道专用副本)。换传感器 = 重新生成整套卷积库 + 适配指挥文件,且依赖 ENVI/IDL。

**CRAMM 模式**:捆绑原始 splib06b(4 种仪器波长网格,53 条 `wavelength_map` 寻址),运行时按 `(w, bp)` 高斯核重采样(带缓存)→ **传感器无关**;EMIT L2A 只是内置读取器之一。

## 4. 白云母亚型的原始设计

.mcf 中 lowAl/medAl/medhighAl/Fe-rich 是 **4 条独立规则**,特征 1(2.2µm 主吸收,权重 0.75)的连续统端点随 Al 含量微移(2.1180–2.1300 起点的差异),靠不同参考光谱"投票"区分化学成分;特征 2(2.34µm 附近,权重 0.25)是 Al-OH 组合频弱吸收,带 `MINFIT_WEAKFEAT` 拟合约束 + 0.015 深度约束。CRAMM 保留该四规则骨架,新增 2.2µm 吸收中心二次拟合(`mus_center`)做连续定量填图与亚型仲裁。

## 5. 引用

.mcf 本身无独立文献条目,随 DS787 数据发布;引用 DS787(Kokaly et al. 2013)+ Kokaly 2011 (OFR 2011-1155, PRISM 手册含 .mcf 语法权威定义)。
