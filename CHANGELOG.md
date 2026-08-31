# Changelog

## v1.2.2 — dry_veg_nongrass splib07 映射更正（2026-08-31）

- **修正 v1.2.0 起存在的选谱错误**：dry_veg_nongrass（splib06b rec 12794，
  占 2 个规则槽）此前按名称精确匹配选了 splib07 `LP-Needles-3_ASDFRa_AREF`
  （r=0.8839，裁决为"仅存重测记录"）。经核查，splib07 的 LP-Needles-3 是 USGS
  **新测的健康绿叶谱**（红边+液态水吸收），并非对应记录；06b 'LP-Needles-3'
  的真正对应是 splib07 **`LP-Needles-2_ASDFRa_AREF`**（编号重排，r=0.999995）。
- 选谱 token 更正（Needles-3→Needles-2，`_splib07_tokens.py` 附编号错位注释），
  `rf07_spectra.npz` 重烘（58 条记录中换 1 条），53 条实物参考中 r<0.999 的
  仅剩 jarosite_K（0.9827）与 illite_gds4（0.9973）两条重测差异。
- `golden_arrays_v07.npz` 已按更正后轨道重建；legacy 轨道不受影响（rf.json 不动）。

## v1.2.1 — AMX 计算混合谱接入 splib07 轨道（2026-08-30）

- 19 条混合配方中的 5 条在 splib07 有**同样品同配比**的 AMX 预计算面积混合记录，
  现烘焙进 `rf07_spectra.npz`（合成 rec id 90008/90010/90012/90017/90021），
  规则文件中以权重 1.0 别名接入（GDS212/213 先例），不再由引擎端元合成：
  mix_7821↔AMX8、mix_7715↔AMX10、mix_7711↔AMX21、mix_7745↔AMX12、mix_7737↔AMX17
  （仪器策略：同质量优先 ASDNG——整数 nm 网格使烘焙为恒等拷贝）。
- AMX 记录与按 .mcf 配方从选定端元的数值加权和存在有界差异
  （EMIT 网格 r=0.918–0.994，max|Δ|≤0.21）——AMX 由 USGS 用其自择端元记录预先计算，
  对 06b 端元合成同样 r≈0.92–0.99，差异不来自 06b→07 重测；逐条 r 值见
  `docs/splib07_selection.md` 与 `docs/MCF_vs_rf07_diff.md`。
- **拒绝 3 条端元失配的 AMX 映射**（AMX3/AMX13 用 KGa-1≠KGa-2、AMX14 用 HS295≠GDS96），
  维持按 .mcf 配方端元合成。
- npz 实物记录 53→58 条；规则面口径不变（77 规则 / 70 唯一规则面参考）。
- `golden_arrays_v07.npz` 已按新轨道重建；legacy 轨道不受影响（rf.json 不动）。

## v1.2.0 — splib07 reference track (2026-08-29)

新增 **splib07 参考谱轨道**，与既有 rf.json 轨道并存（双轨制）：

- `cramm/data/rf_splib07.json`：77 条规则同 rf.json **逐比特一致**
  （诊断参数原样继承 .mcf v6a 启用态），参考光谱来源换成 USGS splib07 同名样品记录
  （53 条唯一实物参考，D1-A 同仪器+同测量类型选谱，50/51 r≥0.99）；
  19 条混合配方同 rf.json 逐比特一致（v1.2.1 起其中 5 条改接 AMX 实物记录）。
- `cramm/data/rf07_spectra.npz`：53 条参考谱烘焙于统一 1 nm 主网格（350–2500 nm），
  分段线性、量程外 NaN、内部删除带桥接；运行时零外部依赖（不需要 splib06b/splib07）。
- 引擎：`MicaClassifier.from_paths` 支持规则文件顶层 `reference_source` 标记
  （或显式 `.npz` splib_path）加载烘焙参考包；`MicaEngine(rf_path=...)` 选择轨道，
  **默认仍 rf.json，既有行为不变**（`docs/MCF_vs_rfjson_verification.md` 结论不受影响）。
- 混合谱不烘焙：沿用 `get_resample` 既有"先传感器网格重采样端元、后加权合成"口径自动重算。
- 审计与实证（docs/）：选谱与特征覆盖校验、导出审计（BECK 稠密化在高斯核下非无损，
  max|Δ|≤1.03e-1 且有界）、全场景双跑差异普查（mus 1.43% / chl 0.005% / cal 0.078%，
  差异集中于族间仲裁边缘，可归因）、`.mcf` 差异声明（`docs/MCF_vs_rf07_diff.md`）。
- 测试：`tests/test_rf07_export.py`（npz 与 splib07 源逐位一致）、
  `tests/test_rf07_engine.py`（引擎分支契约 + 串并行逐比特）、
  `tests/test_parallel_v07.py` + `tests/golden_arrays_v07.npz`（v07 全场景黄金基线）。

## v1.1.0

（此前版本：USGS MICA 纯 Python 重实现 + 深度比约束扩展 + 白云母/绿泥石/碳酸盐
吸收中心产品线；详见 git 历史。）
