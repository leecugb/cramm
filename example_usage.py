#!/usr/bin/env python
# coding: utf-8
"""
CRAMM core package usage examples
=================================

Five typical scenarios, from simple to advanced:

  1. quickstart    full-scene processing: NetCDF -> 3 GeoTIFFs (CLI equivalent)
  2. pixel         single-pixel/single-spectrum identification: Top-N results + PDF diagnostics
  3. raw           float output: muscovite absorption center + fit x depth confidence
  4. custom_rules  custom rule library + cache invalidation contract
  5. components    bypass the facade and use components directly (EmitReader/MicaClassifier/ResultRenderer)

Run:
  python example_usage.py pixel      # run example 2 only (no path edits needed, fastest)
  python example_usage.py all        # everything (examples 1/3 need full-scene analysis, ~70s each)

Requires: test data ./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc
"""
import os
import sys

import numpy as np

NC_PATH = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"


# ---------------------------------------------------------------------------
# Example 1: full-scene processing (most common) -- equivalent to
#   python -m cramm.mica_engine -i <nc> -o output --raw
# ---------------------------------------------------------------------------

def example_quickstart():
    from cramm import MicaEngine

    engine = MicaEngine()  # bundled rf.json + splib06b spectral library + color table

    # load EMIT L2A NetCDF: reflectance cube (float32), lon/lat, band params, valid bands
    spectrum, lon, lat, w, bp, wl, chanels = engine.load_emit(NC_PATH)
    print(f"image {spectrum.shape}, valid bands {len(chanels)}/{len(w)}")

    # spectral analysis: classification + rendering. n_workers=None defaults to min(cpu, 8)
    orth_rgb, color_enhanced, mus_image = engine.spectrum_analysis(
        spectrum, wl, w, bp, chanels,
        n_workers=4,
        progress_callback=lambda p: print(f"  {p}%"),
    )

    # write 3 georeferenced GeoTIFFs (output directory created automatically)
    engine.write_tiff("output/scene", lon, lat, orth_rgb, color_enhanced, mus_image)
    # → output/scene_mapping_orth.tiff / scene_color_enhanced_orth.tiff / scene_mus_orth.tiff


# ---------------------------------------------------------------------------
# Example 2: single-spectrum identification -- the core call for interactive apps
# (GUI pixel picking, field spectrometers)
# ---------------------------------------------------------------------------

