# MICA 算法合规性审计报告

> 审计日期:2026-08-25 ｜ 基线:commit 82c32ef(thuringite + 族锁定之后)
> 审计方法:逐函数对照 USGS 官方定义——DS787(方法学章节)、kokaly2011(PRISM/MICA 论文)、.mcf(2014 v6a)字段语义
> 前置核验(本报告不重复):规则库字段级零数值不一致(verify_mcf_rfjson.py);参考光谱数据级 corr 中位 0.99972(verify_reference_spectra.py)

## 结论

**CRAMM 严格执行 MICA 算法。** 计算核的每一个环节——连续统去除、线性回归 r²、缩放参考深度、特征加权、五层约束过滤、NOT 特征排除、约束违反置零、按加权拟合选优、全零无匹配——均与官方定义一致。审计发现的唯一偏差点在**文档措辞**而非代码(README/algorithm_flow 误写为 argmax(fit×depth),代码实际 argmax(weighted fit),后者才是 MICA 规范),已在本轮修正。

## 逐项对照表

| # | MICA 定义(出处) | CRAMM 实现 | 判定 |
|---|---|---|---|
| 1 | 连续统去除 RC(λ)=RO(λ)/RL(λ)(DS787 Eq.1) | `_diagnostic_feature`:直线连续统过两端点(均值波长, 均值反射率)点,逐通道相除 | ✅ 一致 |
| 2 | 端点取 .mcf CONTINUUM_ENDPTS 四值确定的波长区间 | `_precompute_feature`:idx_l/idx_r 区间通道,反射率与波长各自取均值 | ✅ 一致 |
| 3 | 拟合 = 连续统去除后参考特征与像元特征的线性回归 r²(kokaly2011;"Tetracorder 用 r,MICA 用 r²") | `_fit_r2_depth`:闭式 2×2 最小二乘(含截距 k1),r² = ss_reg/ss_tot | ✅ 一致 |
| 4 | 深度不直接计算,用"缩放(scale)到像元光谱的参考特征"取值(DS787;kokaly2011 降噪设计) | depth = k0·(1 − con_.min) = k0 × 参考特征深度;"scale"为纯乘性(不含 k1),与 docs/DS787_summary.md 的释义记录一致 | ✅ 一致* |
| 5 | 特征加权:weighted fit = Σ wᵢ·fitᵢ,Σwᵢ = 1(kokaly2011) | `_judge_reference_entry`:fit += r2×weight;77 规则权重和=1(6 条偏差 ≤2e-6,系 .mcf 四位小数舍入,原样继承) | ✅ 一致 |
| 6 | 特征级约束:fit / depth 阈值(DS787;`.mcf` FIT_/DEPTH_CONSTRAINTS) | 逐特征 r2 ≥ fit_c、depth ∈ [dmin, dmax],违反置 NaN | ✅ 一致 |
| 7 | 连续统约束:Rc1/Rc2 水平、Rcmid、端点比值(DS787 fig.5B) | 8 槽位 left/mean/right min/max + ratio min/max(右/左) | ✅ 一致(1,136 槽已字段级核验) |
| 8 | NOT 特征:命中即排除(kokaly2011;"weighted fit zeroed out") | 绝对型:r²≥c 且 depth≥c → 置 NaN;相对型:r²≥c 且 depth ≥ 阈值×第 1 诊断特征原始深度(`.mcf` "1 0.0800" = 特征 1 × 0.08) | ✅ 一致(80 处引用已字段级核验) |
| 9 | 材料级约束 WEIGHTED_FIT_DEPTH_CONSTRAINTS(4 槽) | min_weighted_fit / min/max_weighted_depth / min_F×D,逐槽对应 | ✅ 一致(77×4 已字段级核验) |
| 10 | 约束违反 → 该材料 weighted fit 置零(kokaly2011) | 各层拒绝一律置 NaN,汇总后 NaN→0 | ✅ 一致 |
| 11 | 最佳匹配 = 加权拟合最高者(kokaly2011 原文 "highest weighted fit value") | `im = FIT.argmax(1)`,FIT 为加权拟合矩阵(拒绝已置零) | ✅ 一致 |
| 12 | 全部置零 → 无匹配(kokaly2011) | fit_pos = FIT.max(1) > 0,全零像元为背景 | ✅ 一致 |
| 13 | 无效端点配置(区间为空等)的处理 | 抛 InvalidRange/LeftEndPoint/RightEndPoint,该规则列置零并记录日志;串并行行为一致 | ✅ 合理工程化 |

\* 第 4 项:IDL 源码不可得,"scale 是否含回归截距 k1"无法做字节级确认;仓库调研记录(DS787_summary.md §21)采用乘性 scale 释义,且 1,136 个约束槽在 CRAMM 定义下经生产验证有效。

## CRAMM 声明的扩展(非 MICA 内容,均有文档声明)

1. **深度比约束** `max_depth_ratio_feat1_over_feat0`(9 条规则)——抑制白云母误报;
2. **吸收中心波长仲裁**(12 条规则,仅整景;族锁定后跨族翻转结构不可能)——单光谱 Top-N 不启用;
3. **混合物端元线性合成**(19 条规则)——替代 .mcf 实物混合谱,数据级 corr 中位 0.99474;
4. **运行时高斯重采样**——替代 HyMap 预卷积库,传感器无关;与预卷积库数据级比对 corr 中位 0.99972。

## 观察项(不改变合规结论)

1. **k0 > 0 掩膜**:负斜率像元在 r² 计算前排除——保守护栏;IDL 对应行为不可考,但没有任何规则的约束按负斜率情形标定,实际影响为零;
2. **`fd > minimum_fit_depth` 用严格大于**,其余阈值为 ≥——边界概率为零,无实际后果;
3. 闭式最小二乘承自前代 Python 移植 mica_app.py(代码注释),非直接译自 IDL;公式本身为标准 OLS 闭式解;
4. 活像元限制、编译路径、串行/并行等优化均有逐比特等价性测试钉死(check_compiled_path / check_rows_logic / golden 套件),不构成算法偏离。

## 文档修正(本轮已改)

- README.md「How it works」流水线:`argmax fit×depth` → `argmax weighted fit`(与 kokaly2011 原文一致);
- docs/algorithm_flow.md 第 1 步:同步修正,并注明 fit×depth 仅用于材料级 min_F×D 约束与 fd 输出层。
