# Stage 2 of splib07 migration: bake the 53 selected splib07 records onto the
# 1 nm master grid (350-2500 nm) and export cramm/data/rf07_spectra.npz.
#
# Format (D2 addendum):
#   grid    (2151,) float64   master wavelength grid, um
#   keys    (53,)   str       "<name>_<sensor><quality>_<mtype>" (rf_splib07.json refs)
#   spectra (53, 2151) float64 piecewise-linear bake; NaN outside the record's
#                             valid sample range; interior deletion gaps bridged
#   meta    ()      str       JSON list of per-record provenance
#
# Mixtures are NOT baked: rf.json synthesizes them AFTER resampling the
# endmembers to the sensor grid (get_resample); the v07 engine branch keeps
# the exact same order, so only physical records live in the npz.
#
# Audit (docs/splib07_export_audit.md): for every record, native-vs-baked
# resampled onto the real EMIT grid via the engine kernel -- max abs diff,
# Pearson r, holes filled by construction, new holes (must be 0).
import json
import os
import sys

import netCDF4 as nc
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from cramm.classifier import _resample_
from usgs_splib import USGSLibrary

SEL = json.load(open(r"d:\CRAMM\docs\splib07_selection.json", encoding="utf-8"))
GRID_LO, GRID_HI, GRID_STEP = (SEL["master_grid"]["lo_um"],
                               SEL["master_grid"]["hi_um"],
                               SEL["master_grid"]["step_um"])
GRID = np.arange(GRID_LO, GRID_HI + GRID_STEP / 2, GRID_STEP)
assert len(GRID) == 2151

EMIT_NC = r"d:\CRAMM\EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
with nc.Dataset(EMIT_NC) as _ds:
    EMIT_W = _ds["sensor_band_parameters"]["wavelengths"][:].data / 1000.0
    EMIT_BP = _ds["sensor_band_parameters"]["fwhm"][:].data / 1000.0

lib = USGSLibrary(r"D:\usgs_splib07")
by_key = {}
for r in lib.records:
    by_key[f"{r.name}_{r.sensor}{r.quality}_{r.mtype}"] = r


def valid_samples(spec):
    wl = np.asarray(spec.wavelength, dtype="float64")
    sp = np.asarray(spec.reflectance, dtype="float64")
    o = np.argsort(wl)
    wl, sp = wl[o], sp[o]
    k = (wl > 0) & (sp > 0) & (sp < 1e34)
    return wl[k], sp[k]


def bake(wl, sp):
    out = np.full(len(GRID), np.nan)
    m = (GRID >= wl[0]) & (GRID <= wl[-1])
    out[m] = np.interp(GRID[m], wl, sp)
    return out


def resample_native(wl, sp):
    """native samples through the engine kernel (invalid already dropped)"""
    return _resample_(wl, sp, EMIT_W, EMIT_BP)


keys, spectra, meta = [], [], []
audit = []
for rec06, s in SEL["references"].items():
    key = s["splib07_record"]
    if key not in by_key:
        raise KeyError(f"splib07 record not found: {key}")
    spec = lib.load(by_key[key])
    wl, sp = valid_samples(spec)
    baked = bake(wl, sp)
    keys.append(key)
    spectra.append(baked)
    meta.append({
        "key": key,
        "splib07": {"name": s["splib07_name"], "sensor": s["sensor"],
                    "quality": s["quality"], "mtype": s["mtype"]},
        "splib06b_rec": int(rec06),
        "splib06b_title": s["splib06b_title"],
        "rules": s["rules"],
        "r_vs_06b": s["r_vs_06b"],
        "native_valid_samples": int(len(wl)),
        "native_range_um": [round(float(wl[0]), 4), round(float(wl[-1]), 4)],
        "baked_valid_points": int((~np.isnan(baked)).sum()),
    })
    # ---- audit on the EMIT grid (what the engine will actually see) ----
    rn = resample_native(wl, sp)
    rb = _resample_(GRID, baked, EMIT_W, EMIT_BP)
    both = ~np.isnan(rn) & ~np.isnan(rb)
    r = float(np.corrcoef(rn[both], rb[both])[0, 1]) if both.sum() > 10 else None
    maxd = float(np.abs(rn[both] - rb[both]).max()) if both.any() else None
    filled = int((np.isnan(rn) & ~np.isnan(rb)).sum())
    new_holes = int((~np.isnan(rn) & np.isnan(rb)).sum())
    audit.append((key, s["sensor"], r, maxd, filled, new_holes))

spectra = np.vstack(spectra)
out_npz = r"d:\CRAMM\cramm\data\rf07_spectra.npz"
np.savez(out_npz,
         grid=GRID,
         keys=np.array(keys),
         spectra=spectra,
         meta=np.array([json.dumps(meta, ensure_ascii=False)]))
