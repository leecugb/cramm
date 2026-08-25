# -*- coding: utf-8 -*-
"""整景分类 -> 5 幅 GeoTIFF(正射校正),输出目录由 TIMING_OUT_DIR 指定。

复用 timing_full_scene.py 的加载/分类路径;nw 默认 8(本机 72 核实测最优档)。
注意:会覆盖输出目录中同名的旧版产品(如 2026-08-21 Windows 运行产物)。"""
import os
import time

from cramm import MicaEngine

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
OUT_DIR = os.environ.get("TIMING_OUT_DIR", r"D:/test")
NW = int(os.environ.get("TIMING_WORKERS", "8").split(",")[-1])


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    engine = MicaEngine()

    t0 = time.perf_counter()
    spectrum, lon, lat, w, bp, wl, chanels = engine.load_emit(NC)
    print(f"[load] {time.perf_counter() - t0:.1f}s  shape={spectrum.shape}", flush=True)

    t0 = time.perf_counter()
    orth, color, mus, chl, cal = engine.spectrum_analysis(
        spectrum, wl, w, bp, chanels, n_workers=NW
    )
    print(f"[classify nw={NW}] {time.perf_counter() - t0:.1f}s", flush=True)

    t0 = time.perf_counter()
    base = os.path.join(OUT_DIR, os.path.splitext(os.path.basename(NC))[0])
    engine.write_tiff(base, lon, lat, orth, color, mus, chl, cal)
    print(f"[write_tiff] {time.perf_counter() - t0:.1f}s -> {base}_*.tiff", flush=True)


if __name__ == "__main__":
    main()
