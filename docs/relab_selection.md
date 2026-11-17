# RELAB 跨库基准 · 阶段1 遴选

> 日期:2026-09-08 | 脚本:`docs/_relab_stage1_selection.py`(可重复执行) | 数据:本地 RELAB 镜像 | 排重:`crosslib_dedup_hits.csv`(R8)

## 遴选规则

- **R1** material_type == 'Mineral'
- **R2** geometry == 'Bidirectional'
- **R3** range covers [500, 2450] nm
- **R4** mineral_type 不含 ';';group ';' 复合组仅固溶体系列(匹配成员≥2 且同族)放行
- **R5** 名称不含混合/衍生标记 %|\+|mixture|cation.?exchanged|heated|treated|acidified|laid on|\b\d{3}C\b|w/C\b
- **R6** mineral_subtype 不含 '/'
- **R7** 族映射优先级 subtype>name>group;group 为超群 taxonomy(alunite⊃jarosite,calcite⊃siderite/dolomite,mica⊃illite/muscovite);mixed-layer/蛭石/硅铁石否定
- **R8** 排除 crosslib_dedup_hits.csv strength=strong(CMS 同材料)
- **R9** R8 命中标本根号的分样株(-A/-B…)连带排除(改名分样防漏)

## 遴选漏斗

| 阶段 | 记录数 |
|---|---|
| 全库 | 23606 |
| ✗ R1 非单矿物 | 15646 |
| ✗ R7 族外/冲突 | 3484 |
| ✗ R2 非双向几何 | 2361 |
| ✗ R3 波段覆盖不足 | 897 |
| ✗ R5 混合/衍生名称 | 310 |
| ✗ R4 多矿物归属 | 288 |
| ✗ R8 排重(CMS 同材料) | 62 |
| ✗ R9 同标本株连带 | 5 |
| ✗ R6 亚型双重归属 | 2 |
| **入选** | **551** |

## 各族入选规模

| 族 | 光谱 | 标本 |
|---|---|---|
| smectite | 143 | 141 |
| calcite | 105 | 86 |
| serpentine | 57 | 53 |
| gypsum | 41 | 34 |
| jarosite | 39 | 39 |
| dolomite | 38 | 37 |
| chlorite | 30 | 26 |
| siderite | 25 | 25 |
| kaolinite | 21 | 20 |
| tremolite | 13 | 12 |
| alunite | 12 | 11 |
| talc | 10 | 9 |
| illite | 7 | 5 |
| pyrophyllite | 3 | 3 |
| epidote | 2 | 2 |
| muscovite | 2 | 2 |
| opal | 2 | 2 |
| buddingtonite | 1 | 1 |
| **合计** | **551** | **508** |

## RELAB 缺位族(由 ECOSTRESS 腿补足)

`chalcedony`, `topaz`

## 备注

- 族真值 = RELAB 档案矿物归属(subtype 优先,名称兜底);亚型不作真值。
- 同一标本的多条光谱(粒径/制样变体)全部保留;统计命中率时可按 specimen_id 做留一标本交叉验证,防粒径相关过拟合。
- 蒙脱石族入选样本已剔除 CMS 标样(SWy/SAz 等同材料),剩余为天然蒙脱石/皂石/绿脱石——这才是独立证据。
- **保留但需在论文中声明的边界样**:CMS 标样中**与 bundled 参考不同材料**者(STx-1、KGa-1/KGa-1b、IMt-2、SAz-2)构成合法独立测试;合成纯相(PIG004 方解石 / PIG005 石膏 / PIG006 滑石、Baker 系合成绿脱石)保留——bundled 参考本身亦含合成样(GDS96/RES-3/GDS99),判据一致。
