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

The unit section only needs the package-bundled 1nm rule library + spectra bundle (cramm/data/rf77_splib07_1nm.npz); no EMIT image needed.
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
        _ENG = MicaEngine()  # bundled 1nm rule library + spectra bundle
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
    rid = sorted(resampled1.keys())[5]
    rng = np.random.default_rng(7)
    spec = resampled1[rid] + rng.normal(0, 0.003, len(W))
    return np.maximum(spec, 1e-4), resampled1[rid]


# ----------------------------------------------------------------------------
# A. Algorithm units
# ----------------------------------------------------------------------------

def test_resample_fast_vs_slow():
    """_resample_ searchsorted fast path vs original boolean slow path, bit-exact (real 1nm record)."""
    from cramm.classifier import _resample_
    e = eng()
    # 1nm rule-face bundle: (grid, rule_names, rule_labels, spectra)
    grid, rule_names, _labels, spectra = e._classifier._1nm_bundle
    # pick a deterministic rule-name (4th in sorted order)
    rule_name = sorted(e.rf.keys())[3]
    name_to_row = {str(n): i for i, n in enumerate(rule_names)}
    row = name_to_row[rule_name]
    bands = np.asarray(grid, dtype="float64")
    data = np.asarray(spectra[row], dtype="float64")

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
    rid = sorted(resampled1.keys())[0]
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


def test_chlorite_window_arbitration():
    """Chlorite tiling-window arbitration: non-overlapping absorption_center_range
    windows (lowFe [2.245,2.248) / clinochlore [2.248,2.252) / Fe [2.252,2.256)
    / thuringite [2.256,2.266)).
    The four windows tile the 2.245-2.266 um range without overlap, so every
    in-range center hits exactly one window and arbitrates deterministically;
    only an invalid center or one outside every window keeps the match."""
    from cramm.classifier import _reassign_by_absorption_center, CHLORITE_MINERALS
    e = eng()
    rf = e.rf
    names = list(rf.keys())
    index_d = {n: i for i, n in enumerate(names)}
    i_low, i_clino, i_fe, i_thu = (index_d[n] for n in
                                   ("chlorite_lowFe", "clinochlore",
                                    "clinochlore_Fe", "thuringite"))
    # (winner, center) -> expected winner after arbitration
    cases = [
        (i_clino, 2.2522, i_fe),     # inside Fe window -> flip to Fe
        (i_clino, 2.2475, i_low),    # inside lowFe window -> flip to lowFe
        (i_fe,    2.2495, i_clino),  # inside clino window -> flip
        (i_fe,    2.2515, i_clino),  # inside clino window -> flip
        (i_low,   2.2460, i_low),    # inside own window -> keep
        (i_low,   2.2400, i_low),    # outside every window -> keep
        (i_clino, 0.0,    i_clino),  # invalid center -> keep
        (i_fe,    2.2600, i_thu),    # inside thuringite window -> flip
        (i_thu,   2.2535, i_fe),     # thuringite winner, center in Fe window -> flip
        (i_fe,    2.2552, i_fe),     # inside own window -> keep
        (i_thu,   2.2620, i_thu),    # inside own window -> keep
    ]
    n, m = len(cases), len(names)
    im = np.array([c[0] for c in cases], dtype="int64")
    cen = np.array([c[1] for c in cases], dtype="float64")
    FIT = np.full((n, m), 0.5)
    fit_nan = np.zeros((n, m), dtype=bool)
    fit_pos = np.ones(n, dtype=bool)
    # synthetic spectrum with a genuine 2250 nm dip so the post-flip refit
    # returns a valid center (value itself is not asserted)
    wl = np.linspace(2.0, 2.5, 50)
    spectrum1 = np.tile(0.5 - 0.2 * np.exp(-((wl - 2.25) / 0.02) ** 2), (n, 1))
    _reassign_by_absorption_center(im, FIT, fit_nan, cen, spectrum1, wl, rf, index_d, fit_pos,
                                   CHLORITE_MINERALS)
    for (winner, center, expected), got in zip(cases, im):
        assert got == expected, f"winner={names[winner]} center={center}: got {names[got]}, want {names[expected]}"
    assert (cen[cen > 0] > 2.2).all(), "kept/flipped centers must stay positive"


