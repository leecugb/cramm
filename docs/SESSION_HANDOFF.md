# CRAMM 会话交接文档（迁移恢复用）

> 保存时间：2026-09-01 ｜ 当前版本 **v1.2.6** ｜ HEAD `52d1a4d`（main，工作树干净）
> 用途：把当前工作上下文迁移到另一台电脑后，读本文件 + 本文件列出的关键文档即可无缝续作。
> **安全约束（持续有效）：只提交本地仓库，绝不 push 到 GitHub**（remote: github.com/leecugb/cramm.git）。

## 1. 环境（新电脑需对齐）

- Python：`C:\ProgramData\anaconda3\python.exe`（anaconda3，含 numpy/pandas/netCDF4/pyproj/pyresample/threadpoolctl）
- git：`C:\Users\86182\Downloads\PortableGit\cmd\git.exe`（**不在 PATH**；旧版 PortableGit 不支持 `:!` pathspec magic——`git add` 用显式文件列表；提交用 `git commit -F _commit_msg.txt`，事后删该文件）
- USGS splib07：`D:\usgs_splib07`（USGSLibrary；ASCII 头行 1 含 `splib07a Record=NNNNN`）——**必须随仓库迁移或重新下载**
- EMIT 场景：`d:\CRAMM\EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc`（1280×1242×285）
- PowerShell 5.1：无 `&&`，用 `; if ($?) {...}` 串联；不要用 PS cmdlet 编辑 UTF-8 文件
- 全场景双跑约 8–45 分钟（`docs/_splib07_stage4_dualrun.py`），后台跑

## 2. 双轨架构（现状）

- **legacy 轨道**：`cramm/data/rf.json` + splib06b——.mcf v6a 逐比特保真基线，**永远不动**；默认轨道。
- **v07 轨道**：`cramm/data/rf_splib07.json` + `cramm/data/rf07_spectra.npz`，经 `MicaEngine(rf_path=...)` 选择。
- 计数口径：77 规则（与 rf.json 逐比特一致）→ 70 唯一规则面参考（51 直接 + 19 混合）→ **58 npz 实物记录**（51 + 2 GDS212/213 别名 + 5 AMX：90008/90010/90012/90017/90021）。19 混合 = 12 引擎线性合成 + 2 GDS 权重 1.0 别名 + 5 AMX 别名。
- 黄金基线：`tests/golden_arrays.npz`（legacy）/ `tests/golden_arrays_v07.npz`（v07）双轨独立。

## 3. v1.2.1–v1.2.6 更正史（全部经用户裁决，细节见 CHANGELOG.md）

| 版本 | 更正 | 机制 |
|---|---|---|
| v1.2.1 | 5 条混合配方接 AMX 实物记录（90008+） | AMX_MAP 别名 |
| v1.2.2 | dry_veg_nongrass：LP-Needles-3→**LP-Needles-2**（USGS 编号重排） | 选谱 token |
| v1.2.3 | illite_gds4：BECKb→**ASDNGb**（splib07 删了 BECKb 的 1.4µm 带） | RECORD_OVERRIDE[4625] |
| v1.2.4 | AMX 变体审计：撤 AMX17 别名（ASDNGb 不遵循配方 r=0.805）；AMX12→**NIC4a** | AMX_MAP |
| v1.2.5 | 27 号规则重接 **AMX17_NIC4b**（Record=13116，实测面积混合优先于线性合成） | AMX_MAP（90017） |
| v1.2.6 | jarosite_K：NIC4aa→**NIC4a**（06b 遗产测量即 quality a，r=1.0000）；AMX8→**BECKb**（端元均 BECK，对配方合成 max\|Δ\|=0.0） | RECORD_OVERRIDE[4875] + AMX_MAP |

**定稿的仪器策略**：AMX 变体取与选定端元同仪器者（BECK 端元→BECK 变体，NIC4→NIC4）；端元跨仪器取最优可得（AMX10/21 保持 ASDNGb，r=0.96 有界差异已裁决接受）。选谱参考：遗产测量一致性优先于质量字母。

**拒绝的 AMX 映射（3 条，端元样品不一致）**：AMX3/AMX13（KGa-1≠KGa-2=5167）、AMX14（HS295≠GDS96=596）。

## 4. 当前质量状态

- 规则级 06b-vs-07 相关（`docs/rf77_corr_06b_vs_07.csv`）：**71/77 ≥ 0.9999**；r<0.99 仅 3 条已裁决接受：AMX21 0.9624、AMX10 0.9659、illite_gds4 0.9709
- 全场景双跑（`docs/splib07_dualrun_diff.md`）：orth 1.956% / mus 1.431% / chl 0.005% / cal 0.123%；AMX8 改 BECKb 后 v1.2.1–v1.2.5 的 1,637 像元 bin 平移已消除
- legacy 与黄金逐比特一致；v07 串并行逐比特一致（每次双跑自动验证）

## 5. 修改 v07 参考轨道的标准修复链（顺序不可乱）

1. `docs/_splib07_stage1_selection.py`（选谱/AMX_MAP/RECORD_OVERRIDE/裁决文案）→ 运行
2. `docs/_splib07_stage2_export.py`（重烘 npz）→ 运行
3. `docs/_splib07_stage3_rulefile.py`（重生成 rf_splib07.json）→ 运行
4. `tests/test_rf07_export.py`、`tests/test_rf07_engine.py`（计数断言随改动更新）
5. `docs/_splib07_stage4_dualrun.py`（后台，重建 golden_arrays_v07.npz；自动验证 legacy 逐比特 + v07 串并行逐比特）
6. `docs/_splib07_stage4b_readable.py` → `docs/_splib07_stage5_docs.py`（普查叙事如有机制变化需同步改写）
7. **rf77 派生交付物（不自动更新！）按序重跑**：`_inspect_rf77overlay.py` → `_inspect_rf77bake.py` → `_inspect_rf77corr.py`（corr 读 bake 的 1nm npz，顺序错会输出旧映射——v1.2.4 踩过）
8. CHANGELOG.md + pyproject.toml version → 本地提交（显式文件列表 add，commit -F）

## 6. 关键数据/文档索引

- 选谱表：`docs/splib07_selection.json/.md`（逐条 r、覆盖、裁决）
- 导出审计：`docs/splib07_export_audit.md` ｜ 差异声明：`docs/MCF_vs_rf07_diff.md`
- 77 规则映射：`docs/rf77_splib07_mapping.md` + `rf77_splib07_overlay_p1-4.png`
- 77×2151 1nm 参考谱：`docs/rf77_splib07_1nm.npz`（grid/rule/label/spectra；label 三类：实物记录 / `[AMX]` / `[alias]` / `synth`）
- 独立佐证：`docs/library_validation_report.txt`（AMX17 仅 NIC4 变体 0.9999 命中 27 号规则）
- 关键图件：`docs/amx17_nic4b_record.png`、`illite_gds4_compare.png`、`pyro25kaol75_amx17_check.png`
- splib07 Record 号备查：AMX17_NIC4b=13116、PYS1A_NIC4aaa=9130、CM9_NIC4bbb=6005

## 7. 恢复上下文步骤（新电脑）

1. 仓库整体拷贝到 `d:\CRAMM`（含 `D:\usgs_splib07` 库或重下）；git 用 PortableGit 全路径
2. `git log --oneline -5` 确认 HEAD ≥ `52d1a4d`（v1.2.6）
3. 读本文件 → CHANGELOG.md（更正史）→ `docs/MCF_vs_rf07_diff.md`（轨道差异声明）
4. 续作任何 v07 变更时严格按第 5 节修复链；提交永远只到本地
