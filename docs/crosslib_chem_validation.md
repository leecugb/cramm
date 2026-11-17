# 化学验证腿(mus_center / chl_center vs 实测化学)

> 日期:2026-09-08 | 脚本:`docs/crosslib_chem_validation.py`(可重复执行) | 测量:`MicaEngine.spectrum_analysis(raw=True)` 逐谱取 mus_center/chl_center(nm)

## 定位

- A/B 两链光谱来自 USGS splib07——与 bundled rf77 参考同库(部分同材料),定位为**工程一致性核验**:产品代码路径测出的带中心是否与归档链(独立脚本、不同测量口径)及化学趋势一致。
- C 组 RELAB 6 样与 bundled 参考零同源(经阶段1 排重审计),是独立证据,但 n 小,轶事级。
- 本腿不测鉴定准确率(阶段3 已测);测"产品数值 ↔ 化学"的物理一致性,即 [[mus_center/chl_center 相图]] 作为参考标尺的经验地基。

## 结果汇总

| 池 | 谱数 | 产品触发 | 回归(化学→带中心) | Pearson r | Spearman ρ | 与归档 λ 的 RMSE (nm) |
|---|---|---|---|---|---|---|
| A_muscovite_USGS | 22 | 22 | -2.7531 nm/单位, n=22 | -0.9665 | -0.8649 | 0.538 |
| B_chlorite_USGS | 44 | 34 | 24.5041 nm/单位, n=34 | 0.7994 | 0.8439 | 1.809 |
| C_RELAB_chlorite | 4 | 3 | 30.4457 nm/单位, n=3 | 0.9764 | 1.0 | — |
| C_RELAB_mica | 2 | 0 | — | — | — | — |

## 逐谱数据

见 `crosslib_chem_validation.csv`(72 行);双联散点 `crosslib_chem_validation.png`。

## 备注

- Fe# 约定(沿用 2026-08-11 重建定版):全 Fe 视为 Fe²⁺,n(Fe)=2·Fe₂O₃/159.688+FeO/71.844,Fe#=n(Fe)/(n(Fe)+n(Mg))。
- 产品触发率本身是结果:mus_center 仅在像元被判为白云母规则时非零,chl_center 同理(产品定义,非缺陷)。
- SMR-14(Prochlorite 结构异常)与 NMNH83369(归档 CR 拖尾假象)在归档链中为黑名单;本表保留全部测量,读者可按 sample 列剔除复核。
