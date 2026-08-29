# rf.json 参考光谱迁移 splib07 方案

> 日期：2026-08-29 ｜ 状态：提案（未实施）
> 依据：`docs/rfjson_splib07_mapping.md`（77 规则样品级映射）、`docs/rfjson_splib07_verification.md`（51/51 光谱核实）

## 0. 前提判断

1. **可行性已验证**：51 条唯一实物参考谱在 splib07 全部有对应，50 条 r≥0.9995（0.35–2.6 µm），2 条 mix 别名规则（GDS212/213）有同款实测记录，8 条线性合成有 AMX 同配方对应。
2. **但迁移 ≠ 无代价**：r<1.0000 意味着拟合分全变 → 黄金基线必须重建、仲裁普查必须重测、论文/文档必须同步（与 2026-08-26 绿泥石窗口变更同级工作量，且影响面更大——全部 77 条规则而非 4 条）。
3. **项目卖点冲突**：CRAMM 的核心学术主张是与官方 .mcf v6a 逐字段零差异（`docs/MCF_vs_rfjson_verification.md`）。替换参考谱即打破零差异。**因此迁移必须做增量（新规则文件），不得替换 rf.json。**

## 1. 三个决策点

### D1 选谱策略：同源优先（推荐 A）vs 质量升级（B）

| | A：同仪器同类型（推荐） | B：升级最优记录 |
|---|---|---|
| 选谱 | splib07 中与原 06b 记录同仪器+同测量类型者（BECK AREF→BECK AREF，Nicolet RREF→NIC4 RREF，ASD FR→ASDFR/ASDNG AREF） | 每样品取最优（ASDNG/ASDHR 全段 AREF 优先） |
| 光谱差 | r≥0.9995，扰动最小 | 部分样品是全新测量，扰动大 |
| 审计难度 | 黄金差异小，可归因 | 差异大，需逐规则论证 |
| 副作用 | 保持现状 | 可能改善 VNIR 特征覆盖（如 chlorite_lowFe feat2 0.51–1.74 µm——但那是 .mcf 继承的不对称，"改善"反而偏离官方行为，见 `docs/lowfe_feat2_bias.md`） |

**推荐 A**，B 留作后续 v1.3 实验轨道。例外需逐条裁决：`dry_veg_nongrass`（splib07 仅一条 r=0.884 的重测记录，差异最大）、质量等级升级的同名记录（如 Nbbb→Naaa 是否采用）。

### D2 打包方式：烘焙导出（推荐）vs 运行时依赖

| | A：一次性导出进包（推荐） | B：运行时读 splib07 |
|---|---|---|
| 形态 | 导出选中谱为 `cramm/data/rf07_spectra.npz`（波长+反射率+元信息），引擎从 npz 读 | 引擎内置 splib07 ASCII 读取器或依赖 usgs_splib |
| 依赖 | 零新增，引擎保持自包含 | 用户须另装 1.5 GB 光谱库 |
| 可复现性 | 位级固定，黄金基线稳定 | 库版本漂移风险 |
| splib06b 退役 | 可同时退役 dic3 加载路径（对新规则文件而言） | 同左 |

**推荐 A**。引擎只认两种参考来源：rf.json（splib06b dic3，现状）与 rf_splib07.json + rf07_spectra.npz（新）。

#### D2 增补（2026-08-29，用户提议采纳）：统一 1 nm 主网格

rf07_spectra.npz 采用**统一波长主网格**：350–2500 nm @ 1 nm（2151 点，与 splib ASD 标准表对齐；不取 300 起点——EMIT 381 / EnMAP 420 / PRISMA 400 均无 <350 nm 需求，避免 50 列全 NaN 前缀）。

