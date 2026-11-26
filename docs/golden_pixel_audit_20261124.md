# CRAMM 黄金场景逐像素审计（2026-11-24）

## 目标与边界

本审计追踪 `tests/golden_arrays.npz` 与当前工作树之间的全部场景差异，分离：

1. 三条高岭石—白云母混合规则的阈值 0.4→0.55；
2. lowFe 窗口下边界 2.245→2.244 µm；
3. 仲裁重拟合中心越出目标窗时回退到翻转前中心；
4. C2 之后的其他代码变化。

本审计证明可执行来源、差异范围和重复性，不提供独立地质精度验收。脚本不会自动覆盖黄金文件。

## 基线链

- 黄金文件 SHA-256：`4a7a7b7f4a9ba9f3bff58c3eab4594b59596682bce3d0f8847ef53cce9113d7c`；
- 黄金文件最后生成提交：`79dcf88`；
- C2：`051fbd55c0857c519e9ec8a584aac984611aa44c`；
- 当前 HEAD：`1a0ac27a25012388f18e27fddefdeb3145fe3cea`，另有未提交修改。

独立 C2 worktree 的全景运行与黄金五数组 **逐像素完全一致**。因此，当前失败只来自 C2 之后的工作树变更，不涉及更早的发布期代码。

## 变体设计

| 变体 | 用途 |
|---|---|
| `release_051fbd` | 验证 C2 是否复现黄金 |
| `current_all` | 当前完整配置，4 workers |
| `current_threshold04` | 仅将三条混合规则阈值回退到 0.4 |
| `current_lowfe2245` | 仅将 lowFe 下边界回退到 2.245 µm |
| `current_legacy_fallback` | 仅在重拟合非有限时回退，不因越出目标窗回退 |
| `current_reverted_all` | 三项联合回退，检验是否恢复 C2 |
| `current_all_serial` | 当前完整配置，1 worker，检验串并行一致性 |

回退使用独立 worktree、内存规则修改或临时源码 overlay，不修改生产代码和黄金文件。

## 指标与验收门槛

- `changed_pixels`：至少一个 RGB 通道不同的去重像元数；
- `changed_elements`：所有通道中不同的数组元素数；
- 标签转移：按规则名称统计，不把数组索引当作矿物名；
- 中心差异：拆分覆盖增减与共同正值区的数值变化；
- 交互项：联合差异原则上应等于单因素差异并集；存在依赖时必须逐像素给出机制解释，不能忽略；
- 联合回退：RGB、标签和数值数组必须恢复 C2；
- 串并行：当前全部输出必须一致；
- 既有 rebaseline 门槛：平均通道漂移 <5/255，drastic class flips <31,800。

只有全部门槛通过，才允许进入单独的人工 rebaseline 决策。审计脚本不执行写入黄金基线。

## 结果

### 1. 当前配置相对 C2 的总差异

| 数组 | changed pixels | changed elements | 平均通道漂移 | drastic class flips |
|---|---:|---:|---:|---:|
| orth_rgb | 28,186 | 84,305 | 2.582 | 71 |
| color_enhanced | 31,495 | 91,279 | 2.197 | 72 |
| mus_image | 2,309 | 5,476 | 0.114 | 679 |
| chl_image | 36 | 73 | 0.00059 | 0 |
| cal_image | 0 | 0 | 0 | 0 |

旧日志中的 84,305、91,279、5,476 和 73 均为**数组元素数**，不是去重像元数。当前标签共改变 28,226 个，其中 40 个标签变化映射到相同 RGB，因此 orth_rgb 的像元变化为 28,186。

### 2. 单因素归因

| 因素 | 标签变化 | RGB 影响 | 中心影响 |
|---|---:|---|---|
| 阈值 0.4→0.55 | 28,215 | orth 28,175；color 31,484；mus 2,275；chl/cal 0 | 新增 894 个白云母中心正值；共同正值区 27,321 个值变化 |
| lowFe 2.245→2.244 | 11，全部 clinochlore→lowFe | orth 11；color 11；mus/chl/cal 0 | 11 个绿泥石中心值变化，最大 0.000359 µm |
| 越窗重拟合回退 | 0 | mus 34；chl 38；orth/color/cal 0 | 白云母 55 个、绿泥石 189 个中心值变化，无覆盖增减 |

阈值相关标签转移共 23 种，除纯白云母到混合规则外，还包括碳酸盐—蒙脱石、绿泥石—白云母等规则向高岭石—白云母混合规则的接管，以及混合规则之间的双向转移。这些是阈值引发的下游赢家变化，不能自动解释为地质精度提高。

### 3. 交互项

orth、color、mus 和 cal 的联合差异均等于单因素差异并集。chl_image 的单因素回退影响 38 个像元，而联合差异为 36 个，差异恰好是 `(257,61)` 和 `(760,241)`：

- C2 和联合回退均为 clinochlore；
- 当前为 lowFe；
- 当前回退恢复 C2 的中心与 RGB；
- 旧重拟合产生低于 2.244 µm 的中心，chl_image 为黑色。

这两个像元与既有 lowFe 后验审计完全一致。38 与 36 的差别是 lowFe 窗口和回退规则的可解释依赖，不存在未归因像元。

### 4. 验收结果

以下检查全部通过：

1. C2 与黄金五数组逐像素一致；
2. 三项联合回退恢复 C2 的 RGB、规则标签、fit、fd 和三类中心；
3. 当前 1-worker 与 4-worker 的 RGB、标签和数值数组完全一致；
4. 所有交互像元均有逐点机制解释；
5. 平均通道漂移和 drastic class flips 均满足既有 rebaseline 门槛；
6. 黄金文件 SHA-256 在审计前后保持不变。

`audit_summary.json` 的结论为 `audit_pass = true`，即：**可进入单独、明确的人工 rebaseline 决策**。

### 5. 候选文件与基线重建

已生成仅供审查的 `candidate_golden_arrays.npz`，其 SHA-256 为：

`70a0ce893d017b9b7950acde58e6ae741b5310241043b068e6cc74927685341f`

串行和并行候选文件逐字节一致。2026-11-24 经明确指示，已使用候选文件原子替换 `tests/golden_arrays.npz`；旧基线备份为 `output/golden_pixel_audit_20261124/golden_before_rebaseline.npz`，替换记录见 `rebaseline_manifest.json`。重建后 `tests/test_parallel.py 1` 与 `tests/test_parallel.py 4` 均为 **PASS**，五数组全部 bit-identical；完整离线测试为 **40 passed, 2 warnings**。未提交或发布。

主要证据：

- `audit_summary.json`：门槛和完整比较结果；
- `release_current_rgb_delta.npz`：五数组逐像元差异；
- `label_transitions.csv`：全部标签变化及前后 fit/fd；
- `fallback_center_changes.csv`：回退引起的中心变化；
- `chl_interaction_two_pixels.json`：两个交互像元的五配置对照；
- `candidate_manifest.json`：候选哈希与串并行一致性。

