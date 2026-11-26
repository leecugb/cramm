# CRAMM 每条参考光谱与诊断特征审计

> 日期：2026-11-20  
> 脚本：`docs/audit_reference_diagnostic_features.py`  
> 范围：77 条规则、142 个诊断特征，原始 1 nm 与生产 EMIT 波段  
> 当前配置：纯规则深度比 0.6、高岭石—白云母混合规则 0.55、lowFe `[2.244,2.248)`  
> **边界：这是参考谱自洽性与诊断特征审计，不是独立光谱质量或地质精度证明。**

## 1. 总体结果

| 检查项 | 结果 |
|---|---:|
| 参考规则 / 诊断特征 | 77 / 142 |
| 1 nm 与 EMIT 自约束通过 | **142/142** |
| EMIT 中心有效 | 140/142 |
| 边缘最小值导致中心不可估 | 2 |
| EMIT 中心偏移 >4 nm | 7 |
| 仲裁窗口规则中的中心异常 | **0** |
| weight=0 特征 | 26 |
| 原生覆盖从 >1 µm 才开始的规则 | 41 |
| 完全重复参考组 | 6 |
| 无仲裁自身 Top-1 / Top-5 | 70/77、75/77 |
| 清洁参考被仲裁改变 | 0 |

EMIT 参考拟合深度：

- 最小 0.01357，中位数 0.17399；
- 重采样深度比（EMIT/1 nm）最小 0.6374，中位数 0.9769；
- 中心绝对偏移中位数 0.982 nm，最大 75.954 nm（一个非仲裁、宽窗口异常）。

没有发现自约束拒绝、深度 <0.01 或深度衰减超过 50% 的特征。

## 2. 重复参考与自识别例外

六组参考光谱逐位重复：

| 组 | 规则 |
|---|---|
| D01 | dry_veg_grass / dry_veg_grass_2_3um |
| D02 | dry_veg_nongrass / dry_veg_nongrass_2_3um |
| D03 | calcite / calcite_abundant |
| D04 | dolomite / dolomite_abundant |
| D05 | serpentine_antigorite_or_calcite+dolomite / withironfeat / withsecondfeat |
| D06 | serpentine_chrysotile / serpentine_chrysotile_withsecondfeat |

七个未获自身 Top-1 的规则全部位于这些重复组：

- dry_veg_grass、dry_veg_nongrass；
- calcite、dolomite；
- serpentine_antigorite_or_calcite+dolomite；
- serpentine_antigorite_withironfeat；
- serpentine_chrysotile。

这说明自识别例外可由参考重复和规则约束差异解释，没有发现额外的未知 Top-1 自识别错误。两个 Top-5 例外为纯 calcite/dolomite，与其规则约束和 abundant 接管有关，不能简单称为实现错误。

## 3. 中心异常的实际意义

### 3.1 两个不可估中心

| 规则/特征 | 特征窗口 | EMIT 状态 |
|---|---|---|
| water feat1 | 0.42–0.64 µm | 边缘最小值，中心 NaN |
| water_sediment_high feat2 | 0.73–0.885 µm | 边缘最小值，中心 NaN |

这两个不是“已计算出但越窗”的中心，而是最小值落在窗口边缘，三点抛物线无法构造。它们不参与当前吸收中心仲裁。

### 3.2 七个 >4 nm 偏移

主要异常包括：

- `buddingtonite+montmorillonite_mix_intimate` feat0：+75.954 nm；
- `alunite_K_250C` feat1：−15.898 nm；
- `serpentine_antigorite_withironfeat` feat0：−12.318 nm；
- 其余为水体、白云母—碳酸盐混合及宽窗口特征。

这些特征均不携带仲裁窗口。异常更可能反映宽窗口内多极小值、连续统选择或重采样后最小值迁移，而不是仲裁中心直接出错。优化前应先确定目标吸收带，不能简单把最大偏移当作误差并强行改窗口。

## 4. 浅吸收特征

仅三条特征在 EMIT 上深度 <0.03：

| 规则/特征 | EMIT 深度 | weight | 自约束 |
|---|---:|---:|---|
| dolomite_abundant feat1 | 0.01357 | 0 | 通过 |
| serpentine_chrysotile_withsecondfeat feat0 | 0.01642 | 0 | 通过 |
| gypsum.6+montmorilloniteNa.4 feat0 | 0.02610 | 0 | 通过 |

这些特征虽然不增加 weighted fit，却仍可能参与约束和规则语义。**不能因浅或 weight=0 就直接删除。** 若优化，需要分别测量其排除假阳性的贡献。

## 5. 可优化方向与优先级

### P1：显式参考等价组（低风险、直接改善评估）

- 在规则和基准输出中保存 `reference_equivalence_group`；
- 对完全重复参考不再把规则名差异当作独立光谱证据；
- 分别报告规则级、参考等价组级和族级指标；
- 对 calcite/dolomite 丰度层和蛇纹石重复规则，明确其区分来自约束而非独立参考形状。

这比继续调整拟合阈值更能提高评估客观性。

### P1：覆盖范围和中心状态诊断（低风险）

- 对 41 条 SWIR-only 原生参考显式报告覆盖边界；
- 不做外推填补，不把缺失 VNIR 当成负证据；
- 在诊断输出中记录 `VALID / EDGE_MINIMUM / NONFINITE_VERTEX / OUTSIDE_TRIPLET / OUTSIDE_FEATURE`；
- 对多极小值宽窗口增加人工复核标记。

### P2：碳酸盐丰度层与重复规则语义（中风险）

- 将 abundant/plain 更明确地作为规则层或丰度元数据，而非假装为两条独立光谱类别；
- 评价时分别报告层内 calcite/dolomite 归属和丰度层归属；
- 合并规则前必须审计不同约束，不能因为参考相同就直接删除规则。

### P2：lowFe 打分变体（中高风险）

lowFe 的 feat2 压分属于官方规则继承。若需优化，可提供显式变体并比较原规则与变体的低铁保留、误报和黄金差异；不应为追求低铁命中率而静默破坏 MICA 字段保真。

### P3：宽窗口和多极小值特征（需人工复核）

对 75.954 nm 等异常先绘制连续统移除曲线，判断是否需要局部目标子窗口。只有确认诊断目标后才修改端点，并同步回归与 MICA 保真边界。

## 6. 不建议的优化

- 不因 weight=0 删除特征；
- 不因深度浅就降低门槛或强制启用特征；
- 不把重复参考的规则名差异当成独立验证样本；
- 不用当前参考自识别率直接估计真实场景精度；
- 不在黄金回归失败时自动重建基线；
- 不仅凭中心偏移直接修改仲裁窗口。

## 7. 当前验证状态

- 离线完整测试：40 passed / 0 failed；
- 当前编译、行限制、链式 alive-pixel 和单谱专项均通过；
- 黄金场景回归仍为 FAIL，未重建；
- 本审计未修改算法或规则，只增加逐特征证据和优化优先级。

## 8. 产物

- `output/reference_diagnostic_audit_v3/feature_audit.csv`：142 条特征逐项数值、状态和标记。
- `output/reference_diagnostic_audit_v3/rule_audit.csv`：77 条规则的覆盖、自识别、仲裁和重复组。
- `output/reference_diagnostic_audit_v3/duplicate_groups.csv`：六组完全重复参考。
- `output/reference_diagnostic_audit_v3/summary.json`：汇总。
- `output/reference_diagnostic_audit_v3/reference_classification.log`：参考分类过程日志。
