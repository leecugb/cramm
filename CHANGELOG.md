# Changelog

## v1.2.6 — 跨传感器变体审计：jarosite_K 改接 NIC4a、AMX8 改接 BECKb（2026-08-31）

- **审计**：对 npz 引用的全部 splib07 记录枚举同样品跨传感器变体（`_inspect_variant_audit.py`），
  53 条选谱参考中 43 条已是最优变体，AMX12/17 已 r=1.0000、AMX10/21 无更优变体；
  两处真实优化点经裁决采纳。
- **jarosite_K（29 号规则，rec 4875）NIC4aa→NIC4a**：D1-A 按质量字母（aa>a）误排——
  06b 原记录标记 W2R4N**a**，其 NIC4 源测量即 quality a 记录，NIC4a 与 06b r=**1.0000**
  （NIC4aa 的 0.9827 为真实重测差异），且覆盖起点更早（1.300 vs 1.424 µm）。
  经 RECORD_OVERRIDE 改接；29 号规则 r 0.9827→1.0000，53 条实物参考中 r<0.99 仅剩
  illite_gds4（0.9708，1.4 µm 覆盖裁决的已接受代价）。
- **AMX8（55 号规则，mix_7821）ASDNGb→BECKb**：端元 Calcite WS272/Dolomite HS102
  均为 BECK 测量，USGS 按仪器分别计算 AMX——同仪器的 BECKb 变体对配方合成
  r=**1.0000**（ASDNGb 0.9946），且覆盖更宽（0.229–2.976 µm）。仪器策略定稿：
  与选定端元同仪器的变体胜出；端元跨仪器时取最优可得变体（AMX10/21 保持 ASDNGb）。
- 计数口径不变：58 条 npz 实物记录 / 5 条 AMX 别名（合成 rec id 不变）。
- `golden_arrays_v07.npz` 已按更正后轨道重建；legacy 轨道不受影响（rf.json 不动）。

## v1.2.5 — 27 号规则改接 AMX17_NIC4b 实测混合记录（2026-08-31）

- **mix_7737↔AMX17 重新别名，改接 NIC4b 变体**（27 号 pyrophyllite.25+kaolinite.75）：
  v1.2.4 曾以"引擎端元合成与 AMX17_NIC4b r=0.9983、别名无额外保真度"为由撤销别名，
  但 AMX17_NIC4b 是 USGS **实测面积混合记录**（splib07a Record=13116），物理上比线性
  端元合成更接近真实混合——用户裁决采用之（合成 rec id 90017 回到 npz）。
  核对：与 v07 端元合成 r=1.0000（EMIT 网格 max|Δ|=0.034）、与 06b 配方合成 r=1.0000、
  无新增 NaN 波段；原生覆盖 1.3455–5.3062 µm（两端元 PYS1A/CM9 同为 NIC4，覆盖口径一致）。
- AMX 别名 4→5 条，npz 实物记录 57→58；线性合成规则 13→12 条
  （规则面口径不变：77 规则 / 70 唯一规则面参考）。仪器策略补记：选定变体必须对配方
  合成保真，保真前提下优先 ASDNG，否则取保真变体（AMX12→NIC4a、AMX17→NIC4b）。
- `golden_arrays_v07.npz` 已按更正后轨道重建；legacy 轨道不受影响（rf.json 不动）。

## v1.2.4 — AMX 变体审计：撤 AMX17 别名、AMX12 改接 NIC4a（2026-08-31）

- **根因**：USGS 按仪器分别计算 AMX 面积混合谱——BECK/NIC4 变体与同仪器端元的
  配方合成 r=1.0000（配方保真），但 v1.2.1 的"同质量优先 ASDNG（恒等烘焙）"
  策略未逐变体验证配方保真度。用户报告 27 号规则没有正确匹配，属实。
- **撤销 mix_7737↔AMX17 别名**（27 号 pyrophyllite.25+kaolinite.75）：
  AMX17_ASDNGb 与配方合成 r 仅 0.805（与任何 ASDNG 端元组合最高 0.956，
  该变体不遵循配方）；NIC4b 变体配方保真（对配方合成 r=0.998，与同仪器端元
  合成 1.0000；独立佐证：`docs/library_validation_report.txt` 中 AMX17 仅
  NIC4 变体以 0.9999 命中本规则），但引擎端元合成
  （0.25×PYS1A_NIC4+0.75×CM9_NIC4）与 AMX17_NIC4b 本身 r=0.9983——
  别名无额外保真度，按 AMX3/13/14 先例回到引擎端元合成。
- **mix_7745↔AMX12 改接 NIC4a 变体**（kaolinite.5+muscoviteMedhighAl.5）：
  对配方合成 r 0.897（ASDNGa）→ 0.985（NIC4a）。
- AMX 别名 5→4 条，npz 实物记录 58→57；AMX 别名对配方合成最小 r 0.9182→0.9618；
  线性合成规则 12→13 条（规则面口径不变：77 规则 / 70 唯一规则面参考）。
- `golden_arrays_v07.npz` 已按更正后轨道重建；legacy 轨道不受影响（rf.json 不动）。

## v1.2.3 — illite_gds4 splib07 记录换全覆盖重测版（2026-08-31）

- **illite_gds4（splib06b rec 4625）参考谱更换**：原按 D1-A 同仪器策略选
  `Illite_GDS4_Marblehead_BECKb_AREF`（r=0.9973），但 splib07 删除了其
  1.35–1.42 µm 水汽吸收带（06b 该区间有 100 个有效采样，BECKb 仅剩 5 个，
  npz 中只能线性桥接）。经裁决改用同样品重测记录
  **`Illite_GDS4_Marblehead_ASDNGb_AREF`**：1.4 µm 带有 101 个真实采样，
  整数 nm 网格使 1 nm 主网格烘焙为恒等拷贝；代价为全段 r 降至 0.9708
  （整体反射率水平略偏高）。规则特征窗（2.2/2.35 µm）内两记录与 06b
  几乎重合，1.4 µm 不在任何规则特征窗内，分类行为影响可忽略。
- 实现为 stage1 选谱脚本的 `RECORD_OVERRIDE` 机制（4625→ASDNGb，
  裁决理由内嵌注释并写入 `splib07_selection.json/md`）；`rf07_spectra.npz`
  重烘（58 条记录中换 1 条），53 条实物参考中 r<0.99 的现为
  illite_gds4（0.9708）与 jarosite_K（0.9827）两条。
- `golden_arrays_v07.npz` 已按更正后轨道重建；legacy 轨道不受影响（rf.json 不动）。

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