- 格式：`grid`(2151) + `spectra`(N, 2151) + NaN 掩码（部分量程记录如 NIC4 RREF <1385 nm 段填 NaN）+ 元信息；`wavelength_record` 间接层取消。
- 数学性质：分段线性谱**上采样无损**——BECK 10 nm → 1 nm → 传感器网格 ≡ 直接 10 nm → 传感器网格（逐位相同）；ASD 1 nm 整数点对齐为恒等拷贝；唯一真实损失是 NIC4 ~0.93 nm → 1 nm 的轻微降采样，导出时须量化（原生 vs 主网格在 2200/2250/2330 nm 带心拟合差，写入导出审计）。
- **不回改 rf.json**：splib06b 轨道保持原生网格（重构无收益且破坏 .mcf 路径）；主网格仅用于 splib07 轨道。
- 非性能优化：`get_resample` 按传感器缓存，每场景仅重采样 51 条一次；本项价值在数据模型简约。

### D3 版本与兼容：双规则文件（推荐）

- `cramm/data/rf.json` **保持不动**——.mcf v6a 保真基线，论文现行结论全部绑定它。
- 新增 `cramm/data/rf_splib07.json`：结构同 rf.json，`reference` 改为指向 rf07_spectra.npz 的键（样品ID_传感器质量_类型）；17 条线性合成规则按新端元谱重算混合谱后同样烘焙；2 条 GDS212/213 规则直接引用实测记录。
- `MicaEngine(rule_file=...)` 选择规则库，默认仍 rf.json（行为不变）。
- 版本号：新规则文件标志 v1.2.0 轨道。

## 2. 实施阶段

**阶段 1：选谱与覆盖校验**（纯分析，无行为变更）
- 以 verification 报告为底，按 D1-A 生成 51+2 条选谱表；
- **新增逐规则特征覆盖检查**：所选 splib07 记录在该规则全部 diagnostic_features 端点范围内必须有有效数据（NIC4 RREF 从 1.385 µm 起，带 VNIR 特征的规则必须选 AREF 全段记录——现 rf 已如此，迁移须复核）；
- 产出：`docs/splib07_selection.md` + 选谱表 JSON。

**阶段 2：导出管线**
- 脚本：usgs_splib 读选中谱 → 统一校验（单调、去零端、范围）→ 写 rf07_spectra.npz；
- 17 条合成规则按 rf.json mixtures 权重在新端元上重算（沿用引擎现有 resample 口径，保证与分类路径一致）；
- 单元测试：npz 中每条谱与 splib07 源记录逐位一致。

**阶段 3：引擎适配**
- MicaClassifier 支持 rule_file 分支加载（npz 参考源）；缓存契约不变（invalidate_caches）；
- 单元测试：新规则文件串行/并行逐比特一致（沿用现有并行纪律）。

**阶段 4：双轨黄金与场景对比**
- 为 rf_splib07.json 建立独立黄金基线（tests/golden_arrays_v07.npz）；
- 全场景双跑：rf.json vs rf_splib07.json，输出五图层差异普查 + 仲裁翻转数对比 + mus/chl/cal_center 差分布；
- 预期：差异小（r≥0.9995），但必须实测——重点看仲裁窗口边缘像元的归属漂移。

**阶段 5：文档与发布**
- 新增 `docs/MCF_vs_rf07_diff.md`（与 .mcf 的差异声明：参考谱来源+逐条 r 值）；
- README/verification_matrix/paper 增补 v1.2.0 轨道说明（不改动既有结论）；
- CHANGELOG：v1.2.0 — splib07 reference track。

## 3. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 打破 .mcf 零差异主张 | rf.json 不动，新轨道单独声明（D3） |
| dry_veg_nongrass r=0.884 | 阶段 1 逐条裁决：可保留 06b 谱（npz 也收 06b 来源）或接受重测差异并记录 |
| 混合规则端元重算口径漂移 | 重算走引擎同一 resample 函数，禁手写第二套插值 |
| 黄金基线膨胀 | 双 npz 双基线，CI 各自独立 |
| 工作量 | 与绿泥石窗口变更同流程，但审计算子在阶段 4 需新写（差异预期非零且全域） |

## 4. 不做清单

- 不替换/删除 rf.json 与 splib06b 加载路径；
- 不引入 splib07/usgs_splib 运行时依赖；
- 不改变任何诊断特征参数（端点/权重/窗口原样继承，仅换参考谱）；
- 不动 dry_veg_nongrass 之外的 r≥0.9995 选谱（除非阶段 1 覆盖检查失败）。
