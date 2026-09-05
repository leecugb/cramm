# Changelog

## v1.5.0.post1 — README 图片链接修复（2026-09-05）

仅打包元数据修复，代码零变化：README 两处插图由相对路径改为
raw.githubusercontent.com 绝对 URL,PyPI 项目页图片正常显示
（PyPI 不渲染相对路径；1.5.0 页面为发布时快照，无法就地修改）。

## v1.5.0 — 碳酸盐仲裁启用按丰度层对内竞争（2026-09-02）

碳酸盐仲裁由"重复窗声明式零翻转"改为**按丰度层分对内竞争**：新增
`CARBONATE_ABUNDANT_MINERALS`（calcite_abundant vs dolomite_abundant）与
`CARBONATE_PLAIN_MINERALS`（calcite vs dolomite）两个子族列表，`classify` 的
碳酸盐仲裁由一次全族调用拆为两次对内调用。对内两窗互斥
（dolomite [2.308, 2.328) vs calcite [2.334, 2.350)），带位正式参与
dolomite↔calcite 归属裁决；**丰度轴仍由 fit 独立决定**——两个子族仲裁组互不相交，
跨层翻转在结构上不可能。6 nm 死区 [2.328, 2.334) 继续收容 siderite-ish 中心
（~2327 nm 锚点）保持 argmax 赢家；carbonate_Fe_bearing / calcite.5+dolomite.5
维持无窗。规则库零改动（窗口沿用），仲裁器零改动（复用族锁定机制）。

- **影响面（EMIT 025 全场景实测）**：abundant 对双向零候选（事实零翻转）；
  plain 对 calcite→dolomite 翻转 **1599 像元**（0.10% 全场景 / 2.1% 碳酸盐赢家，
  中心分布 2.314–2.328，中位数 2.326），dolomite→calcite 零翻转；门控挡回
  817 候选（目标规则 fit 拒绝，100% 倒在 min_weighted_fit=0.64 /
  fit×depth≥0.045)。翻转像元重拟合 100% 仍在目标窗内、0 个 NaN 回退。
- **设计依据**：评估发现翻转候选的带位（2.314–2.328）显著偏离方解石锚点
  （2339 nm)，且 calcite fit 中位数 0.907 与全体赢家 0.915 相当——fit 证据与
  带位证据真正冲突的"双认领歧义像元"，由带位做决胜；形状证据反对者
  （dolomite r2<0.64）由目标 fit 门控挡回。
- **测试**：`test_carbonate_window_arbitration` 重写为钉死新语义（对内翻窗翻转、
  跨层锁定、死区/出窗/无效保持、目标 fit NaN 门控）；32/32 pytest 通过。
- **黄金链 rebaseline**：orth_rgb 恰 1599 像元类别翻转（calcite→dolomite 配色）；
  color_enhanced 同源着色变化（同 1599 drastic）；cal_image 68 像元重拟合跨档；
  mus/chl 图层零变化。串/并行 5/5 array_equal。

## v1.4.2 — 1nm 迁移边缘修复(代码审阅第 2 轮,2026-09-02)

针对 v1.4.1 1nm-only 迁移边缘的 6 项缺陷修复,bit-exact 保留(32/32 测试通过,
数值路径零改动——仅校验、错误信息与注释)。

- **make_paper_figures.get_splib_record 修复**:原实现调用本次迁移已删除的
  `_output_name_aliases`,所有论文图脚本必崩 `AttributeError`。改为经
  `docs/splib07_selection.json` 的 recno→rule 迁移映射表解析(2047/2253/2371/9262
  验证通过)。
- **output_name 契约校验 + 文档化**:`output_name` 是主参考唯一查找键
  (`_judge_reference_entry` / `_get_compiled_rules` / renderer 三处),此前
  `from_paths` 不校验——缺失时 classify 崩 KeyError,指向其他规则时静默用错谱。
  现校验每条规则 `output_name` 必须为 rf 内规则名字符串,类 docstring 补充契约。
- **>256 规则守卫恢复为 ValueError 并前移**:v1.4.1 将其降级为 `assert`,
  `python -O` 下被剥除后 uint8 `NUM_` 静默回绕(300→44),像素归错矿物。现恢复
  真正的 `ValueError` 且前移到 resample 之前(原位置需先跑完整个 257 规则重采样
  才报错)。
- **过时注释修正(2 处)**:`_judge_reference_entry` 注释声称的"int-record 别名"
  机制已被本次迁移故意删除(finding 1 正是被此类注释误导写出的),改为如实描述;
  `example_usage.py` 自定义规则文件格式注释删除已不存在的 `mixtures` /
  `wavelength_map` 顶层键说明。
