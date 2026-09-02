# CRAMM Project Context — 1nm-only 快照

> 生成时间：2026-09-02（legacy / rf07 轨道删除,仅保留 1nm rule-face 轨道）
> 作用：换电脑 / 长时间停滞后,按本文"迁移 checklist"即可复现开发环境与 BIT-EXACT 验收矩阵。
> 本文件是纯参考,不参与任何代码路径。

---

## 一、迁移 checklist(最小可工作副本)

> 复制下面 **4 个外部资源** + **整个仓库源码** 到新电脑相同盘(推荐仍放在 `D:\CRAMM`,避免脚本中硬编码默认路径需要手改)。

| # | 原位置 | 复制到新电脑的相同路径 | 说明 |
|---|---|---|---|
| 1 | `D:\CRAMM\EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc` | 同 | **EMIT 黄金回归输入**;所有 BIT-EXACT 验证都用同一 cube 的 crop 500:600, 300:400 |
| 2 | `cramm/data/rf77_splib07_1nm.npz` | `cramm/data/` 下 | 1nm rule-face 参考谱束(77 rule × 2151 band @ 1nm);唯一参考源 |
| 3 | `cramm/data/temp_rf_notfeatures_renamed.json` | `cramm/data/` 下 | **唯一**规则库(not_(abs/rel)_feature reflectance_record = 规则名字符串;reference.reflectance_record 仍保留 int,from_paths 经 alias 自动转译) |
| 4 | `D:\CRAMM\_mica_v07_result.npz` | 仓库根 | **1nm 轨道黄金基线**(notebook + 原独立脚本执行产物,作为 CLI 包装层验收基准) |

**Python 环境(新电脑安装要求)**:
- 解释器:`C:\ProgramData\anaconda3\python.exe`(或任意含 numpy / pandas / netCDF4 / h5netcdf 的 conda env;threadpoolctl 可选,有则 BLAS 线程限制更精确)。
- 严格要求 `numpy`(闭包最小二乘 + r2 链依赖其 IEEE 浮点行为;保持 ≥ 1.24 即可,对 MKL/OpenBLAS 后端无感——因其拟合核已改用 `np.einsum` 规避 BLAS 行相关 ulp 差)。

---

## 二、本次改造的代码文件与要点

### 2.1 核心文件变更清单

