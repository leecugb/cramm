#!/usr/bin/env python
# coding: utf-8
"""
Single-spectrum analysis tests (classify_spectrum path)
========================================================

Functional validation of classify_spectrum single-spectrum identification
(complements the bit-exact suites):

  1. Self-identification  77 rule reference spectra (incl. synthetic mixtures) with
                          zero-noise input -> own rule should hit Top-5. Known
                          exceptions: pure calcite / dolomite references do not satisfy
                          their own constraints (USGS rules are tuned for real noisy
                          spectra) -- inherent algorithm behavior, not a defect
  2. Noise robustness     4 representative rules x 10 random seeds (sigma=0.005 Gaussian
                          noise) -> all Top-5
  3. Real pixel           center pixel of the test scene Top-1 hits the known
                          expectation (calcite-montmorillonite mixture)
  4. Determinism          same input called twice -> name list + fit/fd bit-exact
  5. Input style equiv.   full-band [285] input == pre-selected band [244] input (bit-exact)
  6. PDF diagnostics      real pixel generates Top-3 feature PDF
  7. Compile cache        warmed calls significantly faster than the first
                          (reference-side constants compiled only once)

Usage:
    python test_single_spectrum.py           # needs the EMIT test scene in the run directory
    python test_single_spectrum.py --nc <path>
"""
import os
import sys
import time
import traceback
import warnings

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root (where the cramm package lives)

NC_DEFAULT = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"

# Known algorithm behavior: the two pure references (zero noise) never hit their own rules
KNOWN_SELF_MISS = {"calcite", "dolomite"}
# 4 representative rules for the noise-robustness test (single minerals + snow + mixture, stable at sigma=0.005)
NOISE_RULES = ["muscovite_lowAl", "kaolinite_wxl", "snow_melting", "calcite.3+muscoviteLowAl.7"]

RESULTS = []


def run(name, fn):
    try:
        fn()
    except BaseException as e:
        RESULTS.append(("FAIL", name))
        print(f"[FAIL] {name}: {e}")
        traceback.print_exc()
    else:
        RESULTS.append(("OK", name))
        print(f"[ OK ] {name}")


def _bytes(x):
    return np.ascontiguousarray(np.float64(x)).tobytes()


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

_CTX = None


def ctx(nc_path):
    global _CTX
    if _CTX is None:
        from cramm import MicaEngine
        eng = MicaEngine()
        spectrum, lon, lat, w, bp, wl, chanels = eng.load_emit(nc_path)
        resampled1 = eng.get_resample(w, bp)
        _CTX = (eng, spectrum, w, bp, wl, chanels, resampled1)
    return _CTX


# ---------------------------------------------------------------------------
# Test construction (closure captures nc_path)
# ---------------------------------------------------------------------------