def test_carbonate_window_arbitration():
    """Carbonate per-tier pair arbitration (v1.5.0): the abundant pair
    (calcite_abundant vs dolomite_abundant) and the plain pair (calcite vs
    dolomite) each form their own arbitration group. Within a pair the
    windows are disjoint (dolomite [2.308,2.328), calcite [2.334,2.350)),
    so a center landing exclusively inside the OTHER tier-mate's window
    flips the attribution; the abundant/plain axis never flips because the
    two sub-family groups are disjoint (an abundant winner is not a member
    of the plain call and vice versa). Dead-zone / out-of-window / invalid
    centers keep the argmax winner, as do windowless members
    (carbonate_Fe_bearing, calcite.5+dolomite.5)."""
    from cramm.classifier import (_reassign_by_absorption_center,
                                  CARBONATE_ABUNDANT_MINERALS,
                                  CARBONATE_PLAIN_MINERALS)
    e = eng()
    rf = e.rf
    names = list(rf.keys())
    index_d = {n: i for i, n in enumerate(names)}
    i_cab, i_cal, i_dab, i_dol, i_fec, i_mix = (index_d[n] for n in (
        "calcite_abundant", "calcite", "dolomite_abundant", "dolomite",
        "carbonate_Fe_bearing", "calcite.5+dolomite.5"))
    m = len(names)
    # synthetic spectrum with a genuine 2330 nm dip (value itself not asserted)
    wl = np.linspace(2.0, 2.5, 50)

    def arb(rows, family):
        n = len(rows)
        im = np.array([r[0] for r in rows], dtype="int64")
        cen = np.array([r[1] for r in rows], dtype="float64")
        FIT = np.full((n, m), 0.5)
        fit_nan = np.zeros((n, m), dtype=bool)
        fit_pos = np.ones(n, dtype=bool)
        spectrum1 = np.tile(0.5 - 0.2 * np.exp(-((wl - 2.33) / 0.02) ** 2), (n, 1))
        _reassign_by_absorption_center(im, FIT, fit_nan, cen, spectrum1, wl,
                                       rf, index_d, fit_pos, family)
        return im

    # Plain pair: cross-window centers flip within the tier
    im = arb([(i_cal, 2.3200),   # calcite winner, center in dolomite window
              (i_dol, 2.3400),   # dolomite winner, center in calcite window
              (i_cal, 2.3310),   # dead zone between the windows -> keep
              (i_dol, 2.3600),   # outside every window -> keep
              (i_cal, 0.0),      # invalid center -> keep
              (i_cab, 2.3200),   # abundant winner: NOT a member of the
                                 # plain call -> tier axis never flips
              ], CARBONATE_PLAIN_MINERALS)
    assert im[0] == i_dol, "calcite winner with dolomite-window center must flip to dolomite"
    assert im[1] == i_cal, "dolomite winner with calcite-window center must flip to calcite"
    assert im[2] == i_cal and im[3] == i_dol and im[4] == i_cal, \
        "dead-zone / out-of-window / invalid centers must keep the winner"
    assert im[5] == i_cab, "abundant winner must ignore the plain pair (tier lock)"

    # Abundant pair: same semantics one tier up
    im = arb([(i_dab, 2.3400),   # dolomite_abundant winner, calcite window
              (i_cab, 2.3200),   # calcite_abundant winner, dolomite window
              (i_cal, 2.3200),   # plain winner: not a member -> keep
              (i_fec, 2.3350),   # windowless: not in any sub-family -> keep
              (i_mix, 2.3310),   # windowless blend, dead zone -> keep
              ], CARBONATE_ABUNDANT_MINERALS)
    assert im[0] == i_cab, "dolomite_abundant winner with calcite-window center must flip"
    assert im[1] == i_dab, "calcite_abundant winner with dolomite-window center must flip"
    assert im[2] == i_cal and im[3] == i_fec and im[4] == i_mix, \
        "plain/windowless winners must ignore the abundant pair"

    # Target-fit gate: a flip candidate whose target rejected it (fit NaN)
    # must keep its winner even with a uniquely-hit center
    im = np.array([i_cal], dtype="int64")
    cen = np.array([2.3200])
    FIT2 = np.full((1, m), 0.5)
    fit_nan2 = np.zeros((1, m), dtype=bool)
    fit_nan2[0, i_dol] = True
    spectrum1 = np.tile(0.5 - 0.2 * np.exp(-((wl - 2.33) / 0.02) ** 2), (1, 1))
    _reassign_by_absorption_center(im, FIT2, fit_nan2, cen, spectrum1, wl,
                                   rf, index_d, np.ones(1, dtype=bool),
                                   CARBONATE_PLAIN_MINERALS)
    assert im[0] == i_cal, "target fit NaN must block the flip"


