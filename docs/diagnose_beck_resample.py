# -*- coding: utf-8 -*-
"""Diagnose the BECK empty-winner anomaly in the library validation.

Hypothesis: splib07a Beckman (W1R1B*) SWIR sampling is coarser than the EMIT
FWHM window, so the strict-FWHM Gaussian kernel (_resample_) leaves many EMIT
output bands with no in-window sample > 0 -> NaN -> 0. A resampled spectrum
riddled with zeros cannot produce the continuum-removed absorption features,
so no rule fires and classify_spectrum returns [].

Test: for same-sample BECK/NIC4 pairs (and the engine's own bundled reference
for a Beckman-based rule), resample and report zero-fraction + winner.
"""
import sys

import numpy as np

sys.path.insert(0, ".")
from cramm import MicaEngine
from cramm.classifier import _resample_
from usgs_splib import USGSLibrary

NC = "EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"


def resample_from_lib(lib, rec, w, bp):
    spec = lib.load(rec)
    bands = np.asarray(spec.wavelength, dtype="float64").copy()
    data = np.asarray(spec.reflectance, dtype="float64").copy()
    bad = (data < -1e34) | (bands <= 0) | (data <= 0)
    n_deleted = int(bad.sum())
    bands[bad] = 0.0
    data[bad] = 0.0
    res = _resample_(bands, data, w, bp)
    n_nan = int(np.isnan(res).sum())
    res[np.isnan(res)] = 0.0
    return res, bands, data, n_deleted, n_nan


def main():
    eng = MicaEngine()
    _, _, _, w, bp, wl, chanels = eng.load_emit(NC)
    lib = USGSLibrary()
    index = {}
    for r in lib.records:
        index.setdefault((r.name, r.sensor), r)

    # same-sample pairs across sensors
    pairs = [
        ("Clinochlore_GDS159", ["BECK", "NIC4"]),
        ("Cookeite_CAr-1.c_lt30um", ["BECK", "NIC4"]),
        ("Alunite_GDS82_Na82", ["BECK", "NIC4"]),
        ("Muscovite_GDS116", ["BECK", "NIC4"]),
        ("Kaolinite_KGa-1_(wxl)", ["BECK", "NIC4"]),
        ("Montmorillonite_SWy-1", ["BECK", "NIC4"]),
    ]

    print("=== same-sample cross-sensor zero-fraction ===")
    for name, sensors in pairs:
        for s in sensors:
            rec = index.get((name, s))
            if rec is None:
                print(f"  {name:32s} {s:5s}  (no record)")
                continue
            res, bands, data, n_del, n_nan = resample_from_lib(lib, rec, w, bp)
            valid_input = int((bands > 0).sum())
            # zero fraction over the EMIT *valid* channels only
            zf = float((res[chanels] == 0).mean())
            # SWIR region of interest 2.0-2.5 um
            swir = (w >= 2.0) & (w <= 2.5)
            zf_swir = float((res[swir & np.isin(np.arange(len(w)), chanels)] == 0).mean()) \
                if swir.any() else float("nan")
            top = eng.classify_spectrum(res, wl, w, bp, chanels, top_n=3)
            winner = top[0]["name"] if top else "(none)"
            print(f"  {name:32s} {s:5s}  in_valid={valid_input:4d} "
                  f"del={n_del:4d} nan_out={n_nan:3d} "
                  f"zero_frac_all={zf:.2f} zero_frac_swir={zf_swir:.2f} "
                  f"winner={winner}")

    # ------------------------------------------------ engine bundled reference
    print("\n=== engine bundled reference resample zero-fraction ===")
    refs = eng.get_resample(w, bp)  # dict recno -> resampled reference
    swir = (w >= 2.0) & (w <= 2.5)
    print(f"  type={type(refs).__name__}")
    if isinstance(refs, dict):
        items = list(refs.items())
    else:
        arr0 = np.asarray(refs)
        print(f"  shape={arr0.shape}")
        items = [(i, arr0[i]) for i in range(arr0.shape[0])]
    # Beckman-based rule references (splib06b record numbers from fig code)
    beck_recs = {2047: "chlorite_lowFe SMR-13.a", 1751: "calcite WS272",
                 2986: "dolomite HS102.3B", 8623: "siderite HS271.3B"}
    for recno, tag in beck_recs.items():
        arr = None
        if isinstance(refs, dict) and recno in refs:
            arr = np.asarray(refs[recno], dtype="float64")
        if arr is None:
            print(f"  rec {recno} {tag:28s}  (not a key in get_resample)")
            continue
        zf_all = float((arr[chanels] == 0).mean())
        zf_swir = float((arr[swir & np.isin(np.arange(len(w)), chanels)] == 0).mean())
        print(f"  rec {recno} {tag:28s}  zero_frac_all={zf_all:.2f} "
              f"zero_frac_swir={zf_swir:.2f}")
    # overall distribution across all references
    zs = []
    for recno, a in items:
        a = np.asarray(a, dtype="float64")
        if a.ndim == 1 and a.shape[0] == len(w):
            zs.append((recno, float((a[chanels] == 0).mean()),
                       float((a[swir & np.isin(np.arange(len(w)), chanels)] == 0).mean())))
    if zs:
        import statistics
        print(f"\n  all {len(zs)} references: "
              f"median zero_frac_all={statistics.median(z[1] for z in zs):.2f} "
              f"median zero_frac_swir={statistics.median(z[2] for z in zs):.2f}")
        worst = sorted(zs, key=lambda z: -z[2])[:8]
        print("  worst SWIR-zero references:")
        for recno, za, zw in worst:
            print(f"    rec {recno}: all={za:.2f} swir={zw:.2f}")


if __name__ == "__main__":
    main()