def make_tests(nc_path):
    def _ref_spec(eng, resampled1, name):
        rid = eng.rf[name]["reference"]["reflectance_record"]
        spec = resampled1[rid].copy()
        spec[np.isnan(spec)] = 0
        return spec

    def test_self_identification():
        """77 rules zero-noise self-identification: all Top-5 except known exceptions; rank-1 for the vast majority."""
        eng, spectrum, w, bp, wl, chanels, resampled1 = ctx(nc_path)
        ranks = {}
        for name in eng.rf:
            res = eng.classify_spectrum(_ref_spec(eng, resampled1, name), wl, w, bp, chanels, top_n=77)
            names = [r["name"] for r in res]
            ranks[name] = names.index(name) + 1 if name in names else -1
        misses = {k for k, v in ranks.items() if v < 0}
        assert misses <= KNOWN_SELF_MISS, f"unexpected misses: {misses - KNOWN_SELF_MISS}"
        assert KNOWN_SELF_MISS <= misses, f"known-exception behavior changed: {KNOWN_SELF_MISS - misses} now hit"
        over5 = {k: v for k, v in ranks.items() if v > 5}
        assert not over5, f"beyond Top-5: {over5}"
        n_rank1 = sum(1 for v in ranks.values() if v == 1)
        print(f"       rank-1: {n_rank1}/77, known exceptions missed: {sorted(misses)}")
        assert n_rank1 >= 60, f"abnormal rank-1 count: {n_rank1}"

    def test_noise_robustness():
        """4 representative rules x 10 seeds (sigma=0.005) -> all Top-5."""
        eng, spectrum, w, bp, wl, chanels, resampled1 = ctx(nc_path)
        for name in NOISE_RULES:
            rid = eng.rf[name]["reference"]["reflectance_record"]
            base = resampled1[rid].copy()
            valid = ~np.isnan(base)
            worst = 1
            for seed in range(10):
                rng = np.random.default_rng(seed)
                spec = base.copy()
                spec[valid] += rng.normal(0, 0.005, valid.sum())
                spec[~valid] = 0
                spec = np.maximum(spec, 0)
                res = eng.classify_spectrum(spec, wl, w, bp, chanels, top_n=77)
                names = [r["name"] for r in res]
                rank = names.index(name) + 1 if name in names else -1
                assert 0 < rank <= 5, f"{name} seed={seed} rank={rank}"
                worst = max(worst, rank)
            print(f"       {name}: worst rank over 10 seeds = {worst}")

    def test_real_pixel_expected():
        """Real pixel Top-1 hits the known expected mineral (center of this test scene is a calcite-montmorillonite mixture)."""
        eng, spectrum, w, bp, wl, chanels, _ = ctx(nc_path)
        pixel = spectrum[spectrum.shape[0] // 2, spectrum.shape[1] // 2, :]
        res = eng.classify_spectrum(pixel, wl, w, bp, chanels, top_n=5)
        assert res, "center pixel should be non-empty"
        assert res[0]["name"] == "calcite.8+montmorilloniteNa.2_mix_intimate", \
            f"Top-1 changed to {res[0]['name']}"
        assert abs(res[0]["fit"] - 0.9457) < 1e-3, f"fit drift: {res[0]['fit']}"
        print(f"       Top-1: {res[0]['name']} fit={res[0]['fit']:.4f}")

    def test_determinism():
        """Same input called twice: name list + fit/fd bit-exact."""
        eng, spectrum, w, bp, wl, chanels, _ = ctx(nc_path)
        pixel = spectrum[100, 200, :]
        r1 = eng.classify_spectrum(pixel, wl, w, bp, chanels, top_n=77)
        r2 = eng.classify_spectrum(pixel, wl, w, bp, chanels, top_n=77)
        assert [x["name"] for x in r1] == [x["name"] for x in r2]
        for a, b in zip(r1, r2):
            assert _bytes(a["fit"]) == _bytes(b["fit"]) and _bytes(a["fd"]) == _bytes(b["fd"])

    def test_input_style_equivalence():
        """Full-band [285] input == pre-selected band [244] input (real pixel, bit-exact)."""
        eng, spectrum, w, bp, wl, chanels, _ = ctx(nc_path)
        pixel = spectrum[640, 620, :]
        r_full = eng.classify_spectrum(pixel, wl, w, bp, chanels, top_n=77)
        r_sel = eng.classify_spectrum(pixel[chanels], wl, w, bp, chanels, top_n=77)
        assert [x["name"] for x in r_full] == [x["name"] for x in r_sel]
        for a, b in zip(r_full, r_sel):
            assert _bytes(a["fit"]) == _bytes(b["fit"]) and _bytes(a["fd"]) == _bytes(b["fd"])

    def test_pdf_generation():
        """Real pixel Top-3 feature diagnostic PDF generation."""
        import tempfile
        eng, spectrum, w, bp, wl, chanels, _ = ctx(nc_path)
        pixel = spectrum[spectrum.shape[0] // 2, spectrum.shape[1] // 2, :]
        pdf = os.path.join(tempfile.gettempdir(), "cramm_single_spec_test.pdf")
        try:
            res = eng.classify_spectrum(pixel, wl, w, bp, chanels, top_n=3, pdf_path=pdf)
            assert os.path.getsize(pdf) > 5000
            print(f"       PDF {os.path.getsize(pdf)//1024}KB / {len(res)} pages")
        finally:
            if os.path.exists(pdf):
                os.remove(pdf)

    def test_compile_cache_speedup():
        """Compile cache: warmed calls significantly faster than cold-start call (reference-side constants compiled only once)."""
        from cramm import MicaEngine
        eng2 = MicaEngine()  # fresh instance -> cold cache
        _, spectrum, w, bp, wl, chanels, _ = ctx(nc_path)
        pixel = spectrum[640, 620, :]
        t0 = time.perf_counter()
        eng2.classify_spectrum(pixel, wl, w, bp, chanels)
        t_cold = time.perf_counter() - t0
        t0 = time.perf_counter()
        for _ in range(5):
            eng2.classify_spectrum(pixel, wl, w, bp, chanels)
        t_warm = (time.perf_counter() - t0) / 5
        print(f"       cold start {t_cold:.2f}s / warm {t_warm:.3f}s ({t_cold/max(t_warm,1e-9):.1f}x)")
        assert t_warm < t_cold, "cache not effective"

    return [
        ("reference self-identification (77 rules zero noise)", test_self_identification),
        ("noise robustness (4 rules x 10 seeds)", test_noise_robustness),
        ("real pixel Top-1 expectation", test_real_pixel_expected),
        ("determinism (two calls bit-exact)", test_determinism),
        ("input style equivalence (full-band == selected-band)", test_input_style_equivalence),
        ("PDF diagnostic generation", test_pdf_generation),
        ("compile cache speedup", test_compile_cache_speedup),
    ]


def main():
    import argparse
    ap = argparse.ArgumentParser(description="single-spectrum analysis tests (classify_spectrum)")
    ap.add_argument("--nc", default=NC_DEFAULT, help="EMIT NetCDF path")
    args = ap.parse_args()

    if not os.path.exists(args.nc):
        sys.exit(f"test data not found: {args.nc} (specify with --nc)")
    warnings.filterwarnings("ignore")  # RuntimeWarnings such as constraint divide-by-zero are normal for the algorithm

    for name, fn in make_tests(args.nc):
        run(name, fn)

    n_ok = sum(1 for s, _ in RESULTS if s == "OK")
    n_fail = sum(1 for s, _ in RESULTS if s == "FAIL")
    print(f"\nSummary: {n_ok} passed / {n_fail} failed")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
