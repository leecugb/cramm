#!/usr/bin/env python
# coding: utf-8
"""
CRAMM package test script (API contract + behavior tests)
=========================================================

Complements the bit-exact specialist suites:
    check_rows_logic.py     - rows surviving-pixel semantics (14 items, pure unit)
    check_compiled_path.py  - compiled/direct path 302x77 bit-exact diff (needs EMIT NC)
    test_parallel.py 4|1    - full-scene golden regression (needs EMIT NC, slowest)
    test_core.py            - this script: API contract / defensive behavior / integration smoke

Usage:
    python test_core.py                # unit section + (when NC exists) integration section
    python test_core.py --nc <path>    # specify EMIT NetCDF
    python test_core.py --golden       # additionally run test_parallel.py 4 and 1 in subprocesses

The unit section only needs the package-bundled cramm/data (rf.json + splib06b); no EMIT image needed.
"""
import os
import subprocess
import sys
import tempfile
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root (where the cramm package lives)

NC_DEFAULT = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"

# ----------------------------------------------------------------------------
# Mini test framework
# ----------------------------------------------------------------------------

RESULTS = []


class SkipTest(Exception):
    pass


def run(name, fn):
    try:
        fn()
    except SkipTest as e:
        RESULTS.append(("SKIP", name))
        print(f"[SKIP] {name}: {e}")
    except BaseException as e:
        RESULTS.append(("FAIL", name))
        print(f"[FAIL] {name}: {e}")
        traceback.print_exc()
    else:
        RESULTS.append(("OK", name))
        print(f"[ OK ] {name}")


def _bytes(x):
    return np.ascontiguousarray(np.float64(x)).tobytes()


# ----------------------------------------------------------------------------
# Shared fixture: package-bundled resources + synthetic band config (EMIT-like, with 2 bad-band ranges)
# ----------------------------------------------------------------------------

_ENG = None
W = None        # full-band wavelengths μm [285]
BP = None       # FWHM μm [285]
CHANELS = None  # valid band indices [n]
WL = None       # valid band wavelengths [n]


def eng():
    global _ENG, W, BP, CHANELS, WL
    if _ENG is None:
        from cramm.mica_engine import MicaEngine
        _ENG = MicaEngine()  # package-bundled rf.json + splib06b
        W = np.linspace(0.381, 2.508, 285)
        BP = np.full(285, 0.0074)
        # simulate bad bands: cut out two segments (EMIT-like water-vapor absorption regions)
        CHANELS = np.array([i for i in range(285) if not (126 <= i < 150 or 190 <= i < 210)])
        WL = W[CHANELS]
    return _ENG


def ref_spectrum():
    """Take a real reference spectrum (with bad-band gaps zeroed) as test input, plus small noise."""
    e = eng()
    resampled1 = e.get_resample(W, BP)
    rid = sorted(k for k in resampled1 if isinstance(k, int))[5]
    rng = np.random.default_rng(7)
    spec = resampled1[rid] + rng.normal(0, 0.003, len(W))
    return np.maximum(spec, 1e-4), resampled1[rid]


# ----------------------------------------------------------------------------
# A. Algorithm units
# ----------------------------------------------------------------------------

def test_resample_fast_vs_slow():
    """_resample_ searchsorted fast path vs original boolean slow path, bit-exact (real splib record)."""
    from cramm.classifier import _resample_
    e = eng()
    rid = sorted(e.ids)[3]
    wave_rec = e.wavelength_map[str(rid)]
    bands = e.dic3.loc[wave_rec, "data"]
    data = e.dic3.loc[rid, "data"]

    fast = _resample_(bands, data, W, BP)

    # slow-path reference implementation (original per-band boolean scan, independently rewritten inside the test)
    res = []
    data64 = data.astype("double")
    for x, y in zip(W, BP):
        mask = (bands < x + y / 2) & (bands > x - y / 2)
        if not mask.any():
            res.append(np.nan)
            continue
        lamda = y / 2
        sigma = (lamda**2 / np.log(2)) ** 0.5
        xx = bands[mask] - x
        wt = np.exp(-1 * xx**2 / sigma**2)
        temp = data64[mask]
        wt = wt[temp > 0]
        temp = temp[temp > 0]
        res.append((temp * wt).sum() / wt.sum() if len(temp) else np.nan)
    slow = np.array(res)

    nan_eq = np.isnan(fast) == np.isnan(slow)
    assert nan_eq.all(), "NaN positions differ"
    ok = ~np.isnan(fast)
    assert _bytes(fast[ok]) == _bytes(slow[ok]), "fast/slow path values differ"