def test_arbitration_family_lock():
    """The family argument locks the arbitration group structurally: a
    winner can only ever be reassigned among its own family's rules, no
    matter where its center lands. A chlorite winner whose center falls
    inside a MUSCOVITE window (2.2 um) must keep its match (and vice
    versa) — cross-family flips are impossible by construction, not by
    window-spacing luck."""
    from cramm.classifier import (_reassign_by_absorption_center,
                                  CHLORITE_MINERALS, MUSCOVITE_MINERALS)
    e = eng()
    rf = e.rf
    names = list(rf.keys())
    index_d = {n: i for i, n in enumerate(names)}
    i_clino, i_fe = index_d["clinochlore"], index_d["clinochlore_Fe"]
    i_medal, i_lowal = index_d["muscovite_medAl"], index_d["muscovite_lowAl"]
    n, m = 2, len(names)
    FIT = np.full((n, m), 0.5)
    fit_nan = np.zeros((n, m), dtype=bool)
    fit_pos = np.ones(n, dtype=bool)
    wl = np.linspace(2.0, 2.5, 50)
    spectrum1 = np.tile(0.5 - 0.2 * np.exp(-((wl - 2.25) / 0.02) ** 2), (n, 1))

    # Chlorite call: centers inside muscovite-only territory must not flip
    im = np.array([i_clino, i_fe], dtype="int64")
    cen = np.array([2.2005, 2.2080])  # medAl-only and lowAl-only windows
    _reassign_by_absorption_center(im, FIT, fit_nan, cen, spectrum1, wl, rf,
                                   index_d, fit_pos, CHLORITE_MINERALS)
    assert im[0] == i_clino and im[1] == i_fe, (
        "chlorite winners must ignore muscovite windows (family lock)")

    # Muscovite call: centers inside chlorite-only territory must not flip
    im = np.array([i_medal, i_lowal], dtype="int64")
    cen = np.array([2.2490, 2.2600])  # clinochlore-only and thuringite-only
    _reassign_by_absorption_center(im, FIT, fit_nan, cen, spectrum1, wl, rf,
                                   index_d, fit_pos, MUSCOVITE_MINERALS)
    assert im[0] == i_medal and im[1] == i_lowal, (
        "muscovite winners must ignore chlorite windows (family lock)")


def test_render_missing_color():
    """Color table missing a mineral name: render raises KeyError up front (rather than a bare KeyError at lookup)."""
    from cramm.classifier import ClassificationResult
    from cramm.renderer import ResultRenderer
    renderer = ResultRenderer.from_paths()
    bogus = ClassificationResult(
        fit=np.array([1.0]), depth=np.array([0.5]), num=np.zeros(1, dtype="uint8"),
        mus_center=np.zeros(1), chl_center=np.zeros(1), cal_center=np.zeros(1), r=1, c=1,
        index=["no_such_mineral"], index_d={"no_such_mineral": 0},
    )
    try:
        renderer.render(bogus)
        raise AssertionError("should raise KeyError")
    except KeyError as e:
        assert "color table is missing" in str(e) and "no_such_mineral" in str(e)


def test_splib_validation():
    """Nonexistent splib path -> FileNotFoundError."""
    from cramm.classifier import MicaClassifier
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


