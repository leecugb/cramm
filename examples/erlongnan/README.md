# 二龙南 EMIT–ASD 实测案例（整理中）

本目录组织一个**真实场景应用案例**，不是合成精度测试，也不是逐像元分类 benchmark。案例正文见 [二龙南实测案例说明](../../docs/case_studies/erlongnan.md)。

## 文件

| 文件 | 用途 |
|---|---|
| `asd30_index.csv` | 30 条入选 ASD 光谱与原始 100 条 ENVI 光谱库的逐行对应 |
| `build_asd30_index.py` | 从原始数据重新生成溯源表，检查唯一匹配、波长网格、文本光谱内容并记录原始文件 SHA-256 |
| `join_asd30_assay.py` | 直接读取原始化验 XLSX，按样品编号连接 30 条 ASD 光谱，不加载 pickle |
| `classify_asd30_emit.py` | 将 30 条实测 ASD 重采样到真实 EMIT 波段契约并执行当前 CRAMM Top-N |
| `run_emit_case.py` | 用当前 CRAMM 工作树处理整景 EMIT，并记录输入、代码、资源和输出 SHA-256 |

索引中的 `analysis_index_0based` 和 `library_index_0based` 均为 **从 0 开始**的数组行号。`asd30_index.csv` 只记录光谱来源，不包含未经核实的坐标、Au 单位或显微鉴定结果。

## 数据边界

原始 EMIT NetCDF、ASD 数据库和论文图件不随本目录分发。运行时需要自行提供：

- EMIT L2A 原始场景；
- 含 `beishan`、`beishan.hdr` 和原始 `.asd`／`.asd.txt` 的 ASD 目录；
- 30 × 2151 的 `spectra_reflectance.npy`；
- 2151 波段的 `band_wavelength.npy`，单位为 µm。

## 重建 30 条 ASD 溯源表

```bash
python examples/erlongnan/build_asd30_index.py \
  --asd-dir /path/to/20250411北山样品（ASD） \
  --reflectance /path/to/spectra_reflectance.npy \
  --wavelength /path/to/band_wavelength.npy \
  --output examples/erlongnan/asd30_index.csv \
  --summary output/erlongnan_real_case_v1/asd30_traceability.json
```

脚本要求每条入选光谱在原始库中只有一个容差内匹配，容差为 1e-12。当前实数据重建结果为 30 个唯一样品，最大绝对差值为 5.551e-16，30 份二进制 ASD 和 30 份文本光谱全部存在。文本波长网格差异为 0，文本反射率与原始库的最大绝对差值为 5.551e-16；每份原始文件的 SHA-256 均写入索引。

## 连接原始化验表

```bash
python examples/erlongnan/join_asd30_assay.py \
  --index examples/erlongnan/asd30_index.csv \
  --assay-xlsx /path/to/内蒙古北山月牙山基本分析报.xlsx \
  --derived-csv /path/to/alteration_type_classification.csv \
  --output output/erlongnan_real_case_v1/asd30_assay_join.csv \
  --summary output/erlongnan_real_case_v1/asd30_assay_join.json
```

当前 30 件样品全部连接成功，派生表 Au 列与原始化验值的逐行最大绝对差值为 0。原始化验表未在列头注明单位，因此输出使用 `Au_source_value` 和 `source_unit_status`，不推断单位。化验数值暂存于本地 `output/`，公开前需确认共享授权。

## 运行 30 条实测 ASD 的 CRAMM 分类

```bash
python examples/erlongnan/classify_asd30_emit.py \
  --index examples/erlongnan/asd30_index.csv \
  --reflectance /path/to/spectra_reflectance.npy \
  --wavelength /path/to/band_wavelength.npy \
  --emit-nc /path/to/EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc \
  --derived-csv /path/to/alteration_type_classification.csv \
  --output output/erlongnan_real_case_v1/my_asd30_classification \
  --top-n 5
```

该脚本复用 CRAMM 生产 `_resample_`，并使用 EMIT 的 `good_wavelengths`。当前实数据运行的通道索引、中心波长和 FWHM 已与 `EmitReader.load` 的整景结果逐项验证一致。30 条均有输出，但 Top-1 分布与派生蚀变类型存在明显差异，不能将“有输出”写成“验证通过”。派生类型只用于交叉表，不是独立显微真值。

## 运行当前版本整景案例

```bash
python examples/erlongnan/run_emit_case.py \
  --input /path/to/EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc \
  --output output/erlongnan_real_case_v1/my_current_run \
  --name erlongnan_current \
  --workers 4
```

输出目录必须为空或不存在，以防覆盖历史产品。输出包括五个 GeoTIFF、一个原始浮点 NPZ 和 `case_run_manifest.json`。清单记录：

- 输入文件大小和 SHA-256；
- CRAMM 分发版本、Python 和 NumPy 版本；
- 分类器、EMIT 读取器、渲染器、引擎入口及运行脚本本身 SHA-256；
- 当前 `rf.json`、1 nm 参考谱包和颜色表 SHA-256；
- 场景形状、有效波段和波长范围；
- 每个输出的大小和 SHA-256。

若 GDAL 检查时报 `PROJ: ... Open of .../share/proj failed`，先显式指定本机实际 PROJ 数据目录，例如：

```bash
export PROJ_DATA=/path/to/share/proj
```

当前产品已在显式 `PROJ_DATA` 下验证为 WGS 84 / UTM zone 47N（EPSG:32647），但这不替代岩石样品坐标与像元配准。

## 尚不能据此声称的内容

- 不能把岩相级地质一致性换算为逐像元分类准确率；
- 不能把 30 件岩石样品直接当作 60 m EMIT 像元的纯矿物真值；
- 不能将 Au 尾箱包络或 ASD 相关性解释为定量品位预测模型；
- 不能把 CHAI、GEMS 或 USGS 标定归入 CRAMM 核心分类步骤；
- 不能把当前版本复现输出与早期论文产品混为同一批结果。

公开案例前仍需补齐“样品—坐标—Au 及单位—显微鉴定—EMIT 像元”逐样对照表。
