# -*- coding: utf-8 -*-
"""Stage-2 export integrity: cramm/data/rf07_spectra.npz vs splib07 sources.

Every baked record must be bit-exact equal to a fresh piecewise-linear
interpolation of the source record's valid samples onto the master grid, with
NaN strictly outside the native valid range. Skipped when the splib07 library
is not available on this machine (the npz itself ships with the repo; the
1.5 GB library does not).
"""
import json
import os

import numpy as np

NPZ = os.path.join(os.path.dirname(__file__), "..", "cramm", "data", "rf07_spectra.npz")
SELECTION = os.path.join(os.path.dirname(__file__), "..", "docs", "splib07_selection.json")
SPLIB07 = r"D:\usgs_splib07"


def _load_npz():
    z = np.load(NPZ, allow_pickle=False)
    return z["grid"], list(z["keys"]), z["spectra"], json.loads(str(z["meta"][0]))


def test_npz_structure():
    grid, keys, spectra, meta = _load_npz()
    assert grid.shape == (2151,)
    np.testing.assert_allclose(grid, np.arange(0.35, 2.5 + 5e-4, 0.001), rtol=0, atol=1e-12)
    assert spectra.shape == (len(keys), 2151)
    assert len(set(keys)) == len(keys) == 58
    assert len(meta) == len(keys)
    # selection table (references + AMX aliases) and npz must cover exactly
    # the same records
    sel = json.load(open(SELECTION, encoding="utf-8"))
    sel_keys = {s["splib07_record"] for s in sel["references"].values()}
    amx_keys = {a["amx_record"] for a in sel["amx_mixture_aliases"]}
    assert set(keys) == sel_keys | amx_keys


def test_baked_matches_source_bitexact():
    if not os.path.isdir(SPLIB07):
        return  # library not on this machine; structure test above still ran
    from usgs_splib import USGSLibrary

    lib = USGSLibrary(SPLIB07)
    by_key = {f"{r.name}_{r.sensor}{r.quality}_{r.mtype}": r for r in lib.records}
    grid, keys, spectra, _ = _load_npz()
    for i, key in enumerate(keys):
        spec = lib.load(by_key[key])
        wl = np.asarray(spec.wavelength, dtype="float64")
        sp = np.asarray(spec.reflectance, dtype="float64")
        o = np.argsort(wl)
        wl, sp = wl[o], sp[o]
        k = (wl > 0) & (sp > 0) & (sp < 1e34)
        wl, sp = wl[k], sp[k]
        expect = np.full(len(grid), np.nan)
        m = (grid >= wl[0]) & (grid <= wl[-1])
        expect[m] = np.interp(grid[m], wl, sp)
        np.testing.assert_array_equal(spectra[i], expect)  # NaN==NaN, bit-exact
        # NaN strictly outside the native valid range
        assert not np.isnan(spectra[i][m]).any()
        assert np.isnan(spectra[i][~m]).all()


if __name__ == "__main__":
    test_npz_structure()
    test_baked_matches_source_bitexact()
    print("rf07 export integrity: OK")