def test_emit_reader_shape_validation():
    """EMIT-structured but geometrically inconsistent NetCDF -> clear ValueError."""
    try:
        import netCDF4 as nc
    except ImportError:
        raise SkipTest("netCDF4 not available")
    from cramm.emit_reader import EmitReader

    # case 1: reflectance not 3-D
    path = os.path.join(tempfile.gettempdir(), "cramm_bad_shape1.nc")
    try:
        with nc.Dataset(path, "w") as ds:
            ds.createDimension("r", 3)
            ds.createDimension("c", 5)
            ds.createDimension("b", 4)
            loc = ds.createGroup("location")
            loc.createVariable("lon", "f8", ("r", "c"))[:] = 0.0
            loc.createVariable("lat", "f8", ("r", "c"))[:] = 0.0
            ds.createVariable("reflectance", "f4", ("r", "c"))[:] = 0.5
            sbp = ds.createGroup("sensor_band_parameters")
            sbp.createVariable("wavelengths", "f4", ("b",))[:] = np.arange(400, 404)
            sbp.createVariable("fwhm", "f4", ("b",))[:] = 7.4
        try:
            EmitReader.load(path)
            raise AssertionError("should raise ValueError")
        except ValueError as e:
            assert "3-D" in str(e)
    finally:
        if os.path.exists(path):
            os.remove(path)

    # case 2: band axis longer than wavelengths
    path = os.path.join(tempfile.gettempdir(), "cramm_bad_shape2.nc")
    try:
        with nc.Dataset(path, "w") as ds:
            ds.createDimension("r", 3)
            ds.createDimension("c", 5)
            ds.createDimension("b", 4)
            ds.createDimension("b6", 6)
            loc = ds.createGroup("location")
            loc.createVariable("lon", "f8", ("r", "c"))[:] = 0.0
            loc.createVariable("lat", "f8", ("r", "c"))[:] = 0.0
            ds.createVariable("reflectance", "f4", ("r", "c", "b6"))[:] = 0.5
            sbp = ds.createGroup("sensor_band_parameters")
            sbp.createVariable("wavelengths", "f4", ("b",))[:] = np.arange(400, 404)
            sbp.createVariable("fwhm", "f4", ("b",))[:] = 7.4
        try:
            EmitReader.load(path)
            raise AssertionError("should raise ValueError")
        except ValueError as e:
            assert "band axis mismatch" in str(e)
    finally:
        if os.path.exists(path):
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


def test_classify_spectrum_dtype_uniformity():
    """Facade dtype contract: the same float32 spectrum passed as 1-D vs 2-D gives identical results."""
    e = eng()
    spec_full, _ = ref_spectrum()
    spec32 = spec_full[CHANELS].astype("float32")
    r_1d = e.classify_spectrum(spec32, WL, W, BP, CHANELS, top_n=len(e.rf))
    r_2d = e.classify_spectrum(spec32.reshape(1, -1), WL, W, BP, CHANELS, top_n=len(e.rf))
    assert [x["name"] for x in r_1d] == [x["name"] for x in r_2d], "Top-N name lists differ"
    for a, b in zip(r_1d, r_2d):
        assert _bytes(a["fit"]) == _bytes(b["fit"]) and _bytes(a["fd"]) == _bytes(b["fd"])


