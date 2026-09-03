# rf77_splib07_1nm.npz 生成逻辑审计报告

> 日期：2026-09-02 ｜ 审计脚本：[`docs/_audit_rf77_bundle.py`](_audit_rf77_bundle.py)（离线可复跑,不依赖 USGS splib07 库 / splib06b)
> 对象:`cramm/data/rf77_splib07_1nm.npz`（77 rule × 2151 band @ 1nm,1nm 轨道唯一参考源)
> 结论:**内容级验证 7 组 30 项全部 PASS**;主要风险为生成脚本不可复现(见"三、风险")。

---

## 一、生成管线(从 git 历史与文档复原)

```
splib06b(旧 rf.json 参考源)                USGS splib07 库(D:\usgs_splib07)
        │                                          │
        ▼                                          ▼
┌─ stage1 选谱(docs/_splib07_stage1_selection.py,a24c2ec 删除)────────┐
│ 策略 D1-A:同仪器+同测量类型优先 → 组内质量字母最高 → r(vs 06b)最高    │
│ 覆盖判据(引擎口径):splib07 记录经引擎 _resample_ 重采样到真实 EMIT   │
│ 网格后,规则特征区间内不得出现"06b 有值而 07 为 NaN"的新增空洞         │
│ + 人工裁决 RECORD_OVERRIDE(illite_gds4 BECKb→ASDNGb、jarosite_K      │
│   NIC4aa→NIC4a、dry_veg_nongrass LP-Needles-3→2、AMX8/12/17 变体审计)│
│ 产物:docs/splib07_selection.json(53 实物 + 5 AMX + 12 合成)          │
└──────────────────────────────┬────────────────────────────────────┘
                               ▼
┌─ stage2 烘焙(docs/_splib07_stage2_export.py,a24c2ec 删除)──────────┐
│ 58 条记录(53 选谱 + 5 AMX)分段线性插值到 0.35–2.50 µm / 1 nm 主网格  │
│ 量程外 NaN、内部删除带线性桥接(Beckman 10 nm 采样空洞按构造消失)     │
│ 产物:rf07_spectra.npz(58 记录,含 meta provenance,已随 rf07 轨道删除)│
└──────────────────────────────┬────────────────────────────────────┘
                               ▼
┌─ stage3 58→77 rule-face 烘焙(脚本从未提交进 git,见风险 1)─────────┐
│ 每条规则一行:直接引用→对应实物记录;AMX/权重 1.0 别名→实物记录行;    │
│ 12 条合成混合→端元行按 .mcf 配比在 1nm 网格上加权                    │
│ 产物:rf77_splib07_1nm.npz(grid/rule/label/spectra)                 │
│ (7d3b2df 提交信息:"NaN outside native coverage; synth mixes        │
│  weighted on grid, engine order")                                  │
└────────────────────────────────────────────────────────────────────┘
```

label 三类标记:实物记录名(51 直接引用 + 7 复用共享)、`[AMX]`(5 条 USGS 计算混合)、
`[alias]`(GDS212/213 实测 intimate mixture,权重 1.0 别名)、`synth ...`(12 条配方合成)。

## 二、内容级验证结果(2026-09-02 实测,全部 PASS)

