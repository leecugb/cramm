# 碳酸盐吸收波长仲裁逻辑专项审计

> 日期：2026-11-19  
> 当前代码：`cramm/classifier.py`  
> 当前窗口：`cramm/data/rf.json`  
> 整景：`EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc`  
> **证据边界：整景结果验证执行与内部一致性，不等同于碳酸盐亚型的独立地质精度。**

## 1. 两层仲裁结构

碳酸盐不是一次全族仲裁，而是分别调用两个互不相交的组：

| 仲裁层 | 规则 | 窗口 (µm) |
|---|---|---|
| abundant | calcite_abundant | [2.334, 2.350) |
| abundant | dolomite_abundant | [2.308, 2.328) |
| plain | calcite | [2.334, 2.350) |
| plain | dolomite | [2.308, 2.328) |

- 两层使用相同数值窗口，但分开调用，因此不会把层间重复窗口误判为歧义。
- 层内 dolomite 与 calcite 窗口互斥，只允许 dolomite ↔ calcite。
- `[2.328, 2.334)` 为 6 nm 死区；出所有窗口或中心无效时保持原赢家。
- `carbonate_Fe_bearing` 和 `calcite.5+dolomite.5` 无窗口，不参与重指派，但仍有 `cal_center` 产品。
- 翻转后按目标端点重估一次中心；重估非有限或越出目标窗时回退翻转前中心。

## 2. 参考中心与丰度层边界

| 规则 | 1 nm 中心 (µm) | 生产 EMIT 中心 (µm) | 清洁 M00 赢家 |
|---|---:|---:|---|
| calcite_abundant | 2.335323 | 2.338204 | calcite_abundant |
| calcite | 2.335323 | 2.338204 | calcite_abundant |
| dolomite_abundant | 2.315332 | 2.317961 | dolomite_abundant |
| dolomite | 2.315332 | 2.317961 | dolomite_abundant |

abundant/plain 两组参考光谱分别**逐位相同**：

- `calcite_abundant` 与 `calcite` 均使用 `Calcite_WS272_BECKa_AREF`；
- `dolomite_abundant` 与 `dolomite` 均使用 `Dolomite_HS102.3B_BECKb_AREF`。

因此，吸收中心不能区分同一矿物的 abundant 与 plain 规则。清洁 `calcite` 和 `dolomite` 被拟合为 abundant 后，按丰度层锁定设计不会通过波长仲裁改回 plain。

这不是仲裁绕开，而是明确的边界：

> **丰度层由规则和拟合约束决定，波长中心只在层内区分 calcite 与 dolomite。**

## 3. 执行与不变量核验

### 3.1 合成数据

当前合成数据中未观察到碳酸盐仲裁翻转。这与参考中心均落在自身窗口一致，也意味着该数据集不能用于证明碳酸盐仲裁的正向边际收益。

### 3.2 当前整景受控对照

以当前代码分别运行“完整碳酸盐仲裁”和“仅移除碳酸盐窗口”，得到：

| 项目 | 结果 |
|---|---:|
| plain-tier calcite → dolomite | **1,599** |
| plain-tier dolomite → calcite | 0 |
| abundant-tier 翻转 | 0 |
| 跨丰度层变化 | 0 |
| 非碳酸盐标签变化 | 0 |
| 目标规则未通过约束 | **0 / 1,599** |
| 重拟合后目标窗口不一致 | **0 / 1,599** |
| 需要回退到原中心 | 0 / 1,599 |

1,599 个目标 `dolomite` 均通过完整规则约束。逐像元独立重算目标端点中心，输出中心要么等于有效重拟合值，要么满足回退条件；本批没有回退案例。

当前结果与 README 中报告的 1,599 次一致。`docs/arbitration_stats.md` 的旧配置“碳酸盐 0 翻转”仍单独保留，两个配置不相加。

### 3.3 边界回归

`docs/_audit_arbitration.py` 新增并通过：

- 2.328 µm：dolomite 窗口右开边界，进入死区并保持原赢家；
- 2.334 µm：calcite 窗口左闭边界，可翻转至 calcite；
- 2.350 µm：calcite 窗口右开边界，出窗保持；
- 2.308 µm：dolomite 窗口左闭边界，可翻转至 dolomite。

连同既有 abundant/plain 层锁定、死区、无窗成员、目标 fit 和重拟合检查，结果为 **ALL PASS**。日志：`output/carbonate_arbitration_audit.log`。

## 4. 风险与适用边界

1. **不能评价丰度层正确性**：plain 与 abundant 使用相同参考曲线时，中心没有区分信息。
2. **不能用当前合成零翻转证明无效**：需要具有跨窗候选的独立样本。
3. **死区与出窗是保守策略**：它们限制极端或异常中心的重指派，但也意味着某些亚型不会被纠正。
4. **无窗 Fe 碳酸盐和混合规则不重指派**：这避免把混合中心强行解释成纯相亚型。
5. **连续 `cal_center` 与离散仲裁不同**：中心图层可以显示窗口外变化，离散标签仍受窗口和层级约束。

## 5. 结论

**碳酸盐按丰度层仲裁的预设逻辑能够运行，未发现串层、未验收目标或重拟合状态不一致。** 当前整景的 1,599 次 plain-tier calcite→dolomite 均满足目标验收和中心一致性。

主要解释边界不是执行错误，而是：丰度层本身由拟合决定，且 plain/abundant 共享参考曲线时，波长中心无法纠正丰度层误归。

## 6. 证据文件

- `output/carbonate_arbitration_scene_v1/summary.json`：整景翻转、跨层、目标验收和重拟合一致性汇总。
- `output/carbonate_arbitration_scene_v1/refit_verification.csv`：1,599 个像元逐条目标 fit 与中心复核。
- `output/carbonate_arbitration_scene_v1/scene_arrays.npz`：纯基线与仲裁后的标签和中心。
- `output/carbonate_arbitration_audit.log`：窗口边界与层锁定回归。
- `docs/audit_carbonate_arbitration_scene.py`：可复现整景审计脚本。