- **legacy splib06b 报错信息明确化**:迁移自 ≤1.2.x 的用户传 splib06b 二进制,
  原得到 opaque 的 pickle 报错;现明确提示"legacy splib06b binary library was
  dropped in v1.4.0"并指向 1nm npz bundle。

## v1.4.1 — 代码审阅后的 bug 修复（2026-09-02）

代码级审阅后修复的 P1/P2 项,bit-exact 保留(`test_parallel` 5/5 array_equal,
`test_single_spectrum` Top-1 fit=0.9441 不变,41/41 测试通过)。

- **自定义异常继承层级修复**:`InvalidRangeError` / `InvalidLeftEndPointError` /
  `InvalidRightEndPointError` 由 `BaseException` 改为 `Exception` 子类。原实现会
  穿透 `except Exception`(在第三方 wrapper 如 tqdm 进度条中无法被捕获),修复后
  既可被 `except` 显式元组捕获,也可被 `except Exception` 兜底。
- **类型注解修复**:`MicaClassifier._resample_cache` 由 `Optional[Dict, np.ndarray]
  # type: ignore[assignment]` 修正为 `Optional[Dict[str, np.ndarray]]`(移除
  `type: ignore` 掩盖);`MicaClassifier.get_resample` 与 `MicaEngine.get_resample`
  返回类型由 `Dict[int, np.ndarray]` 修正为 `Dict[str, np.ndarray]`(id 删除后
  key 已是 rule-name 字符串)。
- **get_resample 克隆 fallback 改两趟装载**:原单趟循环依赖 `rf.keys()` 插入顺序
  保证 owner 先于 clone 被处理,克隆规则名若字典序在 owner 之后会误报
  `KeyError("cyclic / missing reference")`。改为 pass 1 装载所有 bundle 内有
  行的规则,pass 2 用 `while pending` 迭代解析克隆链(支持 clone-of-clone
  链式继承),无进展时才抛错。彻底消除对字典顺序的隐式依赖。
- **rf 重赋值自动失效缓存**:`get_resample` 入口新增 `id(self.rf)` 快照检测,
  若 rf 被重赋值为不同 dict 对象(`clf.rf = new_dict`),自动调用
  `invalidate_caches()` 丢弃旧缓存。best-effort 设计:id-only 检测不捕获
  in-place mutation(`clf.rf["x"] = ...` 或 `clf.rf["new"] = ...`),后者保留
  原有"stale-trap / KeyError"契约(由 `test_cache_contract` 文档化)。
- **规则数 ≤ 256 提前校验**:`MicaClassifier.__init__` 现在构造时即校验
  `len(rf) <= 256`(`classify` 中 `NUM_` 用 `uint8`),避免在长段循环中段失败。
  原 `classify` 内的检查降级为防御性 `assert`(捕获构造与调用间的 in-place
  添加)。

## v1.4.0 — 规则名作为专家规则与参考光谱库的唯一链接（2026-09-02）

- **id 字段彻底删除**:JSON 数据中 58 处 `reference.reflectance_record` 的 int
  记录号、19 处 `mix_XXXX` 混合谱逻辑标签,全部替换为 owning rule-name 字符串;
  顶层 `mixtures` 配方表删除。`temp_rf_notfeatures_renamed.json` 现仅含 `rf` 一个
  顶层键,每条规则的 `reference` / `not_absolute_features` / `not_relative_features`
  的 `reflectance_record` 都是 `rf.keys()` 中的 rule-name 字符串。
- **代码层 id 逻辑全删**:`MicaClassifier.__init__` 删除 `wavelength_map` / `dic3` /
  `ids` / `output_name_aliases` 四个参数;`from_paths` 删除 `own_rec_to_rule`、
  `extra_aliases`、`_resolve_ref` int 分支、synthetic `wavelength_map` 构建、
  `aliases` 装配,验证逻辑简化为"每个 reflectance_record 必须是 rf.keys() 中的
  rule-name 字符串"。
- **get_resample 极简化**:删除 `_output_name_aliases` int 别名装载循环、
  `mix_to_rule` 反推、`mix_id` 别名安装循环(~30 行)。`resampled1` 现仅含
  rule-name → ndarray 的纯净映射,克隆规则通过 `reference.reflectance_record`
  (已是 rule-name 字符串)直接继承源规则谱。
- **API 兼容别名删除**:`MicaEngine` 不再暴露 `.ids` / `.wavelength_map` / `.dic3`
  别名;`renderer.py` 改走 `rf["output_name"]` 而非 `reference.reflectance_record`
  访问主参考谱。
