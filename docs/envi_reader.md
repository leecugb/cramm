# ENVI Standard HDR input support

> Added: 2026-11-26
> Scope: ENVI Standard `.hdr` + binary reflectance cubes. This is an input adapter, not a new classification algorithm or an independent sensor-validation claim.

## Supported contract

`MicaEngine.load_envi("scene.hdr")` returns:

```text
spectrum, lon, lat, w, bp, wl, chanels
```

- `spectrum`: float32 `[lines, samples, bands]` reflectance;
- `w`, `bp`: full-band center wavelengths and FWHM in µm;
- `wl`: valid-band wavelengths;
- `chanels`: zero-based valid-band indices;
- `lon`, `lat`: `None`. ENVI map metadata are not expanded into per-pixel coordinate grids.

The reader supports:

- BSQ, BIL and BIP interleave;
- little/big endian byte order;
- nonzero header offset;
- ENVI real-valued integer and floating-point data types;
- `wavelength`, `fwhm`, `wavelength units`, `reflectance scale factor`,
  `data ignore value` and optional `good_wavelengths`;
- automatic binary discovery beside the header, or explicit `data_path=`;
- explicit zero-based `valid_bands=` override.

If `wavelength units` is absent, values in the usual hundreds/thousands range are interpreted as nm, and values in the usual 0.35–2.5 range as µm. FWHM uses the same resolved units. If FWHM is absent, pass `fwhm=` explicitly in µm. Complex cubes and unsupported data types are rejected.

## Python API

```python
from cramm import MicaEngine

engine = MicaEngine()
spectrum, lon, lat, w, bp, wl, chanels = engine.load_envi(
    "scene.hdr",
    # data_path="scene.dat",       # optional explicit binary
    # fwhm=0.0074,                 # fallback in µm if absent from header
    # valid_bands=[...],           # optional sensor-specific mask
)

orth, color, mus, chl, cal = engine.spectrum_analysis(
    spectrum, wl, w, bp, chanels, n_workers=4
)
```

`write_envi` preserves the source `lines` and `samples`, performs no reprojection, and copies source `map info`, `coordinate system string`, `projection info`, `rpc info`, `geo points`, `x start` and `y start` when present. `write_tiff` remains the separate orthorectification path and requires genuine per-pixel lon/lat grids.

```python
orth, color, mus, chl, cal, mus_center, chl_center, cal_center, fd = \
    engine.spectrum_analysis(spectrum, wl, w, bp, chanels, n_workers=4, raw=True)
engine.write_envi(
    "output/scene", "scene.hdr", orth, color, mus, chl, cal,
    mus_center=mus_center, chl_center=chl_center, cal_center=cal_center, fd=fd,
)
```

## CLI

```bash
cramm -i scene.hdr -o output -w 4
# Optional:
#   --format envi
#   --envi-data /path/to/scene.dat
#   --envi-fwhm 0.0074
```

For ENVI input, the CLI writes five same-grid RGB products and one four-band float32 product. Each `.dat` has a matching `.hdr`; source map/CRS fields are inherited where present. No coordinate transformation or synthetic geolocation is introduced.

## Valid-band semantics

The generic reader does not apply the EMIT-specific mean-reflectance bad-band rule. It uses, in priority order:

1. explicit `valid_bands=`;
2. `good_wavelengths` in the header;
3. all bands.

Users converting an EMIT scene to ENVI should pass the original valid-band indices when they need production-equivalent channel selection.

## Test coverage

`tests/test_envi_reader.py` covers eleven cases:

- BSQ/BIL/BIP equivalence;
- nm units and unit inference;
- explicit µm fallback FWHM;
- int16 reflectance scaling;
- ignore values;
- big-endian input and header offset;
- `good_wavelengths` and explicit valid-band override;
- binary-size validation;
- `MicaEngine.load_envi` facade integration;
- same-grid ENVI output and verbatim map/CRS inheritance;
- output-grid mismatch rejection.

The full offline suite is **51 passed, 2 warnings**.

## Local converted-scene validation

Source: `/media/lee/KINGSTON/备份项目/GeoAHSI/scene.hdr`.

The header itself identifies the data as `FLAASH Result, EMIT converted test fixture`. It is therefore a format/algorithm fixture, not independent GeoAHSI imagery or geological ground truth.

Verified structure:

- 1280 × 1242 × 285;
- int16 BIL, little endian;
- `reflectance scale factor = 10000`;
- 350–2500 nm-equivalent EMIT wavelength grid, here 381.006–2492.92 nm;
- FWHM 8.415–8.809 nm;
- no per-pixel geolocation returned.

A full-scene API run using the original 244 EMIT valid channels completed successfully. Output counts were:

| Product | Positive pixels |
|---|---:|
| mus_center | 1,003,770 |
| chl_center | 31,005 |
| cal_center | 147,094 |
| fd | 1,586,469 |

A full-scene CLI run with the default 285/285 channels completed successfully and wrote six same-grid ENVI products: five three-band RGB products and one four-band float32 product. All outputs are 1280 × 1242. The source header contains no `map info` or `coordinate system string`, so these particular outputs contain no CRS fields; inheritance from headers that do contain those fields is covered by the writer tests.

These values describe execution on a quantized converted fixture, not independent classification accuracy. The reflectance comparison shows quantization-level agreement with the source EMIT data but is not bit-exact; no independent GeoAHSI scene validation is claimed.

Machine-readable evidence: `output/envi_hdr_validation/`.