def example_pixel():
    from cramm import MicaEngine

    engine = MicaEngine()
    spectrum, lon, lat, w, bp, wl, chanels = engine.load_emit(NC_PATH)

    # take the image center pixel. Two input styles are equivalent (facade handles both):
    #   A. full bands [285] or [1,285] -- engine auto-selects valid bands per chanels
    #   B. pre-selected bands [244] / [1,244]
    pixel = spectrum[spectrum.shape[0] // 2, spectrum.shape[1] // 2, :]

    results = engine.classify_spectrum(
        pixel, wl, w, bp, chanels,
        top_n=5,
        pdf_path="output/pixel_diag.pdf",  # optional: Top-N feature continuum-removal diagnostic plots
    )
    for r in results:
        print(f"  {r['name']:<40s} fit={r['fit']:.4f}  fd={r['fd']:.4f}")

    # repeated calls hit the compile cache (reference-side constants computed once),
    # ideal for interactive per-pixel queries


# ---------------------------------------------------------------------------
# Example 3: float output -- use raw values for your own mapping / thresholding
# ---------------------------------------------------------------------------

def example_raw():
    from cramm import MicaEngine

    engine = MicaEngine()
    spectrum, lon, lat, w, bp, wl, chanels = engine.load_emit(NC_PATH)

    orth, color, mus, mus_center, fd = engine.spectrum_analysis(
        spectrum, wl, w, bp, chanels, n_workers=4, raw=True,
    )
    # mus_center [r,c]: muscovite 2.2μm absorption-center wavelength (μm); 0 for non-muscovite pixels
    #            -- Al-content indicator: shorter wavelength = high Al, longer = low Al / illitization
    # fd        [r,c]: per-pixel best fit x depth joint confidence
    print(f"muscovite pixel count: {(mus_center > 0).sum()}, absorption-center range "
          f"{mus_center[mus_center > 0].min():.4f}–{mus_center[mus_center > 0].max():.4f} μm")
    np.savez_compressed("output/scene_raw.npz", mus_center=mus_center, fd=fd)


# ---------------------------------------------------------------------------
# Example 4: custom rule library -- must call invalidate_caches() after trimming/modifying rules
# ---------------------------------------------------------------------------

def example_custom_rules():
    from cramm import MicaEngine

    engine = MicaEngine()
    spectrum, lon, lat, w, bp, wl, chanels = engine.load_emit(NC_PATH)

    # scenario: run clay minerals only (trim the rule library for speed and fewer false positives)
    # engine.rf is an alias of the classifier's rule dict -- mutate it in place
    # (assigning engine.rf = clay would only rebind the alias, not the classifier's dict)
    clay = {k: v for k, v in engine.rf.items()
            if any(s in k for s in ("kaolinite", "illite", "smectite", "muscovite"))}
    engine.rf.clear()
    engine.rf.update(clay)
    engine.invalidate_caches()  # critical! the cache key does not include rule-library content; stale constants persist unless cleared

    pixel = spectrum[spectrum.shape[0] // 2, spectrum.shape[1] // 2, :]
    for r in engine.classify_spectrum(pixel, wl, w, bp, chanels, top_n=5):
        print(f"  {r['name']:<40s} fit={r['fit']:.4f}")

    # custom rules can also come from a JSON file: MicaEngine(rf_path="my_rules.json")
    # format: see cramm/data/rf.json (top level {"rf": {...}, "mixtures": {...}, "wavelength_map": {...}})


# ---------------------------------------------------------------------------
# Example 5: bypass the facade and use components directly -- when embedding into your own pipeline
# ---------------------------------------------------------------------------

def example_components():
    from cramm.classifier import MicaClassifier
    from cramm.emit_reader import EmitReader
    from cramm.renderer import ResultRenderer

    # each component loads self-contained, independent of the others
    spectrum, lon, lat, w, bp, wl, chanels = EmitReader.load(NC_PATH)
    clf = MicaClassifier.from_paths()          # bundled rule library + splib
    renderer = ResultRenderer.from_paths()     # bundled color table

    # classify (returns ClassificationResult: fit/depth/num/mus_center/index etc.)
    result = clf.classify(spectrum, wl, w, bp, chanels, n_workers=4)
    print(f"mineral species identified: {(result.num.max())} / {len(result.index)} rules total")
    print(f"mineral name list: {result.index[:5]} ...")

    # rendering the three maps + writing GeoTIFF are separate calls (e.g. thematic map only, custom output names)
    orth_rgb, color_enhanced, mus_image = renderer.render(result)
    renderer.write_tiff("output/scene_comp", lon, lat, orth_rgb, color_enhanced, mus_image)


# ---------------------------------------------------------------------------

EXAMPLES = {
    "quickstart": ("full-scene processing -> GeoTIFF", example_quickstart),
    "pixel": ("single-spectrum identification + PDF diagnostics", example_pixel),
    "raw": ("float output mus_center/fd", example_raw),
    "custom_rules": ("custom rule library", example_custom_rules),
    "components": ("component-level calls", example_components),
}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "pixel"
    if not os.path.exists(NC_PATH):
        sys.exit(f"test data not found: {NC_PATH}")
    os.makedirs("output", exist_ok=True)
    for key, (title, fn) in EXAMPLES.items():
        if which not in ("all", key):
            continue
        print(f"== Example {key}: {title} ==", flush=True)
        fn()
