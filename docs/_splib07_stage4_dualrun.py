# Stage 4 of splib07 migration: dual-track full-scene run + diff census.
#
#   legacy  MicaEngine()                          -> validate vs golden_arrays.npz
#   v07     MicaEngine(rf_path=rf_splib07.json)   -> tests/golden_arrays_v07.npz
#
# Also: v07 subscene serial-vs-parallel bit-exact check (golden discipline).
# Output: docs/splib07_dualrun_diff.md
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

NC = r"d:\CRAMM\EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
GOLD06 = r"d:\CRAMM\tests\golden_arrays.npz"
GOLD07 = r"d:\CRAMM\tests\golden_arrays_v07.npz"
LAYERS = ["orth_rgb", "color_enhanced", "mus_image", "chl_image", "cal_image"]
RAW = ["mus_center", "chl_center", "cal_center", "fd"]
NW = 4


def main():
    from cramm.mica_engine import MicaEngine

    t0 = time.time()
    eng06 = MicaEngine()
    spectrum, lon, lat, w, bp, wl, chanels = eng06.load_emit(NC)
    print(f"[load] {time.time()-t0:.1f}s spectrum={spectrum.shape}", flush=True)

    # ------------------------------------------------------------ legacy run
    t1 = time.time()
    out06 = eng06.spectrum_analysis(spectrum, wl, w, bp, chanels, n_workers=NW, raw=True)
    print(f"[legacy classify] {time.time()-t1:.1f}s", flush=True)
    g = np.load(GOLD06)
    for name, arr in zip(LAYERS, out06[:5]):
        same = np.array_equal(arr, g[name])
        print(f"  legacy vs golden {name:16s} array_equal={same}", flush=True)
        if not same:
            raise SystemExit(f"legacy track no longer bit-exact vs golden: {name}")

    # ------------------------------------------------------------ v07 run
    eng07 = MicaEngine(rf_path=os.path.join(os.path.dirname(HERE),
                                            "cramm", "data", "rf_splib07.json"))
    t2 = time.time()
    out07 = eng07.spectrum_analysis(spectrum, wl, w, bp, chanels, n_workers=NW, raw=True)
    print(f"[v07 classify] {time.time()-t2:.1f}s", flush=True)
    np.savez(GOLD07, **{name: arr for name, arr in zip(LAYERS + RAW, out07)})
    print(f"[golden] wrote {GOLD07}", flush=True)

    # ---------------------------------- v07 subscene serial/parallel check
    sub = np.ascontiguousarray(spectrum[:200])
    s1 = eng07.spectrum_analysis(sub, wl, w, bp, chanels, n_workers=1, raw=True)
    s4 = eng07.spectrum_analysis(sub, wl, w, bp, chanels, n_workers=4, raw=True)
    for name, a, b in zip(LAYERS + RAW, s1, s4):
        same = np.array_equal(a, b) if a.dtype == np.uint8 else \
            (np.array_equal(np.isnan(a), np.isnan(b)) and
             np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)]))
        print(f"  v07 subscene serial-vs-parallel {name:16s} bitexact={same}", flush=True)
        if not same:
            raise SystemExit(f"v07 serial/parallel mismatch: {name}")

    # ------------------------------------------------------------ diff census
    L = []
    L.append("# splib07 迁移 · 阶段4 全场景双跑差异普查")
    L.append("")
    L.append("> 日期：2026-08-29 ｜ 脚本：`docs/_splib07_stage4_dualrun.py` ｜ 场景：EMIT_L2A_RFL_001_20220819T061448_2223104_025")
    L.append("> 双轨：legacy=rf.json+splib06b（与 golden_arrays.npz 逐位一致，已验证）；v07=rf_splib07.json+rf07_spectra.npz。")
    L.append("")
    L.append("## 五图层差异普查")
    L.append("")
    L.append("| 图层 | 相同像元 | 差异像元 | 差异占比 |")
    L.append("|---|---|---|---|")
    for name, a, b in zip(LAYERS, out06[:5], out07[:5]):
        same = np.all(a == b, axis=-1)
        L.append(f"| {name} | {same.sum()} | {(~same).sum()} | {(~same).mean()*100:.3f}% |")
    L.append("")

    # class transition matrices on the class images (RGB tuple == class color)
    for li, name in enumerate(["mus_image", "chl_image", "cal_image"], start=2):
        a = out06[li].reshape(-1, 3)
        b = out07[li].reshape(-1, 3)
        both = np.vstack([a, b])
        uniq, inv = np.unique(both, axis=0, return_inverse=True)
        ca, cb = inv[:len(a)], inv[len(a):]
        changed = ca != cb
        L.append(f"### {name} 类别迁移（差异 {changed.sum()} 像元）")
        L.append("")
        if changed.any():
            pairs, counts = np.unique(np.stack([ca[changed], cb[changed]], axis=1),
                                      axis=0, return_counts=True)
            order = np.argsort(-counts)
            L.append("| legacy RGB | v07 RGB | 像元数 |")
            L.append("|---|---|---|")
            for i in order[:15]:
                pa, pb = pairs[i]
                L.append(f"| {tuple(uniq[pa])} | {tuple(uniq[pb])} | {counts[i]} |")
        L.append("")

    L.append("## center 连续图层差异")
    L.append("")
    L.append("| 图层 | 双非零像元 | Δ 中位数 | Δ p95 | Δ max | 仅 legacy 非零 | 仅 v07 非零 |")
    L.append("|---|---|---|---|---|---|---|")
    for name, a, b in zip(RAW[:3], out06[5:8], out07[5:8]):
        a = np.nan_to_num(a)
        b = np.nan_to_num(b)
        nz = (a != 0) & (b != 0)
        d = np.abs(a[nz] - b[nz]) if nz.any() else np.array([0.0])
        L.append(f"| {name} | {nz.sum()} | {np.median(d):.4f} | "
                 f"{np.percentile(d, 95):.4f} | {d.max():.4f} | "
                 f"{((a != 0) & (b == 0)).sum()} | {((a == 0) & (b != 0)).sum()} |")
    L.append("")
    a, b = out06[8], out07[8]
    nz = (a != 0) & (b != 0)
    d = np.abs(a[nz] - b[nz])
    L.append(f"fd（best fit×depth）双非零 {nz.sum()} 像元：Δ 中位数 {np.median(d):.4f}，"
             f"p95 {np.percentile(d, 95):.4f}，max {d.max():.4f}")
    L.append("")
    with open(r"d:\CRAMM\docs\splib07_dualrun_diff.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"[done] total {time.time()-t0:.1f}s -> docs/splib07_dualrun_diff.md", flush=True)


if __name__ == "__main__":
    main()