print(f"wrote {out_npz}: {len(keys)} records x {len(GRID)} grid points, "
      f"{os.path.getsize(out_npz)/1024:.0f} KiB")

# ---- integrity check, two tiers ----
# (a) records whose native in-range samples are integer-nm aligned (ASD 1 nm
#     tables): baking must be an identity copy -- bit-exact at sample points.
# (b) non-aligned records (BECK 10 nm, NIC4 ~0.93 nm): reproduction error at
#     native kink points is interpolation error by construction, NOT an
#     integrity failure; report the worst as information.
worst_aligned = 0.0
worst_rep, worst_rep_key = 0.0, None
for rec06, s in SEL["references"].items():
    key = s["splib07_record"]
    wl, sp = valid_samples(lib.load(by_key[key]))
    m = (wl >= GRID[0]) & (wl <= GRID[-1])
    i = keys.index(key)
    back = np.interp(wl[m], GRID, spectra[i])
    d = float(np.abs(back - sp[m]).max()) if m.any() else 0.0
    aligned = bool((np.abs(wl[m] - np.round(wl[m] / 0.001) * 0.001) < 1e-6).all())
    if aligned:
        worst_aligned = max(worst_aligned, d)
        if d > 1e-12:
            print(f"  !! aligned record not bit-exact: {key} max|diff|={d:.3e}")
    elif d > worst_rep:
        worst_rep, worst_rep_key = d, key
print(f"aligned-grid identity max|diff|: {worst_aligned:.3e} (must be <=1e-12)")
print(f"non-aligned reproduction max|diff| at kink points: {worst_rep:.3e} ({worst_rep_key})")

# ---- audit report ----
L = []
L.append("# splib07 迁移 · 阶段2 导出审计")
L.append("")
L.append("> 日期：2026-08-29 ｜ 脚本：`docs/_splib07_stage2_export.py` ｜ 产物：`cramm/data/rf07_spectra.npz`")
L.append("> 审计口径：原生有效样本 vs 1 nm 主网格烘焙谱，分别经引擎 `_resample_` 重采样到真实 EMIT 网格后比较。")
L.append("> NIC4 ~0.93 nm→1 nm 轻微降采样的影响即体现在 max|Δ| 列；filled = 烘焙按构造填掉的 FWHM 空洞（遗产改善）；new holes 必须为 0。")
L.append("")
L.append("| 记录 | 传感器 | r | max\\|Δ\\| | 填洞数 | 新增空洞 |")
L.append("|---|---|---|---|---|---|")
bad = 0
for key, sensor, r, maxd, filled, holes in audit:
    flag = "" if holes == 0 else " **✗**"
    if holes:
        bad += 1
    L.append(f"| `{key}` | {sensor} | {r:.6f} | {maxd:.2e} | {filled} | {holes}{flag} |")
L.append("")
L.append("## 完整性核验")
L.append("")
L.append(f"- 整数 nm 对齐记录（ASD 1 nm 表；BECK 10 nm 采样点亦落在整数 nm）烘焙为恒等拷贝，回读 max|diff| = {worst_aligned:.3e}（要求 ≤1e-12）")
L.append(f"- 非对齐记录（NIC4 ~0.93 nm）采样点回读差为构造性插值误差，最大 {worst_rep:.3e}（`{worst_rep_key}`）——非完整性问题，其引擎侧影响见上表 max|Δ| 列")
L.append("")
L.append("## 对 D2 增补“上采样无损”论断的修正")
L.append("")
L.append("无损证明仅对线性插值型重采样成立。引擎 `_resample_` 是按 FWHM 窗内样本做高斯加权平均"
         "（权重按窗内样本归一），粗采样窗内仅 1–2 个样本时其加权均值 ≠ 稠密插值样本的加权均值"
         "（≈真卷积）。因此 BECK 10 nm→1 nm 烘焙**改变**高斯核重采样结果：EMIT 网格上 max|Δ| "
         "普遍 ≤2e-2，最大 1.03e-1（Topaz_HS184.3B，2.0–2.16 µm 陡沿，r=0.9962）。"
         "烘焙谱更接近真实仪器卷积，但与现行 06b 粗采样口径存在有界行为差——列入阶段 4 双跑仲裁。")
n_nic4 = [a for a in audit if a[1] == "NIC4"]
worst_nic4 = max(n_nic4, key=lambda a: a[3])
L.append("")
L.append(f"NIC4 降采样最大偏差：{worst_nic4[3]:.2e}（`{worst_nic4[0]}`，r={worst_nic4[2]:.6f}）")
with open(r"d:\CRAMM\docs\splib07_export_audit.md", "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print(f"new-hole violations: {bad}")
print(f"NIC4 worst max|diff|: {worst_nic4[3]:.3e} ({worst_nic4[0]})")
