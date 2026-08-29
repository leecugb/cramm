# 波长仲裁窗口速查表（归档）

> 归档日期：2026-08-26 ｜ 基线：绿泥石窗口改为无缝拼接（此前为 1711e20 起的容差重叠方案，2026-08-26 重置）
> 数据来源：`cramm/data/rf.json` 实测 ｜ 仲裁语义：`cramm/classifier.py::_reassign_by_absorption_center`

## 仲裁器判定逻辑（三族共用）

对每个胜方属于带窗规则的像元，用二次拟合吸收中心计数命中窗口数：

| 命中数 | 语义 | 动作 |
|---|---|---|
| 0（出所有窗 / 中心无效） | 无效 | 保守保持原匹配 |
| ≥2（重叠带） | 歧义 | 保持原匹配（argmax 结果） |
| 恰好 1 且非当前匹配、目标规则接受了该像元（fit 非 NaN 且 > 0） | 排他落入他窗 | 翻转归属 + 用目标规则 feat0 端点重拟合中心一次（单趟，不迭代） |

单趟向量化、串并行路径共用同一实现（逐比特一致），全部判定基于重判前状态。

## 白云母族（2.2 µm Al–O 带）：无缝拼接，每中心唯一归属

| 规则 | 窗口 [µm) |
|---|---|
| muscovite_medhighAl | [2.195, 2.200) |
| muscovite_medAl | [2.200, 2.206) |
| muscovite_lowAl | [2.206, 2.210) |
| muscovite_Fe-rich | [2.210, 2.220) |

四窗无重叠铺满 2.195–2.220，任何有效中心恰中一窗 → 必仲裁到唯一亚型。
无窗成员（不参与仲裁）：illite_imt1、illite_gds4、5 条 kaolinite/calcite×muscovite 混合规则、clinochlore_Fe.3+muscovite.7。

## 绿泥石族（2250 nm Fe–OH 带）：无缝拼接，每中心唯一归属

| 规则 | 窗口 [µm) | 宽度 |
|---|---|---|
| chlorite_lowFe | [2.245, 2.248) | 3.0 nm |
| clinochlore | [2.248, 2.252) | 4.0 nm |
| clinochlore_Fe | [2.252, 2.256) | 4.0 nm |
| thuringite | [2.256, 2.266) | 10.0 nm |

- 四窗无重叠铺满 2.245–2.266 µm，按 Fe 含量递增（SMR-13.a → GDS158 → CCa-1 → SMR-15.c）
- 任何有效中心恰中一窗 → 必仲裁到唯一亚型（与白云母族同构）；出窗 / 无效中心保守保持
- 2026-08-26 起生效：旧方案为容差重叠（[2.245,2.248) / [2.247,2.252) / [2.251,2.25549) / [2.255,2.266)，重叠带歧义保持），现改为确定性平铺
- 混合规则 chlorite+muscovite_mix_intimate、clinochlore_Fe.3+muscovite.7 无窗（带位反映混合而非成分）
- 已知规则内在不对称：chlorite_lowFe 独有 feat2(VNIR, w=0.3）对其实打分存在 ~0.19 系统性惩罚（官方 .mcf 继承，行为不变，实测归档见 `docs/lowfe_feat2_bias.md`)；低铁归属低估由本族仲裁窗口事后部分纠偏

### 典型判别示例：thuringite 赢家中心落入 clinochlore_Fe 窗

中心 2.2535 µm → 仅命中 clinochlore_Fe 一窗（自身窗未中）→ 排他落入 → **翻转 clinochlore_Fe + 重拟合**。对照：

- 2.249（仅中 clinochlore）→ 翻转 clinochlore + 重拟合
- 2.2535（仅中 clinochlore_Fe）→ 翻转 clinochlore_Fe + 重拟合
- 2.256（仅中自身 thuringite）→ 保持

单测钉死：tests/test_core.py 绿泥石仲裁用例组（含 2.2475 翻 lowFe、2.2515 翻 clinochlore 例）。

## 碳酸盐族（2330 nm C–O 带）：重复窗，声明式零翻转

| 规则 | 窗口 [µm) | 类型 |
|---|---|---|
| calcite_abundant | [2.334, 2.350) | 重复窗 |
| calcite | [2.334, 2.350) | 与 abundant 完全相同 |
| dolomite_abundant | [2.308, 2.328) | 重复窗 |
| dolomite | [2.308, 2.328) | 与 abundant 完全相同 |
| carbonate_Fe_bearing | 无窗 | 不参与仲裁 |
| calcite.5+dolomite.5 | 无窗 | 不参与仲裁 |

容差机制的极端形式：abundant 与平凡版窗口完全相同，任何落窗中心必中两窗 → 恒歧义 → 永不翻转（专门单测钉死）。
产品价值在连续 `cal_center` 图层本身：被规则库静默归入 dolomite 的文石（2315 nm）、菱镁矿（2311 nm）在中心图层上可辨识。
七锚点解读序列：magnesite 2311 < aragonite 2315 < Fe-dolomite 2319 < dolomite 2321 < siderite ~2327 < calcite 2339 < rhodochrosite ~2369 nm。

## 族间隔离：结构保证（family lock）

**2026-08-24 起**，`_reassign_by_absorption_center` 增加 `family` 参数，仲裁组**直接锁定**为本族成员列表 ∩ 带窗规则：

- 白云母调用：group = MUSCOVITE_MINERALS ∩ 带窗 = medhighAl / medAl / lowAl / Fe-rich
- 绿泥石调用：group = CHLORITE_MINERALS ∩ 带窗 = lowFe / clinochlore / clinochlore_Fe / thuringite
- 碳酸盐调用：group = CARBONATE_MINERALS ∩ 带窗 = calcite/dolomite abundant+plain 四条

跨族翻转由此**在结构上不可能**（不再依赖「中心数组仅本族非零 + 窗口间距」的涌现性质——两者仍作为纵深防御保留）。单测 `test_arbitration_family_lock` 钉死：绿泥石赢家中心落入白云母窗口（反之亦然）必须保持原匹配。

自定义规则库改为**按族加入**：新规则须先加入对应族列表、再携带 `absorption_center_range` 才参与仲裁；族外规则带窗将被忽略（族锁定优先）。

纵深防御（仍成立，整景实测）：
- 各中心数组仅本族赢家非零（`mus_c > 0` 成员门）
- 白云母上限 2.220 ↔ 绿泥石下限 2.245：间距 25 nm；绿泥石上限 2.266 ↔ 碳酸盐下限 2.308：间距 42 nm
- 整景交叉翻转证据六项全零（tests/check_arbitration_independence.py，现作为防御性证据保留）

## 相关档案

- `docs/algorithm_flow.md` — 流水线第 2–6 步
- `docs/paper_preparation.md` — 事实核对表（12 条仲裁窗口规则）
- `docs/arbitration_stats.{md,json}` — 生产翻转统计（开窗 vs 纯 argmax 两遍实验）
- `docs/MCF_vs_rfjson_verification.md` — 与官方 .mcf 的逐字段核验