def test_color_tif_sampling_and_validation():
    """Custom color LUT GeoTIFF: 10 columns sampled evenly across the actual width;
    single-band tif raises a clear ValueError (not a bare IndexError)."""
    try:
        from osgeo import gdal
    except ImportError:
        raise SkipTest("gdal not available")
    from cramm.renderer import ResultRenderer
    tmp = tempfile.mkdtemp(prefix="cramm_lut_")
    try:
        # heritage width 283: sampling must equal the original linspace(0, 282, 10) positions
        width = 283
        arr = np.zeros((3, 1, width), dtype="uint8")
        arr[0, 0, :] = np.arange(width) % 256
        arr[1, 0, :] = (np.arange(width) * 2) % 256
        arr[2, 0, :] = (np.arange(width) * 3) % 256
        path = os.path.join(tmp, "lut.tif")
        ds = gdal.GetDriverByName("GTiff").Create(path, width, 1, 3, gdal.GDT_Byte)
        for i in range(3):
            ds.GetRasterBand(i + 1).WriteArray(arr[i])
        ds = None
        renderer = ResultRenderer.from_paths(color_tif_path=path)
        indices = np.linspace(0, width - 1, 10).astype(int)
        assert len(renderer.table) == 10
        for k, idx in enumerate(indices):
            assert np.array_equal(renderer.table[k], arr[:, 0, idx]), f"sample {k} mismatch at column {idx}"
        # single-band tif -> clear ValueError
        bad = os.path.join(tmp, "lut_1band.tif")
        ds = gdal.GetDriverByName("GTiff").Create(bad, width, 1, 1, gdal.GDT_Byte)
        ds.GetRasterBand(1).WriteArray(arr[0])
        ds = None
        try:
            ResultRenderer.from_paths(color_tif_path=bad)
            raise AssertionError("single-band LUT should raise ValueError")
        except ValueError as e:
            assert "3-band" in str(e)
    finally:
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)


