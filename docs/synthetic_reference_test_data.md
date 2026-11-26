# CRAMM 参考谱衍生合成测试数据 · v1

> 日期：2026-11-18  
> 生成器：`docs/synthesize_reference_test_data.py`  
> 数据目录：`output/synthetic_reference_v1/`（由 `.gitignore` 排除，不进入软件包）  
> **证据边界：使用 CRAMM 自带参考谱生成，只适用于开发、自检和配对消融，不是独立测试集，不能据此宣称无偏算法精度。**

## 1. 数据源与传感器

- 唯一输入：`cramm/data/rf77_splib07_1nm.npz`。
- 输入 SHA-256：`22376845fac68481e8abba0a39f3b7deb1fdde094c85f87958edd3de9b831f01`。
- 77 条 rule-face 参考曲线，原始 0.35–2.50 µm、1 nm 网格；不修改原 NPZ。
- 采用与离线测试一致的 EMIT-like 配置：285 个波段，0.381–2.508 µm，FWHM = 0.0074 µm。
- 固定排除零基波段区间 `[126,150)` 和 `[190,210)`，基础有效波段 241 个。
- 高斯重采样使用与 CRAMM 相同的 FWHM 截断窗口；仅在参考谱原生有效覆盖内计算，**不向外推 NaN**。

## 2. 合成设计

### A. 单参考谱腿

77 条参考曲线均纳入，包括实物、AMX、alias 和既有合成混合规则行。这里的 `single_reference` 表示“一条参考规则曲线”，不表示地质上的纯矿物。

每条曲线生成：

- 1 条无连续统扰动、无噪声基线；
- 连续统斜率 `−0.10 / 0 / +0.10 µm⁻¹`；
- SNR = `40 / 25 / 15 dB`；
- 每个组合 2 个独立噪声实现。

合计 **1,463 条**。

### B. 二元面积混合腿

- 从实物、单族矿物参考中确定 36 个端元；不使用已有 synth/AMX/alias 行再次充当新混合端元。
- 按固定索引步长 1 和 7 生成 72 个唯一端元对。
- 每个端元对生成比例 `0.25/0.75`、`0.50/0.50`、`0.75/0.25`。
- 每个比例包含 1 条清洁基线及上述 3 种连续统 × 3 种 SNR 的 9 条扰动光谱。

合计 **2,160 条**。

### 总数

| 类别 | 清洁 | 40 dB | 25 dB | 15 dB | 合计 |
|---|---:|---:|---:|---:|---:|
| 单参考谱 | 77 | 462 | 462 | 462 | 1,463 |
| 二元面积混合 | 216 | 648 | 648 | 648 | 2,160 |
| **总计** | **293** | **1,110** | **1,110** | **1,110** | **3,623** |

连续统采用 `1 + slope × (wavelength_um − 1.4)` 乘法扰动。噪声按各条清洁光谱有效波段的 RMS 和目标 SNR 确定高斯噪声标准差。低于 `1e-6` 的值被截断，截断数逐条记录，未隐瞒该处理。

## 3. 输出结构

### `spectra.npz`

主要数组：

- `reflectance`：加扰动后的输入光谱，`(3623,285)`；
- `noise_free_reflectance`：同条件无噪声光谱；
- `valid_mask`：逐谱有效波段布尔掩膜；
- `band_centers_um`、`fwhm_um`、`base_valid_mask`；
- `reference_row_1/2`、`fraction_1/2`；
- `continuum_slope_per_um`、`snr_db_target`、`replicate`；
- `noise_seed`、`noise_sigma`；
- `reference_rules`、`reference_sensor_spectra`。

无效波段统一写为 NaN，不填零、不外推。

### `truth.csv`

逐条保存样本 ID、来源规则和原始 label、族集合、端元行号、混合比例、优势端元、连续统、目标与实测 SNR、随机种子、噪声标准差、截断数、有效波段数和原生覆盖范围。

`50/50` 混合的 `dominant_rule` 留空，不强行指定单一真值。

### `manifest.json`

