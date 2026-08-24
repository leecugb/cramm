# CRAMM performance benchmark (authoritative record)

Date: 2026-08-23 · Code: HEAD after cal_center (commit c683947 + docs) ·
Scene: `EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc` (1280×1242×285,
1.85 GB, 1,589,760 px, 244/285 valid bands) · Machine: Windows 11
(10.0.26200), Intel 24 logical CPUs, Python 3.13.9, numpy 2.3.5.

Reproduce: `python benchmark.py --full --workers 1 2 4 --json docs/benchmark.json`
from the repo root. Raw log: `docs/benchmark.log`; machine-readable:
`docs/benchmark.json`. `n_workers=8` is excluded — it OOMs on this machine
(worker chunk ~590 MiB float64); nw=4 is the practical setting.

## Full scene (classification + three center product lines + arbitration)

| n_workers | wall time | throughput | vs serial |
|---|---|---|---|
| 1 (serial) | 131.73 s | 12,068 px/s | 1.00× |
| 2 | 93.00 s | 17,093 px/s | 1.42× |
| 4 | 61.88 s | 25,689 px/s | 2.13× |

Serial and parallel outputs are bit-identical (guarded by
`tests/test_parallel.py` against `tests/golden_arrays.npz`).

## Other operations

| operation | time |
|---|---|
| load_emit (1.85 GB NetCDF → cube) | 3.75 s |
| reference resampling, cold (72 records → 285 bands) | 133.4 ms |
| single-spectrum classify, cold (resample + rule compilation) | 159.1 ms |
| single-spectrum classify, warm (median of 30) | 9.8 ms (16.3× cache speedup) |
| orthorectify + 3 GeoTIFFs | 4.66 s |
| Top-3 single-spectrum diagnostic PDF | 2.42 s |

## Earlier runs and consistency

- `output/benchmark_full.log` (pre-cal_center): serial 131.15 s, nw=2 90.49 s,
  nw=4 64.91 s — consistent with the authoritative run above (cal_center adds
  no measurable cost: the carbonate arbitration never flips and the fit loop
  covers only ~5% of pixels).
- `D:/test/full_scene_timing.json`: serial 156.4 s was measured under tight
  RAM (~9.6 GB free); superseded by the table above.
- `tests/test_parallel.py 1` printed 224 s for its serial leg: that run
  followed a parallel run in the same process chain under memory pressure;
  not a clean serial measurement. Use this document's numbers.

## Status of the "faster than USGS MICA (IDL/PRISM)" claim

**Anchor measurement (author-reported, 2026-08-23)**: USGS PRISM (IDL MICA)
processing the same EMIT granule takes **~25 minutes (≈1500 s)**. Against the
authoritative table above this gives:

| comparison | ratio |
|---|---|
| CRAMM serial (131.73 s) vs PRISM (~1500 s) | **~11×** |
| CRAMM nw=4 (61.88 s) vs PRISM (~1500 s) | **~24×** |

Both execution modes exceed an order of magnitude, so the manuscript-level
claim "more than an order of magnitude faster" is defensible even under the
most conservative (serial-vs-PRISM) comparison.

**Protocol gaps still to close before submission** (the 25 min figure is a
single author-side observation; reviewers will ask for conditions):
- [x] same machine as the table above: **confirmed** (author, 2026-08-24) — PRISM and CRAMM timings are directly comparable
- [x] ENVI/IDL + PRISM version: **ENVI Classic 5.6.2 + IDL 8.8.2** (author-reported 2026-08-24) — far newer than the official PRISM v1.0 target (ENVI 4.8 + IDL 8.0, OFR 2011-1155), which makes the ~25 min figure conservative in PRISM's favour; still to state: which MICA command file / convolved library was used for EMIT
- [x] what the 25 min covers: **pure classification only** (author, 2026-08-24) — excludes the spectral-library convolution (PRISM Function 2.9) and the command-file editing/adaptation PRISM requires beforehand. This makes the comparison conservative in PRISM's favour: CRAMM's 131.73 s serial / 61.88 s nw=4 covers classification **plus** the three absorption-center product lines and arbitration, and CRAMM's runtime resampling of the whole reference library costs 133.4 ms cold (table above), i.e. the preprocessing PRISM excludes is effectively free in CRAMM
- [x] MICA command file / library used for the EMIT run: **official 2014 v6a, EMIT-convolved version** (author, 2026-08-24) — i.e. the identical rule content CRAMM was verified against, so the timing comparison is also a like-for-like rule-content comparison
- [ ] optional but strongest: one archived re-run of the PRISM classification with the log saved next to this file, converting the author-reported figure into a documented one

Until those are recorded, the manuscript states the comparison with its
conditions explicit (Section 4.3), and the abstract uses only the bounded
wording above.
