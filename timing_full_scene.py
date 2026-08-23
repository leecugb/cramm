# -*- coding: utf-8 -*-
"""整景影像处理耗时测试:加载 + 串行/并行分类,结果写入 D:/test。"""
import json
import os
import platform
import time

import numpy as np

from cramm import MicaEngine

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
OUT_DIR = r"D:/test"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    engine = MicaEngine()

    t0 = time.perf_counter()
    spectrum, lon, lat, w, bp, wl, chanels = engine.load_emit(NC)
    t_load = time.perf_counter() - t0

    rows, cols, bands = spectrum.shape
    alive = int(np.count_nonzero(spectrum[..., 0] > 0))  # 粗略活像元统计
    print(f"[load] {t_load:.1f}s  shape={spectrum.shape}  dtype={spectrum.dtype}")

    n_workers_list = [int(x) for x in os.environ.get("TIMING_WORKERS", "1,4").split(",")]
    runs = {}
    for nw in n_workers_list:
        t0 = time.perf_counter()
        orth, color, mus, chl, cal = engine.spectrum_analysis(
            spectrum, wl, w, bp, chanels, n_workers=nw
        )
        dt = time.perf_counter() - t0
        runs[f"n_workers={nw}"] = dt
        print(f"[classify n_workers={nw}] {dt:.1f}s")

    serial_key = next((k for k in runs if k == "n_workers=1"), None)
    par_key = next((k for k in runs if k != "n_workers=1"), None)
    t1 = runs.get("n_workers=1")
    t8 = runs.get(par_key) if par_key else None
    report = {
        "file": NC,
        "scene_shape": [rows, cols, bands],
        "machine": {
            "platform": platform.platform(),
            "cpu": platform.processor(),
            "logical_cpus": os.cpu_count(),
            "python": platform.python_version(),
        },
        "load_emit_s": round(t_load, 2),
        "runs_s": {k: round(v, 2) for k, v in runs.items()},
        "pixels": rows * cols,
    }
    if t1 and t8:
        report["speedup"] = round(t1 / t8, 2)
        report["serial_ms_per_kpixel"] = round(t1 / (rows * cols) * 1000 * 1000, 1)
        report["parallel_ms_per_kpixel"] = round(t8 / (rows * cols) * 1000 * 1000, 1)
    out = os.path.join(OUT_DIR, "full_scene_timing.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
