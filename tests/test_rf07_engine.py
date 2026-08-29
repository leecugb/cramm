# -*- coding: utf-8 -*-
"""Stage-3 engine branch: rf_splib07.json + rf07_spectra.npz track.

    python tests/test_rf07_engine.py

Covers:
  1. v07 rule file loads with zero splib06b dependency; get_resample exposes
     53 physical ids + 19 mixture ids; every rule's reference resolves; the
     77 rule slots consume exactly 70 unique references (7 shared).
  2. Mixture synthesis is the same weighted sum of resampled endmembers as
     the legacy track (bit-exact recomputation).
  3. _resample_ fast path on the master grid (NaN-masked data) vs the slow
     boolean reference implementation: bit-exact.
  4. Serial vs parallel spectrum_analysis on a synthetic cube under the v07
     rule file: bit-exact five-layer outputs (same discipline as
     test_parallel.py, scene-independent).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA = os.path.join(os.path.dirname(__file__), "..", "cramm", "data")
RF07 = os.path.join(DATA, "rf_splib07.json")

W = np.linspace(0.381, 2.508, 285)
BP = np.full(285, 0.0074)
CHANELS = np.array([i for i in range(285) if not (126 <= i < 150 or 190 <= i < 210)])
WL = W[CHANELS]

_ENG = None


def eng07():
    global _ENG
    if _ENG is None:
        from cramm.mica_engine import MicaEngine
        _ENG = MicaEngine(rf_path=RF07)
    return _ENG


def _bytes(x):
    return np.ascontiguousarray(np.float64(x)).tobytes()


def test_load_and_resample_keys():
    e = eng07()
    clf = e._classifier
    assert len(clf.rf) == 77 and len(clf.mixtures) == 19
    resampled = clf.get_resample(W, BP)
    int_ids = {k for k in resampled if isinstance(k, int)}
    mix_ids = {k for k in resampled if not isinstance(k, int)}
    # three counting levels:
    #   53 physical records = 51 directly rule-referenced + 2 alias-only
    #     (GDS212/213, reached only through weight-1.0 mixtures)
    #   70 rule-facing unique references = 51 direct + 19 mixtures
    #   77 rule slots = 70 + 7 shared references (6 sharing groups)
    assert len(int_ids) == 53, f"expected 53 physical ids, got {len(int_ids)}"
    assert mix_ids == set(clf.mixtures), "mixture keys mismatch"
    # every rule reference resolves to a resampled spectrum
    rule_refs = set()
    for name, rule in clf.rf.items():
        rec = rule["reference"]["reflectance_record"]
        key = rec if isinstance(rec, int) else str(rec)
        assert key in resampled, f"{name}: reference {key} not resampled"
        rule_refs.add(key)
        arr = resampled[key][CHANELS]
        assert (~np.isnan(arr)).sum() > 100, f"{name}: reference nearly empty on valid bands"
    assert len(rule_refs) == 70, f"expected 70 rule-facing references, got {len(rule_refs)}"


def test_mixture_synthesis_bitexact():
    e = eng07()
    clf = e._classifier
    resampled = clf.get_resample(W, BP)
    for mix_id, components in clf.mixtures.items():
        expect = np.zeros_like(W, dtype="float64")
        for comp_id, weight in components.items():
            expect = expect + resampled[int(comp_id)] * weight
        assert _bytes(resampled[mix_id]) == _bytes(expect), f"{mix_id} synthesis differs"


def test_resample_fast_vs_slow_master_grid():
    from cramm.classifier import _resample_
    e = eng07()
    clf = e._classifier
    bands = clf.dic3.loc[-1, "data"]  # shared 1 nm master grid row
    for rid in (1751, 6348, 9412):  # BECK calcite / NIC4 muscovite / BECK topaz
        data = clf.dic3.loc[rid, "data"]
        fast = _resample_(bands, data, W, BP)
        res = []
        data64 = data.astype("double")
        for x, y in zip(W, BP):
            mask = (bands < x + y / 2) & (bands > x - y / 2)
            if not mask.any():
                res.append(np.nan)
                continue
            sigma = ((y / 2) ** 2 / np.log(2)) ** 0.5
            xx = bands[mask] - x
            wt = np.exp(-1 * xx**2 / sigma**2)
            temp = data64[mask]
            wt = wt[temp > 0]
            temp = temp[temp > 0]
            res.append((temp * wt).sum() / wt.sum() if len(temp) else np.nan)
        slow = np.array(res)
        assert (np.isnan(fast) == np.isnan(slow)).all(), f"rec {rid}: NaN positions differ"
        ok = ~np.isnan(fast)
        assert _bytes(fast[ok]) == _bytes(slow[ok]), f"rec {rid}: fast/slow values differ"


def _synthetic_cube(r=24, c=32):
    """Deterministic cube: mixtures of v07 references + noise, float32 like EMIT input."""
    e = eng07()
    resampled = e._classifier.get_resample(W, BP)
    ids = sorted(k for k in resampled if isinstance(k, int))
    rng = np.random.default_rng(11)
    base = np.zeros((r * c, len(W)))
    for i in range(r * c):
        a, b = ids[i % len(ids)], ids[(i * 7 + 3) % len(ids)]
        t = (i % 10) / 10.0
        base[i] = t * resampled[a] + (1 - t) * resampled[b]
    base += rng.normal(0, 0.002, base.shape)
    base[np.isnan(base)] = 0.0
    return np.maximum(base, 1e-4).astype("float32").reshape(r, c, len(W))


def test_serial_parallel_bitexact():
    e = eng07()
    cube = _synthetic_cube()
    out1 = e.spectrum_analysis(cube, WL, W, BP, CHANELS, n_workers=1)
    out4 = e.spectrum_analysis(cube, WL, W, BP, CHANELS, n_workers=4)
    names = ["orth_rgb", "color_enhanced", "mus_image", "chl_image", "cal_image"]
    for name, a, b in zip(names, out1, out4):
        assert np.array_equal(a, b), f"{name}: serial vs parallel differ"


if __name__ == "__main__":
    test_load_and_resample_keys()
    print("[ OK ] load_and_resample_keys")
    test_mixture_synthesis_bitexact()
    print("[ OK ] mixture_synthesis_bitexact")
    test_resample_fast_vs_slow_master_grid()
    print("[ OK ] resample_fast_vs_slow_master_grid")
    test_serial_parallel_bitexact()
    print("[ OK ] serial_parallel_bitexact")
    print("rf07 engine branch: OK")