- **测试更新**:`test_core.py` 三处 `sorted(k for k in resampled1 if isinstance(k, int))`
  改为 `sorted(resampled1.keys())`;`test_custom_rules.py` 不再向 trimmed JSON 写
  `wavelength_map` 字段。
- **bit-exact 保留**:EMIT 场景全部 5 个渲染数组与 v1.3.1 基线 bit-identical
  (`test_parallel` 5/5 array_equal,无需重新基线 golden);`test_single_spectrum`
  Top-1 fit=0.9441 不变;41/41 测试通过。

## v1.3.1 — get_resample 用 npz 预烘焙谱作为权威（2026-09-02）

- **性能优化**:`MicaClassifier.get_resample` 直接从 1nm bundle 按 rule-name
  取预烘焙谱,删除运行时端元线性合成 + orphan fallback 路径(~80 行)。
  19 条混合规则的谱在 npz 打包时已烘焙好,运行时不再查 `mixtures` 配方表。
- **bit-exact 保留**:对 EMIT 场景全部 5 个渲染数组与旧基线 bit-identical
  (4 条与 npz 偏离的混合规则未进入 Top-1 像素)。`test_single_spectrum` 的
  Top-1 fit=0.9441 不变;`test_parallel` 5/5 array_equal。
- **自定义规则兼容**:克隆 / 裁剪规则库场景通过 `_output_name_aliases` +
  `reference.reflectance_record` 直接查找 fallback 路径继承源规则谱,
  `test_custom_rules` 7/7 通过。
- **`mixtures` 字段语义**:运行时不再读取,仅作端元配方的文档 / introspection
  用途;`get_resample` 仅用 `mix_to_rule` 字典安装 `mix_XXXX` → owning rule 的
  谱别名,以便 `resampled1["mix_7737"]` 等访问路径继续可用。
- **golden 重基线**:`tests/golden_arrays.npz` 原子替换,审计 0 diff pixel。

## v1.3.0 — 仅保留 1nm rule-face 轨道,删除 legacy / rf07 轨道（2026-09-02）

- **重大重构**:分类器仅运行 1nm rule-face 轨道,`cramm.classifier` /
  `cramm.mica_engine` / `mica_core_v07_1nm.py` 全部移除 legacy splib06b 与
  rf07 轨道分支,数值路径 BIT-EXACT 与原 1nm 轨道一致。
- **API 兼容**:`MicaEngine(reference_track=…)` 与
  `MicaClassifier.from_paths(reference_track=…)` 的 `reference_track` 参数保留,
  但被忽略;传入非 `None` / `"1nm"` 的值会抛 `ValueError`。
- **删除数据文件**:`cramm/data/rf.json`、`cramm/data/rf_splib07.json`、
  `cramm/data/splib06b`(21MB specpr 二进制)、`cramm/data/rf07_spectra.npz`
  全部移除;唯一规则库 `cramm/data/temp_rf_notfeatures_renamed.json`、唯一参考谱束
  `cramm/data/rf77_splib07_1nm.npz`(打包入 wheel 的 package-data)。
- **删除测试**:`tests/test_rf07_export.py`、`tests/test_rf07_engine.py`
  (依赖被删除的 rf07 npz 与 `rf_splib07.json`)。
- **删除一次性迁移脚本**:`docs/_splib07_stage*.py`、
  `docs/_map_rf_to_splib07_step*.py`、`docs/_verify_rf_splib07.py`、
  `docs/_splib07_tokens.py`、`docs/verify_reference_spectra.py`、
  `docs/verify_mcf_rfjson.py`(全部依赖已删除的 `_hyper_read_specpr` /
  `dic3` / `rf.json`)。
- **`make_paper_figures.py::get_splib_record` 重写**:不再走 `eng.dic3`
  (1nm-only 架构下为 `None`),改用 `eng._classifier._1nm_bundle` + int→rule-name
  别名翻译。
- **缓存键简化**:`get_resample` / `_get_compiled_rules` 的缓存键不再内嵌 track。
- **`pyproject.toml` `package-data`**:仅保留 `data/color_table.json`;
  后续追加 `data/temp_rf_notfeatures_renamed.json` 与
  `data/rf77_splib07_1nm.npz`(配置文件移入 `cramm/data/` 目录)。
- **规则库清理**:删除 `temp_rf_notfeatures_renamed.json` 中的死字段
  `wavelength_record`(reference 与 not_features 各级)与顶层 `wavelength_map`
  (53 条仪器网格映射);1nm 轨道不读取这些字段,代码内合成恒等映射
  仅供 API 兼容。规则库顶层 keys 由 `rf/mixtures/wavelength_map` 简化为
  `rf/mixtures`。
- **`PROJECT_CONTEXT.md` / `README.md`**:全篇重写以反映 1nm-only 架构。

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