def test_precompute_consistency():
    """_diagnostic_feature: pre-compiled vs on-the-fly computation bit-exact; rows subset contract."""
    from cramm.classifier import _continuum_constraints_list, _diagnostic_feature, _precompute_feature
    e = eng()
    rule = e.rf["muscovite_lowAl"]
    feat = rule["diagnostic_features"][0]
    resampled1 = e.get_resample(W, BP)
    ref = resampled1[rule["reference"]["reflectance_record"]][CHANELS]
    spec_full, _ = ref_spectrum()
    spec4 = np.repeat(spec_full[CHANELS][None, :], 4, axis=0)
    spec4[1] *= 1.01  # inter-row difference
    spec4[3] *= 0.99

    cc = _continuum_constraints_list(feat["continuum_constraints"])
    args = (feat["continuum_endpoints"], feat["feature_weight"], cc,
            feat["fit_constraint"], feat["depth_constraints"])

    direct = _diagnostic_feature(spec4, ref, WL, *args)
    pre = _precompute_feature(ref, WL, feat["continuum_endpoints"])
    compiled = _diagnostic_feature(spec4, None, WL, None, *args[1:], pre=pre)
    for a, b in zip(direct, compiled):
        assert _bytes(a) == _bytes(b), "pre-compiled path differs from on-the-fly computation"

    # rows subset contract: subset result == full result at subset positions, NaN elsewhere
    rows = np.array([1, 3])
    sub = _diagnostic_feature(spec4, ref, WL, *args, rows=rows)
    for f, s in zip(direct, sub):
        assert np.array_equal(np.isnan(f[rows]), np.isnan(s[rows]))
        ok = ~np.isnan(s[rows])
        assert _bytes(f[rows][ok]) == _bytes(s[rows][ok]), "rows subset values differ"
        out = np.delete(np.arange(4), rows)
        assert np.isnan(s[out]).all(), "positions outside rows must be NaN"


def test_endpoint_exc_compile_and_freshness():
    """Endpoint exceptions are decided at compile time; evaluation raises a fresh instance of the same type (cached instance does not accumulate traceback)."""
    from cramm.classifier import InvalidRangeError, _diagnostic_feature, _precompute_feature
    e = eng()
    resampled1 = e.get_resample(W, BP)
    rid = sorted(k for k in resampled1 if isinstance(k, int))[0]
    ref = resampled1[rid][CHANELS]

    pre = _precompute_feature(ref, WL, [9.0, 9.1, 9.2, 9.3])  # beyond band range -> no channels
    assert isinstance(pre["exc"], InvalidRangeError)

    spec = np.ones((1, len(CHANELS)))
    for _ in range(5):
        try:
            _diagnostic_feature(spec, None, WL, None, 1.0, pre=pre)
            raise AssertionError("should raise InvalidRangeError")
        except InvalidRangeError:
            pass
    assert pre["exc"].__traceback__ is None, "cached exception instance accumulated a traceback"


def test_vnir_only_graceful():
    """VNIR-only band config: SWIR rules gracefully skipped, no exception leakage, deterministic results."""
    e = eng()
    ch_v = CHANELS[WL < 1.05]
    wl_v = W[ch_v]
    spec_full, _ = ref_spectrum()
    spec_v = spec_full[ch_v].reshape(1, -1)
    clf = e._classifier

    r1 = clf.classify_spectrum(spec_v, wl_v, W, BP, ch_v)
    for _ in range(9):
        clf.classify_spectrum(spec_v, wl_v, W, BP, ch_v)
    n_exc = 0
    for rule in clf._compiled_rules.values():
        for ft in rule["diag"] + rule["not_abs"] + rule["not_rel"]:
            exc = ft[0].get("exc")
            if exc is not None:
                n_exc += 1
                assert exc.__traceback__ is None, "shared exception instance in VNIR scenario accumulated a traceback"
    assert n_exc > 0, "VNIR-only should have at least one rule judged invalid at compile time"
    r2 = clf.classify_spectrum(spec_v, wl_v, W, BP, ch_v)
    assert [x["name"] for x in r1] == [x["name"] for x in r2]


# ----------------------------------------------------------------------------
# B. API contract / defensive behavior
# ----------------------------------------------------------------------------

def test_classify_spectrum_shape_validation():
    """classifier-layer shape validation: 1-D / multi-row / wrong width all raise ValueError."""
    clf = eng()._classifier
    n = len(CHANELS)
    for bad in (np.zeros(n), np.zeros((2, n)), np.zeros((1, n + 1))):
        try:
            clf.classify_spectrum(bad, WL, W, BP, CHANELS)
            raise AssertionError(f"shape {bad.shape} should be rejected by ValueError")
        except ValueError:
            pass