| 文件 | 行数变化 | 主要改动 |
|---|---|---|
| [`cramm/classifier.py`](file:///D:/CRAMM/cramm/classifier.py) | ~1400→~2100 | **1nm-only 核心**:新增 `_read_1nm_npz`、`__init__(reference_1nm_bundle, output_name_aliases)`(hardcoded `track="1nm"`)、`from_paths(rf_path, splib_path)` 1nm 加载(含 1nm strict not_feature 字符串校验)、`get_resample` 1nm 路径 + mixture 1nm lookup + 双别名零拷贝、`_judge_reference_entry` 与 `_get_compiled_rules` 主参考**统一改走 `rf["output_name"]`**(双别名键兜底)。 |
| [`cramm/mica_engine.py`](file:///D:/CRAMM/cramm/mica_engine.py#L83-L115) | 加 30 行左右 | `MicaEngine.__init__` 保留仅关键字参数 `reference_track=None`(API 兼容,实际被忽略),内部以 `MicaClassifier.from_paths(...)` 透明转发。 |
| [`mica_core_v07_1nm.py`](file:///D:/CRAMM/mica_core_v07_1nm.py) | 1474 → 173 | **彻底瘦身**为 CLI 包装层:argparse + `EmitReader.load` + `MicaClassifier.from_paths()` + `classify(n_workers=2)` + 输出原字段 npz,默认 crop `500:600,300:400`、默认 workers=2(与 notebook 黄金 nw=2 对齐)。 |
| 临时脚本 `_smoke_classifier.py` / `_probe_*` / `_debug_*` / `_reproduce_*` / `_quick_alias_check.py` / `_error_and_sanity.py` / `_1nm_full_check.py` + 对应 `.out` / `_serial_check.npz` / `_core_check.npz` | 全部已删除 | 仅用于本次改造的探针脚本与一次性验证产物,**不随仓库迁移**。早期 `_inspect_*` / `_plot_*` / `_md2pdf` / `_api_push` 等历史脚本保留原样。 |
| 删除文件 | — | `cramm/data/rf.json` / `cramm/data/rf_splib07.json` / `cramm/data/splib06b` / `cramm/data/rf07_spectra.npz` 等legacy/rf07 数据,以及 `tests/test_rf07_export.py` / `tests/test_rf07_engine.py`。 |

### 2.2 1nm 架构(迁移后务必保持此心智模型)

```
                    ┌──────────────────────────────────────────┐
                    │         _judge_reference_entry           │
                    │   (查找: resampled1[rf["output_name"]])  │
                    └──────────────┬───────────────────────────┘
                                   │  resampled1[key]
          ┌────────────────────────┼────────────────────────┐
          │ 双别名键: int 与 rule-name 指向同一 ndarray       │
          │ (零拷贝, pickle shared-ref dedup 不膨胀)         │
          └────────────────────────┼────────────────────────┘
                                   │
                       ┌───────────┴────────────┐
                       │ 1nm rule-face         │
                       │ 主键: rule-name str   │
                       │ alias: int owner      │
                       │       + 19 mixt-back  │
                       └───────────────────────┘
```

- **主参考统一键**:`_judge_reference_entry` 和 `_get_compiled_rules` 都查 `resampled1[rf["output_name"]]`。分叉已彻底消除,数值路径 BIT-EXACT 统一。
- **compiled 缓存 / 重采样缓存**:键不再含 track,因实例只承载 1nm(`_resample_cache_key = (w bytes, bp bytes)`;`_compiled_key = (resample_cache_key, wl, chanels)`)。
- **1nm 轨道严格类型**:`from_paths` 会 strict 校验 not_(abs/rel)_feature reflectance_record 必须为 rule-name 字符串,否则抛 `ValueError` 列出前 8 条违规样例。reference.reflectance_record 仍允许 int,经 `own_rec_to_rule` → `extra_aliases` → get_resample 装 int→rule 别名自动解决。
- **1nm 轨道 orphan rec(10466 / 10477 → mix_7785 / mix_7807)**:它们非任何 rf 规则主参考,配方合成时查不到 owning-rule → fallback 为零向量加权;因下游从未用 `mix_7785` 作为 direct lookup 目标(主参考改走 `output_name`= 规则名本身),所以数值完全无影响,不必伪造谱到 1nm bundle。

---

## 三、BIT-EXACT 验证矩阵(迁移后快速验收 3 条命令)

> 以下命令**全部 PASS** = 迁移成功、数值未漂移。
> 所有命令在仓库根 `D:\CRAMM` 下执行,解释器:`C:\ProgramData\anaconda3\python.exe`。

| # | 命令 | 验证目标 | 预期 |
|---|---|---|---|
| (1) | `python mica_core_v07_1nm.py` (默认 nw=2 crop=500:600,300:400 输出 `_core_check.npz`)<br>然后: `python -c "...load golden vs _core_check ... np.testing.assert_array_equal * 9 字段"` (见下方附) | 1nm 瘦身后 CLI 包装层 vs notebook 黄金基线 `_mica_v07_result.npz` (9 字段: fit/depth/num/mus_center/chl_center/cal_center/index/r/c) | 全部 **BIT-EXACT PASS**;index 顺序完全一致 |
| (2) 可选 工程深度:compiled vs direct 差分 | 写一个 1nm 小脚本,对 crop 100×100 中的任一 302 像素 × 77 规则,分别走 `_judge_reference_entry(..., compiled=None)`(direct)与 `_judge_reference_entry(..., compiled=compiled[key])`,NaN-aware strict compare `np.testing.assert_array_equal` after `nan_to_num(x,nan=999)` | 77×302 **BIT-EXACT PASS** |
| (3) 可选 Top-1 一致性:`classify_spectrum` 像素级 Top-1 vs `classify` | 随机挑 120 像素逐个 `classify_spectrum(..., top_n=1)[0]["fit"]` vs 同一 cube 分类后 `fit[i]` | 匹配率 100%,fit 差 `0.000e+00` |

**(1) 的完整比对脚本(可复制粘贴)**:
```python
import sys, numpy as np
gold = np.load(r"D:\CRAMM\_mica_v07_result.npz", allow_pickle=True)
new  = np.load(r"D:\CRAMM\_core_check.npz",        allow_pickle=True)
assert sorted(gold.files) == sorted(new.files)
ok = True
for k in sorted(gold.files):
    g, n = gold[k], new[k]
    if k == "index":
        if list(g.tolist()) != list(n.tolist()):
            ok=False; print(f"index MISMATCH")
        else:
            print(f"index ORDER MATCH (len={len(g)})")
        continue
    try:
        np.testing.assert_array_equal(g, n, err_msg=k)
        print(f"  {k:<12s} BIT-EXACT PASS")
    except AssertionError:
        ok=False
        print(f"  {k:<12s} FAIL  max|Δ|={np.abs(np.nan_to_num(np.asarray(g,np.float64),nan=999)-np.nan_to_num(np.asarray(n,np.float64),nan=999)).max():.3e}")
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
```

---

## 四、常见坑(迁移后第一处排查)

1. **1nm 轨道报 ValueError(Found N int record references)**:你传了原版 `rf.json` 而非 `temp_rf_notfeatures_renamed.json`。not_feature 的 reflectance_record 在 1nm 轨道必须是规则名字符串。
2. **get_resample KeyError: 'dry_veg_grass_2_3um' / 'pyrophyllite.25+kaolinite.75'**:alias 没挂好。确认 `from_paths` 中:
   - 混合物合成后要 walk `rf`,把 `rf[rname]["ref"] == mix_id` 的 19 条 mixture-backed 规则也挂上 `resampled1[rname] = result`(共享引用)。
   - `extra_aliases[int_rec] = owner_rule-name` 必须在 from_paths 阶段建立。
3. **1nm compiled vs direct 有 diff(尤其是 NaN 位置不匹配)**:检查 `_get_compiled_rules` 主参考是否用 `resampled1[rf["output_name"]][chanels]` 而非 `rf["reference"]["reflectance_record"]`。两者在 1nm 下指向不同对象(前者是 1nm bundle 真实谱;后者若 ref 是 int 10466 会解析到 orphan mix 合成的零向量)。
4. **Windows 并行(nw≥2)卡死或报脚本未受签名 / PSSecurityException**:
   - 主入口脚本必须 `if __name__ == "__main__":` 守卫(spawn 会重新 import `__main__`)。
   - 本工程所有脚本都用 `.py` 由 python.exe 直接执行,不用 `.ps1` 的 `npm.ps1` / conda 脚本绕过策略。
5. **临时 `mica_spec_*.npy` 泄漏到 `%TEMP%`**:一般不会——finally 里关 pool + 15×0.2s 重试删除 + atexit 兜底三重保证;若仍有残留(比如进程被外部 kill),可直接手动删 `%TEMP%\mica_spec_*.npy`。
6. **BLAS 线程过订阅 / parallel vs serial 出现 ulp 级 fit diff**:已通过「einsum 替换 dgemm」+「spawn+5 环境变量锁 BLAS=1 线程」从机制上避免;若新电脑 MKL 版本特别新仍有 diff,跑一次 (2) 能定位。

---

## 五、快速使用 API(3 行)

迁移验证通过后,开发期调用 1nm 轨道的最小代码:

```python
from cramm.classifier import MicaClassifier
from cramm.emit_reader import EmitReader

cls = MicaClassifier.from_paths(
    rf_path="cramm/data/temp_rf_notfeatures_renamed.json",
    splib_path="cramm/data/rf77_splib07_1nm.npz",
)
spectrum, _lon, _lat, w, bp, wl, chanels = EmitReader.load(
    r"D:\CRAMM\EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
)
z = cls.classify(spectrum[500:600, 300:400], wl, w, bp, chanels, n_workers=2)
# z.fit, z.depth, z.num, z.mus_center, z.chl_center, z.cal_center, z.index
```

引擎仅运行 1 nm 轨道,`reference_track` 参数保留仅为 API 兼容,显式传非 `None`/`"1nm"` 值会抛 `ValueError`:

```python
from cramm.mica_engine import MicaEngine
eng = MicaEngine()                     # 默认即 1 nm 轨道
eng = MicaEngine(reference_track="1nm") # 显式(等价)
```

---

## 六、当前工程状态一览(最后一次验证快照)

| 项目 | 状态 |
|---|---|
| 1nm nw=2 CLI 包装层 vs notebook 黄金 | ✅ 9 字段全 BIT-EXACT |
| 1nm compiled vs direct (77 rule × 302 px) | ✅ NaN-aware BIT-EXACT |
| classify_spectrum Top-1 vs classify 120 px | ✅ 100% fit Δ=0 |
| 1nm strict ValueError 自测(原版 rf.json → 报错) | ✅ 抛 80 条违规 + 前 8 样例 |
| alias 双向 zero-copy + pickle 体积 | ✅ 1nm=225KB |
| mica_engine.py facade `reference_track=` 兼容 | ✅ 参数保留但实际被忽略 |
| 临时脚本 / 日志清理 | ✅ 11 py + 10 out + 2 npz 全部删除 |
| `mica_core_v07_1nm.py` 瘦身 | ✅ 1474 → 173 行 CLI 包装层 |
