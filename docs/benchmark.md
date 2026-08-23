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

## Status of the "10× faster than USGS MICA (IDL)" claim

**No in-repo evidence exists**: the IDL/ENVI MICA run behind the ~10× figure
was an author-side measurement and is not archived here. Before submission,
either (a) re-run official MICA on this scene with a documented protocol
(ENVI/IDL version, machine, settings) and archive the log next to this file,
or (b) downgrade the wording to what this file proves (absolute throughput
and scaling). Option (a) is strongly preferable — reviewers will ask.