def test_write_tiff_antimeridian_guard():
    """write_tiff: scene crossing the antimeridian raises a clear ValueError instead of
    building a ~360-degree raster (no output files written)."""
    try:
        from osgeo import gdal  # noqa: F401
    except ImportError:
        raise SkipTest("gdal not available")
    from cramm.renderer import ResultRenderer
    r, c = 4, 5
    lon = np.linspace(179.0, 181.0, r * c).reshape(r, c)
    lon[lon > 180] -= 360  # EMIT [-180, 180] convention -> now straddles the antimeridian
    lat = np.linspace(30.0, 31.0, r * c).reshape(r, c)
    img = np.zeros((r, c, 3), dtype="uint8")
    tmp = tempfile.mkdtemp(prefix="cramm_antim_")
    try:
        try:
            ResultRenderer.write_tiff(os.path.join(tmp, "scene"), lon, lat, img, img, img)
            raise AssertionError("antimeridian-crossing scene should raise ValueError")
        except ValueError as e:
            assert "antimeridian" in str(e)
        assert os.listdir(tmp) == [], "no output files should be written"
    finally:
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)


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

    def test_chl_center_product():
        """Chlorite product line: chl_center contract on a chlorite-rich tile
        (rows 440:540, cols 160:260 of the EMIT test scene — 3109 chlorite
        pixels in the golden baseline)."""
        from cramm.emit_reader import EmitReader
        e = eng()
        spectrum, lon, lat, w, bp, wl, chanels = EmitReader.load(nc_path)
        tile = spectrum[440:540, 160:260]

        # 1) classify-level contract: chl_center > 0 exactly on chlorite winners
        # (chl_idx mirrors CHLORITE_MINERALS, incl. thuringite since it joined
        # the center-fit family with its [2.256, 2.266) window)
        from cramm.classifier import CHLORITE_MINERALS
        res = e._classifier.classify(tile, wl, w, bp, chanels, n_workers=1)
        chl_idx = [res.index_d[n] for n in CHLORITE_MINERALS if n in res.index_d]
        winner = np.isin(res.num, chl_idx) & (res.fit > 0)
        assert winner.sum() > 1000, "tile should be chlorite-rich"
        has_center = res.chl_center > 0
        assert (has_center <= winner).all(), "center without a chlorite win"
        assert (winner == has_center).mean() > 0.999, "winners should all get a center"
        vals = res.chl_center[has_center]
        assert (vals > 2.23).all() and (vals < 2.27).all(), "center out of 2250nm band range"

        # 2) facade-level contract: raw=True returns 9 arrays, renderer colors
        # exactly the in-range pixels
        out = e.spectrum_analysis(tile, wl, w, bp, chanels, n_workers=1, raw=True)
        assert len(out) == 9
        orth, color, mus, chl, cal, mus_center, chl_center2, cal_center, fd = out
        assert chl.shape == (100, 100, 3) and chl_center2.shape == (100, 100)
        colored = chl.any(axis=2)
        inrange = (chl_center2 >= 2.244) & (chl_center2 < 2.259)
        assert (colored == inrange).all(), "chl_image bins must match the [2.244, 2.259) contract"

    def test_cal_center_product():
        """Carbonate product line: cal_center contract on a carbonate-rich tile
        (rows 950:1050, cols 950:1050 of the EMIT test scene — 5421 carbonate
        pixels, centers spanning both the dolomite and calcite windows)."""
        from cramm.emit_reader import EmitReader
        e = eng()
        spectrum, lon, lat, w, bp, wl, chanels = EmitReader.load(nc_path)
        tile = spectrum[950:1050, 950:1050]

        # 1) classify-level contract: cal_center > 0 exactly on carbonate winners
        # (cal_idx mirrors CARBONATE_MINERALS, incl. the windowless mixture
        # calcite.5+dolomite.5, which takes part in the center fit)
        from cramm.classifier import CARBONATE_MINERALS
        res = e._classifier.classify(tile, wl, w, bp, chanels, n_workers=1)
        cal_idx = [res.index_d[n] for n in CARBONATE_MINERALS if n in res.index_d]
        winner = np.isin(res.num, cal_idx) & (res.fit > 0)
        assert winner.sum() > 4000, "tile should be carbonate-rich"
        has_center = res.cal_center > 0
        assert (has_center <= winner).all(), "center without a carbonate win"
        assert (winner == has_center).mean() > 0.999, "winners should all get a center"
        vals = res.cal_center[has_center]
        assert (vals > 2.27).all() and (vals < 2.40).all(), "center out of 2330nm band range"

        # 2) facade-level contract: renderer colors exactly the in-range pixels
        out = e.spectrum_analysis(tile, wl, w, bp, chanels, n_workers=1, raw=True)
        assert len(out) == 9
        orth, color, mus, chl, cal, mus_center, chl_center, cal_center2, fd = out
        assert cal.shape == (100, 100, 3) and cal_center2.shape == (100, 100)
        colored = cal.any(axis=2)
        inrange = (cal_center2 >= 2.308) & (cal_center2 < 2.358)
        assert (colored == inrange).all(), "cal_image bins must match the [2.308, 2.358) contract"

    return [("integration: load_emit output contract", test_load_emit_contract),
            ("integration: real-pixel classify_spectrum", test_real_pixel_classify),
            ("integration: chl_center product line", test_chl_center_product),
            ("integration: cal_center product line", test_cal_center_product)]


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
    run("chlorite tiling-window arbitration", test_chlorite_window_arbitration)
    run("render color table upfront validation", test_render_missing_color)
    run("splib validation", test_splib_validation)
    run("EmitReader non-EMIT error", test_emit_reader_non_emit_nc)
    run("EmitReader shape validation", test_emit_reader_shape_validation)
    run("PDF rcParams restoration", test_pdf_rcparams_restored)
    run("classify_spectrum dtype uniformity (1-D vs 2-D)", test_classify_spectrum_dtype_uniformity)
    run("color LUT tif sampling + validation", test_color_tif_sampling_and_validation)
    run("write_tiff antimeridian guard", test_write_tiff_antimeridian_guard)

    if os.path.exists(args.nc):
        print("== C. Integration (EMIT NC) ==", flush=True)
        for name, fn in make_integration_tests(args.nc):
            run(name, fn)
    else:
        print(f"== C. Integration section skipped ({args.nc} does not exist) ==")

    if args.golden:
        print("== D. golden regression (subprocess) ==", flush=True)
        tp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_parallel.py")
        for nw in ("4", "1"):
            print(f"-- test_parallel.py {nw} --", flush=True)
            p = subprocess.run([sys.executable, "-X", "utf8", tp, nw])
            RESULTS.append(("OK" if p.returncode == 0 else "FAIL", f"golden nw={nw}"))

    n_ok = sum(1 for s, _ in RESULTS if s == "OK")
    n_skip = sum(1 for s, _ in RESULTS if s == "SKIP")
    n_fail = sum(1 for s, _ in RESULTS if s == "FAIL")
    print(f"\nSummary: {n_ok} passed / {n_skip} skipped / {n_fail} failed")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
