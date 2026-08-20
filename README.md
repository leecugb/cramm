# CRAMM

[![PyPI](https://img.shields.io/pypi/v/cramm)](https://pypi.org/project/cramm/)
[![Python](https://img.shields.io/pypi/pyversions/cramm)](https://pypi.org/project/cramm/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/leecugb/cramm/blob/main/LICENSE)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

**EMIT L2A hyperspectral mineral identification toolkit** — built on the USGS
MICA (Material Identification and Characterization Algorithm) decision-rule
system, and extended beyond it in two ways:

1. **An enhanced rule schema.** CRAMM adds an optional secondary-feature
   depth-ratio constraint (`max_depth_ratio_feat1_over_feat0`) that rejects
   pixels whose secondary absorption is too deep relative to the primary
   2.2 µm feature — suppressing white-mica false positives that pass the
   original five-layer MICA filtering. Nine bundled rules (muscovite, illite,
   kaolinite–muscovite mixtures) carry the new constraint; any custom rule
   can opt in. See *Enhancements over USGS MICA*.
2. **Wavelength-arbitrated muscovite subtyping.** MICA labels a pixel
   "muscovite_lowAl / medAl / medhighAl / Fe-rich" by best fit alone; CRAMM
   then re-arbitrates that attribution with the pixel's fitted 2.2 µm
   absorption center against per-rule calibrated wavelength windows
   (`absorption_center_range`) — the spectroscopically meaningful axis along
   which these four subtypes are actually defined. See *Enhancements over
   USGS MICA → Wavelength-based muscovite attribution*.
3. **From mineral detection to mineral composition.** Beyond labeling
   muscovite pixels, CRAMM fits the per-pixel 2.2 µm absorption-center
   wavelength (`mus_center`) — a quantitative composition proxy whose
   thermodynamic basis (Tschermak substitution vs. wv2200 on a
   GEMS/MINES23.1 reaction-path phase diagram) lets each fitted pixel be
   read as muscovite chemistry, formation temperature and fluid K⁺/H⁺
   conditions. See *Application: reading muscovite composition from
   mus_center*.

Everything is pure Python and GUI-free. Cross-platform:
**Windows / Linux / macOS** · Python **3.9 – 3.13**

---

## Highlights

- **Enhanced MICA pipeline** — continuum removal → closed-form 2×2 least
  squares → fit (r²) & absorption depth → five-layer constraint filtering
  **+ the CRAMM depth-ratio constraint**, driven by a JSON rule library
  (77 rules covering clay, sulfate, carbonate, mica, chlorite, amphibole,
  iron oxide, snow/ice and their mixtures).
- **Quantitative muscovite mapping** — per-pixel 2.2 µm absorption-center
  wavelength as a dedicated thematic map and float array; the same center
  also re-arbitrates the lowAl / medAl / medhighAl / Fe-rich attribution
  against calibrated wavelength windows, with a phase-diagram
  interpretation framework.
- **Whole-scene and single-spectrum modes** — batch-classify an entire EMIT
  scene to GeoTIFF, or identify one spectrum (GUI point-click, field
  spectrometer) with Top-N ranking and a PDF diagnostic report.
- **Fast** — reference-side constants are precompiled once per band
  configuration (two-level cache; ~16× speedup on repeated single-spectrum
  calls), and scene classification parallelizes across rules with worker
  processes.
- **Bit-exact discipline** — serial and parallel paths produce identical
  bytes; every change is guarded by a dual-path golden regression suite.
- **Self-contained** — the rule library (`rf.json`), the USGS `splib06b`
  spectral library, and the mineral color table are bundled inside the wheel.

## How it works

```
EMIT L2A NetCDF
      │  load_emit (bad-band removal, float32 cube)
      ▼
Reference resampling ── splib06b records ──► sensor wavelengths/FWHM
      │                                        (Gaussian kernel, cached)
      ▼
Per-rule evaluation (77 rules, parallel across rules)
      │  diagnostic features: continuum removal → 2×2 LSQ → r² / depth
      │  not-absorption / not-related features: exclusion filters
      │  continuum & depth-ratio constraints
      ▼
Best-match selection (argmax fit×depth)  +  muscovite 2.2 µm center fit
      │
      ▼
Mineral map · color-enhanced map · muscovite map (+ raw float arrays)
```

## Installation

```bash
pip install cramm            # core features (PyPI wheels on all three platforms)
pip install cramm[tiff]      # + GeoTIFF output (GDAL; PyPI wheels are Windows-only)
pip install cramm[pdf]       # + single-spectrum feature PDF diagnostics
pip install cramm[all]       # everything
```

**GDAL on Linux/macOS**: PyPI ships GDAL wheels for Windows only. Install a
system libgdal first (conda-forge recommended), then install without deps:

```bash
conda install -c conda-forge gdal
pip install cramm --no-deps        # or: pip install cramm[pdf]
```

Without GDAL, only `write_tiff` (GeoTIFF output) is unavailable — all
classification and analysis functions work (lazy import).

From source (sdist / checkout):

```bash
pip install .            # add [all] for the optional extras
```

## Quick start

### Command line

```bash
cramm -i EMIT_L2A_RFL_001_xxx.nc -o output [-n scene] [-w 4] [--raw]
```

| Flag | Default | Meaning |
|---|---|---|
| `-i`, `--input` | *(required)* | Path to the EMIT L2A NetCDF file |
| `-o`, `--output` | `.` | Output directory |
| `-n`, `--name` | input filename | Output filename prefix |
| `-w`, `--workers` | `min(cpu, 8)` | Parallel worker processes (`1` = serial) |
| `--raw` | off | Also save `mus_center` + `fd` float arrays as `.npz` |

**Output files** (written to `<output>/<name>*`):

| File | Content |
|---|---|
| `<name>_mapping_orth.tiff` | Mineral map (orthorectified, rule-library colors) |
| `<name>_color_enhanced_orth.tiff` | Color-enhanced mineral map |
| `<name>_mus_orth.tiff` | Muscovite 2.2 µm absorption-center thematic map |
| `<name>_raw.npz` | *(only with `--raw`)* `mus_center` [μm] + `fd` (fit×depth), float `[r, c]` |

### Python API

```python
from cramm import MicaEngine

engine = MicaEngine()                                    # all resources bundled
spectrum, lon, lat, w, bp, wl, chanels = engine.load_emit("EMIT_xxx.nc")

# --- whole scene → GeoTIFF -------------------------------------------------
orth, color, mus = engine.spectrum_analysis(spectrum, wl, w, bp, chanels,
                                            n_workers=4)
engine.write_tiff("output/scene", lon, lat, orth, color, mus)

# --- single spectrum (one pixel, field spectrometer, ...) ------------------
pixel = spectrum[100, 200, :]                            # full-band [285] or selected [len(chanels)]
results = engine.classify_spectrum(pixel, wl, w, bp, chanels,
                                   top_n=5, pdf_path="diag.pdf")
for r in results:
    print(f"{r['name']:50s} fit={r['fit']:.4f}  fd={r['fd']:.4f}")
```

`classify_spectrum` returns a list of `{"name", "fit", "fd"}` dicts sorted by
descending fit (empty list when nothing passes the filters). With
`pdf_path=` it also writes a multi-page PDF: one page per Top-N mineral with
continuum-removed feature overlays and constraint annotations (requires the
`[pdf]` extra).

Each PDF page dissects one candidate rule — every diagnostic / not-absorption
/ not-relative feature with its continuum endpoints, the reference
continuum-removed profile (squares) against the input (circles), and the
full constraint audit (k0/k1, r², raw depth, weights, thresholds):

![Single-spectrum diagnostic PDF: per-rule feature dissection](https://cdn.jsdelivr.net/gh/leecugb/cramm@main/docs/single_spectrum_diagnostic.png)

More scenarios — float (`raw=True`) output, custom rule libraries, the
`invalidate_caches()` contract, component-level calls — in
[example_usage.py](https://github.com/leecugb/cramm/blob/main/example_usage.py): `python example_usage.py pixel`.

## API overview

| `MicaEngine` method | Purpose |
|---|---|
| `load_emit(path)` | Read EMIT L2A NetCDF → `(spectrum, lon, lat, w, bp, wl, chanels)`; float32 cube, bad bands removed, fill values zeroed |
| `spectrum_analysis(spectrum, wl, w, bp, chanels, ...)` | Classify a whole scene → 3 uint8 RGB images; `raw=True` adds `mus_center` + `fd` float arrays. Supports `progress_callback`, `log_callback`, `cancel_flag`, `n_workers` |
| `classify_spectrum(spectrum, wl, w, bp, chanels, top_n=10, pdf_path=None)` | Identify one spectrum → Top-N `[{"name", "fit", "fd"}]` |
| `write_tiff(prefix, lon, lat, orth, color, mus)` | Orthorectify (pyresample) and write the 3 GeoTIFFs; requires GDAL |
| `get_resample(w, bp)` | All reference spectra resampled to the sensor bands `{record_id: spectrum}` (cached) |
| `invalidate_caches()` | **Required** after mutating `engine.rf` in place — see below |

### Custom rule libraries

```python
engine = MicaEngine(rf_path="my_rules.json")          # at construction
# — or mutate in place —
engine.rf["my_mineral"] = {...}
engine.invalidate_caches()                            # mandatory!
```

The compiled-rule cache is keyed on band configuration only, **not** on rule
content. If you modify `engine.rf` after any classification call, you must call
`invalidate_caches()` (or build a new engine) — otherwise results silently use
the old reference-side constants.

## Enhancements over USGS MICA

CRAMM extends the original USGS MICA decision rules with an optional per-rule
**secondary-feature depth-ratio constraint**,
`max_depth_ratio_feat1_over_feat0`:

> After the standard MICA filtering, a rule carrying this key rejects any pixel
> where `raw_depth(feat1) / raw_depth(feat0) ≥ threshold`, using the
> *unweighted* feature depths `(1 − min(continuum-removed)) × k0`. Pixels with
> an invalid primary feature (NaN depth) are conservatively kept.

For white micas the primary 2.2 µm Al-OH absorption (feat0) must dominate the
secondary ~2.35 µm feature (feat1); a secondary absorption that is too deep
relative to the primary indicates look-alike minerals rather than muscovite /
illite. Nine bundled rules use this constraint:

| Threshold | Rules |
|---|---|
| `0.6` | muscovite_lowAl, muscovite_medAl, muscovite_medhighAl, muscovite_Fe-rich, illite_imt1, illite_gds4 |
| `0.4` | kaolinite.5+muscoviteMedAl.5, kaolinite.5+muscoviteMedhighAl.5, kaolinite+muscovite_mix_intimate |

The constraint is part of the rule schema — custom rule libraries can set
`"max_depth_ratio_feat1_over_feat0": <float>` on any rule with ≥2 diagnostic
features; omitting the key disables it (original MICA behavior).

### Wavelength-based muscovite attribution

CRAMM also adds an optional per-feature **absorption-center window**,
`absorption_center_range` on a rule's first diagnostic feature. After the
best-match selection, pixels attributed to a rule carrying this field are
re-arbitrated by their fitted 2.2 µm absorption center (`mus_center`):

> If the center falls inside exactly one rule's `[lo, hi)` window, differs
> from the current match, and that rule itself accepted the pixel, the pixel
> is reassigned to the matching rule (fit/depth/index follow, and the center
> is refitted once with the new rule's endpoints). An invalid center, a
> center outside every window, or a center inside several overlapping
> windows keeps the original match (conservative).

The four bundled pure-muscovite rules carry calibrated windows (anchored on
each reference spectrum's measured wv2200): medhighAl `[2.195, 2.200)`,
medAl `[2.200, 2.206)`, lowAl / Fe-rich `[2.206, 2.220)` — the latter two
share a window, so wavelength never overrides their mutual attribution.
This is a scene-classification feature; single-spectrum Top-N ranking is
unaffected. Custom rule libraries opt in by adding the field; rules without
it are never reassigned.

## Application: reading muscovite composition from mus_center

The muscovite thematic map's per-pixel `mus_center` (2.2 µm Al-OH absorption
position) is a quantitative proxy for muscovite chemistry. The phase diagram
below — a GEMS/MINES23.1 titration reaction-path model of the
K₂O–Al₂O₃–SiO₂–H₂O–HCl–FeO–MgO system — overlays the Tschermak substitution
degree X_Ts = X(Fe-Celadonite)+X(Celadonite) in the muscovite stability field
with the corresponding wv2200 position (USGS conversion chain:
X_Ts → Al₂O₃ wt% → λ = −3.1·Al₂O₃ + 2308):

![Tschermak substitution degree vs. wv2200 in the muscovite field](https://cdn.jsdelivr.net/gh/leecugb/cramm@main/docs/muscovite_wv2200_phase_diagram.png)

X_Ts rises from ~0 on the high-T / low-K⁺ side to 0.35+ on the low-T / high-K⁺
side, and the wv2200 contours (magenta, 2190→2215 nm) run nearly parallel to
the X_Ts contours (dark blue). Each `mus_center` value fitted from an EMIT
pixel therefore maps directly onto this diagram, inverting muscovite
composition — and with it formation temperature and fluid K⁺/H⁺ conditions —
from orbit.

## Performance notes

- **Precompiled rules**: continuum endpoints, band indices, the reference-side
  normal-equation constant `B` and depth factors are computed once per
  `(wavelengths, FWHM, valid-band)` configuration and reused across all pixels
  and calls.
- **Parallelism**: scene classification fans out across the 77 rules with
  `multiprocessing` (spawn context); BLAS is pinned to a single thread so the
  parallel path stays bit-identical to the serial one.
- **Typical runtime**: a full EMIT scene (≈1280×1242 pixels) classifies in a
  few minutes on a desktop; a warm single-spectrum call is ≈10 ms.

## Testing

```bash
python tests/test_core.py              # 14 API contract / behavior tests
                                       # (integration section auto-skips without the test scene)

# The suites below need the EMIT test scene in the working directory
# (file name defined in each script's NC constant):
python tests/check_rows_logic.py       # rows alive-pixel semantics (14 checks)
python tests/test_single_spectrum.py   # single-spectrum identification (7 tests:
                                       #   self-ID / noise robustness / determinism / ...)
python tests/check_compiled_path.py    # compiled vs direct path, 302 pixels × 77 rules, bit-level diff
python tests/test_parallel.py 4        # full-scene golden regression (parallel)
python tests/test_parallel.py 1        # full-scene golden regression (serial)
```

**The golden baseline is platform-bound.** `tests/golden_arrays.npz` encodes
this machine's BLAS results; ulp-level differences across BLAS builds are
expected. On a new platform — or after an intentional classification-semantics
change — regenerate the baseline locally with `python regen_golden.py` (runs
both paths, asserts serial ≡ parallel, then rewrites the golden) before
relying on `test_parallel.py`.

## Troubleshooting

- **`netCDF4` fails to open a path containing non-ASCII characters on
  Windows** — a limitation of the netCDF C library, not of CRAMM. `cd` into the
  data directory and use a relative path instead.
- **`ImportError: gdal`** — you called `write_tiff` without GDAL installed; see
  *Installation*. Classification itself never imports GDAL.
- **`RuntimeWarning: invalid value encountered in divide`** during
  classification — benign: ratio constraints are evaluated against zero
  left-endpoint reflectances on some rules; the resulting NaN/inf correctly
  fails the comparison.

## Package layout

```
cramm/
  __init__.py       # exports MicaEngine / ProcessResult
  mica_engine.py    # facade: resource loading + component wiring + CLI main()
  emit_reader.py    # EMIT L2A NetCDF reader + bad-band removal (float32 contract)
  classifier.py     # MICA core: resampling / compiled rules / serial & parallel classification
  renderer.py       # rendering: three maps / GeoTIFF / single-spectrum PDF diagnostics
  data/             # rf.json + splib06b + color_table.json
tests/              # bit-exact verification suite + API contract tests
example_usage.py    # five usage-scenario examples
```

## Requirements

- Python 3.9 – 3.13
- Runtime: `numpy`, `pandas`, `netCDF4`, `pyproj`, `pyresample`, `threadpoolctl`
- Optional: `gdal` (GeoTIFF), `matplotlib` (PDF diagnostics)

## Acknowledgments

The decision rules implement the USGS MICA system
(Kokaly et al., `russet`-era rule set); reference spectra come from the USGS
splib06b spectral library (Clark et al., 2007). EMIT L2A products are courtesy
of NASA/JPL.
