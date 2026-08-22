#!/usr/bin/env python
# coding: utf-8
"""CRAMM runtime benchmark
=========================

Measures the package's runtime on the EMIT test scene, in two modes:

    python benchmark.py              # quick (~2 min): everything except full-scene sweeps
    python benchmark.py --full       # complete (~10 min): adds full-scene n_workers sweep
    python benchmark.py --full --workers 1 2 4 8

Sections
    1. environment        CPU / platform / numpy
    2. load_emit          NetCDF read + bad-band removal (1.8 GB input)
    3. get_resample       cold (fresh engine) vs warm (cached)
    4. classify_spectrum  cold (first call) vs warm (median of repeated calls)
    5. subset scene       150-row slab, n_workers sweep -> per-pixel throughput & scaling
    6. full scene         (--full) whole 1280x1242 scene, n_workers sweep + write_tiff
    7. PDF diagnostics    classify_spectrum with pdf_path

Requires the EMIT test scene (NC constant below). Results are printed as a
table and optionally saved with --json <path>.
"""
import argparse
import json
import os
import platform
import statistics
import sys
import time

import numpy as np

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
SUBSET_ROWS = 150

REPORT = {}


def fmt(t):
    return f"{t * 1000:.1f} ms" if t < 1 else f"{t:.2f} s"


def record(section, name, value, unit=""):
    REPORT.setdefault(section, []).append((name, value, unit))
    print(f"  {name:<58s} {value}{(' ' + unit) if unit else ''}", flush=True)


def main():
    ap = argparse.ArgumentParser(description="CRAMM runtime benchmark")
    ap.add_argument("--full", action="store_true", help="add the full-scene n_workers sweep + write_tiff")
    ap.add_argument("--workers", type=int, nargs="+", default=None,
                    help="n_workers values for the full-scene sweep (default: 1 2 4 min(cpu,8))")
    ap.add_argument("--json", default=None, help="also save results to this JSON file")
    ap.add_argument("--nc", default=NC, help="EMIT NetCDF path")
    args = ap.parse_args()

    if not os.path.exists(args.nc):
        sys.exit(f"test scene not found: {args.nc}")

    from cramm import MicaEngine

    print("== 1. environment ==", flush=True)
    ncpu = os.cpu_count() or 1
    record("environment", "logical CPUs", ncpu)
    record("environment", "platform", platform.platform())
    record("environment", "numpy", np.__version__)

    # ---- 2. load_emit ----
    print("== 2. load_emit (NetCDF read + bad-band removal) ==", flush=True)
    engine = MicaEngine()
    t0 = time.perf_counter()
    spectrum, lon, lat, w, bp, wl, chanels = engine.load_emit(args.nc)
    t_first = time.perf_counter() - t0
    t0 = time.perf_counter()
    engine.load_emit(args.nc)
    t_second = time.perf_counter() - t0
    r, c, s = spectrum.shape
    record("load_emit", f"first read [{r}x{c}x{s}, {os.path.getsize(args.nc)/1e9:.2f} GB]", fmt(t_first))
    record("load_emit", "second read (OS disk cache warm)", fmt(t_second))

    # ---- 3. get_resample cold/warm ----
    print("== 3. get_resample ==", flush=True)
    t0 = time.perf_counter()
    engine.get_resample(w, bp)
    record("get_resample", "cold (72 records -> 285 bands, Gaussian kernel)", fmt(time.perf_counter() - t0))
    t0 = time.perf_counter()
    engine.get_resample(w, bp)
    record("get_resample", "warm (cache hit)", fmt(time.perf_counter() - t0))

    # ---- 4. classify_spectrum cold/warm ----
    print("== 4. classify_spectrum (single pixel) ==", flush=True)
    pixel = spectrum[r // 2, c // 2, :]
    e2 = MicaEngine()  # fresh engine: nothing cached
    t0 = time.perf_counter()
    e2.classify_spectrum(pixel, wl, w, bp, chanels, top_n=10)
    t_cold = time.perf_counter() - t0
    warm = []
    for _ in range(30):
        t0 = time.perf_counter()
        e2.classify_spectrum(pixel, wl, w, bp, chanels, top_n=10)
        warm.append(time.perf_counter() - t0)
    t_warm = statistics.median(warm)
    record("classify_spectrum", "cold (first call: resample + rule compilation)", fmt(t_cold))
    record("classify_spectrum", f"warm (median of {len(warm)}, compile cache hit)", fmt(t_warm))
    record("classify_spectrum", "cache speedup", f"{t_cold / t_warm:.1f}x")

    # ---- 5. subset scene scaling ----
    print(f"== 5. subset scene (first {SUBSET_ROWS} rows = {SUBSET_ROWS * c:,} pixels) ==", flush=True)
    sub = spectrum[:SUBSET_ROWS]
    for nw in (1, 2, 4):
        t0 = time.perf_counter()
        engine.spectrum_analysis(sub, wl, w, bp, chanels, n_workers=nw)
        t = time.perf_counter() - t0
        px = SUBSET_ROWS * c / t
        record("subset_scene", f"n_workers={nw}: {fmt(t)}", f"{px:,.0f} px/s")

    # ---- 6. full scene sweep (--full) ----
    if args.full:
        workers = args.workers or sorted({1, 2, 4, min(ncpu, 8)})
        print(f"== 6. full scene ({r}x{c} = {r * c:,} pixels), sweep {workers} ==", flush=True)
        t_serial = None
        last = None
        for nw in workers:
            t0 = time.perf_counter()
            last = engine.spectrum_analysis(spectrum, wl, w, bp, chanels, n_workers=nw)
            t = time.perf_counter() - t0
            if nw == 1:
                t_serial = t
            px = r * c / t
            speedup = f", {t_serial / t:.2f}x vs serial" if t_serial else ""
            record("full_scene", f"n_workers={nw}: {fmt(t)}{speedup}", f"{px:,.0f} px/s")
        orth, color, mus = last[:3]
        t0 = time.perf_counter()
        engine.write_tiff("output/benchmark_scene", lon, lat, orth, color, mus)
        record("write_tiff", "orthorectify + 3 GeoTIFFs", fmt(time.perf_counter() - t0))

    # ---- 7. PDF diagnostics ----
    print("== 7. PDF diagnostics ==", flush=True)
    t0 = time.perf_counter()
    res = e2.classify_spectrum(pixel, wl, w, bp, chanels, top_n=3, pdf_path="output/benchmark_diag.pdf")
    record("pdf", f"Top-{len(res)} feature continuum-removal PDF", fmt(time.perf_counter() - t0))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(REPORT, f, indent=2, ensure_ascii=False)
        print(f"results saved: {args.json}", flush=True)

    print("\nDone.", flush=True)


if __name__ == "__main__":
    main()