def test_engine_band_selection_equivalence():
    """engine facade: full-band input with automatic band selection == caller pre-selected bands (bit-exact)."""
    e = eng()
    spec_full, _ = ref_spectrum()
    r_full = e.classify_spectrum(spec_full, WL, W, BP, CHANELS, top_n=len(e.rf))
    r_sel = e.classify_spectrum(spec_full[CHANELS], WL, W, BP, CHANELS, top_n=len(e.rf))
    assert [x["name"] for x in r_full] == [x["name"] for x in r_sel], "Top-N name lists differ"
    for a, b in zip(r_full, r_sel):
        assert _bytes(a["fit"]) == _bytes(b["fit"]) and _bytes(a["fd"]) == _bytes(b["fd"])


def test_invalidate_caches():
    """invalidate_caches clears both cache levels; results after rebuild are bit-exact."""
    e = eng()
    spec_full, _ = ref_spectrum()
    spec = spec_full[CHANELS].reshape(1, -1)
    r1 = e.classify_spectrum(spec, WL, W, BP, CHANELS)
    clf = e._classifier
    assert clf._compiled_key is not None and clf._resample_cache_key is not None
    e.invalidate_caches()
    assert clf._compiled_key is None and clf._resample_cache_key is None
    r2 = e.classify_spectrum(spec, WL, W, BP, CHANELS)
    assert [x["name"] for x in r1] == [x["name"] for x in r2]
    for a, b in zip(r1, r2):
        assert _bytes(a["fit"]) == _bytes(b["fit"])


def test_muscovite_guard():
    """classify does not crash when the custom rule library lacks the muscovite entry (MUSCOVITE_MINERALS guard)."""
    from cramm.classifier import MUSCOVITE_MINERALS
    e = eng()
    clf = e._classifier
    saved_rf, saved_index = clf.rf, None
    try:
        clf.rf = {k: v for k, v in saved_rf.items() if k != "muscovite_lowAl"}
        clf.invalidate_caches()
        spec_full, _ = ref_spectrum()
        cube = np.repeat(spec_full[None, None, :], 2, axis=0).repeat(2, axis=1)
        res = clf.classify(cube, WL, W, BP, CHANELS, n_workers=1)
        assert res.num.shape == (4,)
        assert "muscovite_lowAl" not in res.index
        for m in MUSCOVITE_MINERALS:
            assert m != "muscovite_lowAl" or m not in res.index_d
    finally:
        clf.rf = saved_rf
        clf.invalidate_caches()


def test_render_missing_color():
    """Color table missing a mineral name: render raises KeyError up front (rather than a bare KeyError at lookup)."""
    from cramm.classifier import ClassificationResult
    from cramm.renderer import ResultRenderer
    renderer = ResultRenderer.from_paths()
    bogus = ClassificationResult(
        fit=np.array([1.0]), depth=np.array([0.5]), num=np.zeros(1, dtype="uint8"),
        mus_center=np.zeros(1), r=1, c=1,
        index=["no_such_mineral"], index_d={"no_such_mineral": 0},
    )
    try:
        renderer.render(bogus)
        raise AssertionError("should raise KeyError")
    except KeyError as e:
        assert "color table is missing" in str(e) and "no_such_mineral" in str(e)


def test_specpr_and_splib_validation():
    """Empty/corrupt specpr -> ValueError; nonexistent splib path -> FileNotFoundError."""
    from cramm.classifier import MicaClassifier, _hyper_read_specpr
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        empty = f.name
    try:
        try:
            _hyper_read_specpr(empty)
            raise AssertionError("empty file should raise ValueError")
        except ValueError as e:
            assert "no spectral records parsed" in str(e)
    finally:
        os.remove(empty)
    try:
        MicaClassifier.from_paths(splib_path="no_such_splib.bin")
        raise AssertionError("should raise FileNotFoundError")
    except FileNotFoundError:
        pass


def test_emit_reader_non_emit_nc():
    """NetCDF without EMIT structure -> ValueError (rather than a bare IndexError)."""
    try:
        import netCDF4 as nc
    except ImportError:
        raise SkipTest("netCDF4 not available")
    from cramm.emit_reader import EmitReader
    path = os.path.join(tempfile.gettempdir(), "cramm_fake_nc_test.nc")
    with nc.Dataset(path, "w") as ds:
        ds.createDimension("x", 4)
        ds.createVariable("foo", "f4", ("x",))[:] = 1.0
    try:
        try:
            EmitReader.load(path)
            raise AssertionError("should raise ValueError")
        except ValueError as e:
            assert "not an EMIT L2A structure" in str(e)
    finally:
        os.remove(path)