记录输入哈希、生成参数、样本计数、审计结果和输出文件哈希。

## 4. 质量检查结果

- 3,623 条光谱全部具有至少 101 个有效波段；中位数 114，最大 240。
- 所有有效观测均为有限正值；无效位置均为 NaN。
- 清洁单参考谱可精确重建对应重采样参考曲线。
- 清洁二元混合可按记录比例精确重建。
- 所有噪声实现按保存的种子和标准差重放，逐位一致。
- 独立二次运行后，NPZ 内全部数组、truth CSV 及 NPZ 文件本身均逐字节一致。
- 与 CRAMM 引擎重采样结果的有效掩膜完全一致；16,277 个有效参考波段中仅 4 个值存在 `1.11e-16` 量级差异。
- 5 条代表性清洁/含噪、单参考/混合光谱已通过 `MicaEngine.classify_spectrum` 接口检查。该检查只验证数据接口，不是精度评分。
- 123 条光谱发生低值截断，共 2,491 个波段值；相关样本和数量已在 truth CSV 中标记。

文件：

- `spectra.npz`：5,339,503 bytes；SHA-256 `b1342123be1fa6ff58d29fc327f37d7f8f68d669a09dfeb9b97e3cca749ccf52`。
- `truth.csv`：1,016,654 bytes；SHA-256 `b1bf5008d051fee085a8615040b4a7c76d92a5f46b05bfa1402a2d8e47e39483`。

## 5. 复现与读取

```bash
/home/lee/miniconda3/bin/python -I docs/synthesize_reference_test_data.py \
  --output output/synthetic_reference_v1
```

生成器要求输出目录为空，避免无意覆盖已有数据。

```python
import numpy as np

z = np.load("output/synthetic_reference_v1/spectra.npz", allow_pickle=False)
i = 0
chanels = np.flatnonzero(z["valid_mask"][i])
wl = z["band_centers_um"][chanels]
spectrum = z["reflectance"][i, chanels].reshape(1, -1)
# classify_spectrum(spectrum, wl, z["band_centers_um"],
#                   z["fwhm_um"], chanels, top_n=10)
```

## 6. 下一步

真实 EMIT 波段数据与四配置配对测试已完成，见 `docs/synthetic_emit_ablation.md`。生成器新增 `--emit-nc` 参数，可直接读取 EMIT granule 的实际波长、FWHM 和 `good_wavelengths`。

后续评价必须使用同一批样本和随机种子，并同时报告识别结果、覆盖率及中心恢复误差。由于端元来自 CRAMM 自身参考库，后续仍需要独立标本模板或参数化前向模型作为外部验证。

## 7. 低频扰动与定向混合扩展

生成器现支持：

- `--perturbation white`：原有独立波段高斯噪声；
- `--perturbation low-frequency`：先对全波段随机序列进行 6 波段 sigma 的高斯平滑，再在有效波段上去均值并归一化到目标 RMS；
- `--mix-design white-mica-confuser`：仅生成 6 条白云母/伊利石与 7 条碳酸盐、绿泥石、绿帘石规则的 42 个定向端元对；
- `--mix-design combined`：保留原 72 对并加入 42 个定向对，共 114 对。
- `--mix-design white-mica-clay`：仅生成 42 个白云母/伊利石—高岭石/蒙脱石对；
- `--mix-design extended`：通用对、高比值干扰对和低比值粘土对全部纳入，共 153 对，并逐条保存 `targeted_group`。

```bash
/home/lee/miniconda3/bin/python -I docs/synthesize_reference_test_data.py \
  --emit-nc EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc \
  --perturbation low-frequency --mix-design combined \
  --output output/synthetic_emit_lowfreq_v1
```

新数据包含 4,883 条光谱，其中 1,260 条定向混合。结果与分层审计见 `docs/low_frequency_synthetic_audit.md`。旧白噪声数据保持不变。

使用新种子 20261119 的 `extended` 批次包含 6,053 条光谱，高比值干扰组与低比值粘土组各 1,260 条。完整语义复核见 `docs/algorithm_semantic_reassessment.md` 第 8 节。
