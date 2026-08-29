# chlorite_lowFe feat2(VNIR)系统性压分实测归档

> 归档日期:2026-08-29 ｜ 行为不变(方案 A+C),仅记录规则内在不对称性
> 复现脚本:`docs/diagnose_lowfe_feat2_bias.py`(tile = 测试场景 rows 440:540, cols 160:260,绿泥石富集区 3109 px)

## 问题

四条纯绿泥石规则中,只有 chlorite_lowFe 携带第三个诊断特征 feat2(VNIR 0.51–0.55 / 1.69–1.74 µm,权重 0.3;官方 .mcf v6a 原样继承,逐字段核验零差异的一部分)。其打分结构为 `0.0×fit0 + 0.7×fit1 + 0.3×fit2`,而其余三条为 `1.0×fit1`。用户质疑:feat2 是否对 lowFe 不公平?

## 实测数字(tile,对通过 lowFe 全部门槛的 867 px)

| 指标 | 数值 |
|---|---|
| feat1(2.3 µm)原始 fit 中位数 | 0.9075 |
| feat2(VNIR)原始 fit 中位数 | 0.2849 |
| fit2 < fit1 的像元占比 | **100%** |
| 分数惩罚 0.3×(fit1−fit2)中位数 / p90 | +0.187 / +0.222 |
| 加权 fit 中位数:现行 vs 假想 feat1-only | 0.719 vs 0.9075 |
| 纯因 feat2 拖累跌破 min_weighted_fit 0.64 被拒 | 12 px(feat1-only 时为 0) |
| head-to-head vs clinochlore(447 px 双通过) | 现行得分差中位数 −0.232(0 胜);feat1-only 时 −0.042(仍 0 胜) |

## 机理

1. feat2 是 1.2 µm 跨度的直线连续统(0.53→1.715 µm),横跨仪器拼接段与 1.4 µm 水汽带两翼;对真实地表像元(土壤/植被/混合),直线连续统是结构性坏模型,fit 系统性低不是噪声。
2. feat2 的存在是**数据可得性产物而非平衡设计**:四条参考谱仅 SMR-13(rec 2047)为全波段 AREF 记录,其余三条(GDS158 / SC-CCa-1 / SMR-15)是 ~1.4 µm 起步的 RREF 分段记录,VNIR 段根本无数据可加特征。

## 净效应评估(为什么不改)

- 压分方向**保守**:宁可少报 lowFe,不产生假阳性。
- 系统自带纠偏通道:`chl_center` 仲裁窗口 [2.245, 2.248) 会把真正低铁的中心从 clinochlore 胜家中翻回 lowFe(全场景生产普查翻回 133 px,docs/arbitration_stats.md)。标签可能漏报,但中心图层数值不受影响。
- 保真性优先:feat2 属官方 MICA 规则,项目卖点是与 .mcf v6a 逐字段零差异(docs/MCF_vs_rfjson_verification.md);修改将打破零差异纪录并需重建黄金基线。
- tile 内 head-to-head 显示:即使归还 feat2 压的分(−0.232 → −0.042),lowFe 在富铁场景依旧 0 胜——该场景的 clinochlore 归属是光谱真实的,feat2 只是放大了差距而非颠倒了归属。

## 结论

feat2 对 lowFe 存在系统性、单方向(~0.19 fit 单位)的打分惩罚,属官方规则的内在不对称性。行为保持不变;若未来针对低铁绿泥石富集场景做定量反演,应意识到 lowFe 标签被系统性低估,判读以连续 `chl_center` 图层为准。