def test_pdf_rcparams_restored():
    """plot_features_pdf is scoped via rc_context: global rcParams are not polluted."""
    try:
        import matplotlib as mpl
    except ImportError:
        raise SkipTest("matplotlib not available")
    e = eng()
    spec_full, _ = ref_spectrum()
    before = dict(mpl.rcParams)
    pdf = os.path.join(tempfile.gettempdir(), "cramm_rc_test.pdf")
    try:
        results = e.classify_spectrum(spec_full, WL, W, BP, CHANELS, top_n=2, pdf_path=pdf)
        assert len(results) > 0, "reference spectrum self-match should be non-empty"
        assert os.path.getsize(pdf) > 5000
    finally:
        if os.path.exists(pdf):
            os.remove(pdf)
    assert dict(mpl.rcParams) == before, "rcParams not restored"


# ----------------------------------------------------------------------------
# C. Integration section (needs EMIT NC)
# ----------------------------------------------------------------------------

def make_integration_tests(nc_path):
    def test_load_emit_contract():
        from cramm.emit_reader import EmitReader
        spectrum, lon, lat, w, bp, wl, chanels = EmitReader.load(nc_path)
        assert spectrum.ndim == 3 and spectrum.dtype == np.float32
        assert lon.shape == lat.shape == spectrum.shape[:2]
        assert len(chanels) < len(w) and len(wl) == len(chanels)
        assert _bytes(wl) == _bytes(w[chanels]), "wl and w[chanels] differ"
        assert (spectrum > -100).all(), "-9999 fill values should be zeroed (small negatives are normal noise)"
        assert spectrum.max() < 10, "reflectance should be within a reasonable magnitude"

    def test_real_pixel_classify():
        from cramm.emit_reader import EmitReader
        e = eng()
        spectrum, lon, lat, w, bp, wl, chanels = EmitReader.load(nc_path)
        r, c, _ = spectrum.shape
        res = e.classify_spectrum(spectrum[r // 2, c // 2, :], wl, w, bp, chanels, top_n=5)
        assert isinstance(res, list)
        for x in res:
            assert x["name"] in e.rf and x["fit"] > 0

    return [("integration: load_emit output contract", test_load_emit_contract),
            ("integration: real-pixel classify_spectrum", test_real_pixel_classify)]


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    import argparse
    ap = argparse.ArgumentParser(description="core package API contract + behavior tests")
    ap.add_argument("--nc", default=NC_DEFAULT, help="EMIT NetCDF path (integration section)")
    ap.add_argument("--golden", action="store_true", help="additionally run test_parallel.py 4/1 golden regression")
    args = ap.parse_args()

    print("== A. Algorithm units ==", flush=True)
    run("resample fast/slow path bit-exact", test_resample_fast_vs_slow)
    run("precompute consistency + rows contract", test_precompute_consistency)
    run("endpoint exception compile + instance freshness", test_endpoint_exc_compile_and_freshness)
    run("VNIR-only graceful degradation", test_vnir_only_graceful)

    print("== B. API contract / defense ==", flush=True)
    run("classify_spectrum shape validation", test_classify_spectrum_shape_validation)
    run("engine full-band == selected-band", test_engine_band_selection_equivalence)
    run("invalidate_caches", test_invalidate_caches)
    run("muscovite guard", test_muscovite_guard)
    run("render color table upfront validation", test_render_missing_color)
    run("specpr/splib validation", test_specpr_and_splib_validation)
    run("EmitReader non-EMIT error", test_emit_reader_non_emit_nc)
    run("PDF rcParams restoration", test_pdf_rcparams_restored)

    if os.path.exists(args.nc):
        print("== C. Integration (EMIT NC) ==", flush=True)
        for name, fn in make_integration_tests(args.nc):
            run(name, fn)
    else:
        print(f"== C. Integration section skipped ({args.nc} does not exist) ==")

    if args.golden:
        print("== D. golden regression (subprocess) ==", flush=True)
        for nw in ("4", "1"):
            print(f"-- test_parallel.py {nw} --", flush=True)
            p = subprocess.run([sys.executable, "-X", "utf8", "test_parallel.py", nw])
            RESULTS.append(("OK" if p.returncode == 0 else "FAIL", f"golden nw={nw}"))

    n_ok = sum(1 for s, _ in RESULTS if s == "OK")
    n_skip = sum(1 for s, _ in RESULTS if s == "SKIP")
    n_fail = sum(1 for s, _ in RESULTS if s == "FAIL")
    print(f"\nSummary: {n_ok} passed / {n_skip} skipped / {n_fail} failed")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