| 组 | 验证项 | 结果 |
|---|---|---|
| A | 网格:2151 点,0.35–2.50 µm,严格均匀 1 nm、单调 | ✅ |
| B | 77 行规则键与当前规则库 `rf.keys()` **顺序完全一致**;spectra 形状 (77, 2151) | ✅ |
| C | label 分类:5 `[AMX]` + 2 `[alias]` + 12 `synth` + 60 实物 = 77 | ✅ |
| D | 实物行 label 与 `splib07_selection.json` 选定记录一致;无 selection 条目的恰为 12 条 synth | ✅ |
| E | **无内部 NaN**(桥接烘焙声明成立);无全 NaN 行;量程外 NaN 正常 | ✅ |
| F | AMX 5 条 label = AMX8_BECKb / AMX10/21_ASDNGb / AMX12_NIC4a / AMX17_NIC4b;GDS212/213 alias label 正确 | ✅ |
| G | **12 条合成混合行 = 端元行按旧 rf.json mixtures 配比加权和,max\|Δ\|=0.00e+00 bit-exact,NaN 掩码完全一致**(旧 rf.json 取自 git 历史 11b0f53) | ✅ |
| H | `docs/rf77_splib07_1nm.csv` 镜像:网格/规则序/label 全一致;数值差 max 5e-7 = csv 6 位小数舍入(cosmetic) | ✅ |
| J | 全部有限值 ∈ (0, 0.968],无非正样本 | ✅ |
| K | **splib07 原生谱 → 烘焙行保真**(需本机 usgs_splib 包 + splib07 库):58 条选定记录全部在库,按 stage2 同口径重新烘焙后与 npz 对照——**65/65 实物规则行 max\|Δ\|=0.000e+00 bit-exact,NaN 掩码全等**(2026-09-02,本机 `/home/lee/Downloads/usgs_splib07` 2457 条记录) | ✅ |

复跑方式:仓库根目录 `python docs/_audit_rf77_bundle.py`,退出码 0 = ALL PASS。
K 组为可选段(无 usgs_splib 包或库时自动 SKIP,不影响 A–J 离线核心)。

## 三、风险与缺口

1. **P1 — 生成脚本不可复现**:stage3(58→77)烘焙脚本**从未提交进 git**(本机
   Untitled1.ipynb 只有读取代码);stage1/2 脚本可从 git 历史(11b0f53)恢复,但硬编码
   `D:\` 路径、依赖外部 `usgs_splib` 模块和已删除的 splib06b `dic3`。
   **2026-09-02 更新:此风险已大幅缓解**——本机已确认装有 usgs_splib v1.3.0(源码备份
   于 `/media/lee/共享14/backup/my/usgs_splib`)和完整 splib07 库
   (`/home/lee/Downloads/usgs_splib07`),K 组验证证明 npz 全部 65 条实物行可由
   本机库 bit-exact 重新烘焙,12 条 synth 行由端元加权 bit-exact 重构——**npz 已可在
   本机完整复现**(唯一不能复验的是与 splib06b 的相关性对比,06b 库已删除)。剩余缺口:
   stage1 选谱的 D1-A 打分/裁决过程本身仍不可重跑(依赖 06b)。
2. **P2 — provenance 外挂**:58 记录版 npz 曾内置 meta(每记录来源),77 行版只有
   label 字符串;完整溯源依赖 `docs/splib07_selection.json` 存活(已随仓库管理)。
3. **P3 — 合成口径语义变化(已接受的既有决策)**:旧引擎口径"端元先重采样到传感器
   波段再加权",烘焙口径"1nm 网格先加权再重采样"。`_resample_` 对每波段为线性加权,
   端元 NaN 掩码一致时两者数学等价;本审计 G 组证实 12 条 synth 端元掩码一致。该差异
   当年经 stage4 双跑仲裁(文档已删),属 v1.2.x 系列已接受行为。
4. **附带观察**:当前规则库 77 条 `reference.reflectance_record` 全部等于规则名自身,
   `get_resample` 的两趟克隆解析对内置库是死路径(仅自定义克隆规则触发)——与
   PROJECT_CONTEXT.md 描述一致,无误。

## 四、附:审计方法与判据来源

- 生成逻辑叙述复原自:`git show 11b0f53:docs/_splib07_stage1_selection.py` /
  `..._stage2_export.py`(已删脚本)、提交 7d3b2df 提交信息、`docs/splib07_selection.json`
  (含 adjudications 裁决记录)、`docs/SESSION_HANDOFF.md`(已删,11b0f53)。
- 数值验证全部基于仓库内现存产物 + git 历史 + 本机 splib07 库(K 组),无需 splib06b。
- 实物行的"splib07 原生谱 → 1nm 烘焙"环节当年由 stage2 导出审计(`docs/splib07_export_audit.md`,
  已删)首次覆盖;**2026-09-02 已由本审计 K 组在本机复验:65/65 行 bit-exact**,该环节不再
  是未覆盖缺口。
