# -*- coding: utf-8 -*-
"""Pin down exactly which constraint knocks the Na-alunites out of the
alunite rules, by calling the classifier's own _diagnostic_feature.

The MICA 'fit' is R^2 of the least-squares fit between the sample's and the
reference's continuum-removed feature. Each alunite rule has:
  feature 1 (weight 0, fit_constraint 0.65): 1.44-1.55 um gate -- must pass
  feature 2 (weight 1)                       : 2.02-2.27 um Al-OH -- scored
Rule fires iff  gate R2 >= 0.65  AND  weighted-fit (== feature2 R2) >= 0.64.

We read the RAW R2 of each feature (FEATURE_WEIGHT=1, FIT_CONSTRAINTS=None).
"""
import sys

import numpy as np

sys.path.insert(0, ".")
from cramm import MicaEngine
from cramm.classifier import _diagnostic_feature, _resample_
from usgs_splib import USGSLibrary

NC = "EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
RULES = {"alunite_K_250C": 596, "alunite_Na_450C": 655}
SAMPLES = [
    ("Alunite_GDS82_Na82", "NIC4"),
    ("Alunite_GDS83_Na63", "NIC4"),
    ("Alunite_GDS84_Na03", "NIC4"),
    ("Alunite_RES-9_Summitv_(400C)", "ASDNG"),
    ("Alunite_RES-9_Summitv_(400C)", "NIC4"),
    ("Alunite_RES10_NA56%_Syn_450C", "NIC4"),
]


def resample_lib(lib, rec, w, bp):
    spec = lib.load(rec)
    b = np.asarray(spec.wavelength, float).copy()
    d = np.asarray(spec.reflectance, float).copy()
    bad = (d < -1e34) | (b <= 0) | (d <= 0)
    b[bad] = 0.0
    d[bad] = 0.0
    r = _resample_(b, d, w, bp)
    r[np.isnan(r)] = 0.0
    return r


def feat_r2(spec2d, refspec, wl, feat):
    """Raw R2 of one diagnostic feature (no fit gating, weight=1)."""
    cc = feat["continuum_constraints"]
    cc_list = [cc["left_min"], cc["left_max"], cc["mean_min"], cc["mean_max"],
               cc["right_min"], cc["right_max"], cc["ratio_min"], cc["ratio_max"]]
    r2w, _, _, _ = _diagnostic_feature(
        spec2d, refspec, wl, feat["continuum_endpoints"], 1.0,
        CONTINUUM_CONSTRAINTS=cc_list, FIT_CONSTRAINTS=None,
        DEPTH_CONSTRAINTS=[None, None])
    return float(r2w[0])


def main():
    eng = MicaEngine()
    _, _, _, w, bp, wl, chanels = eng.load_emit(NC)
    refs = eng.get_resample(w, bp)
    rf = eng.rf  # 1nm rule library loaded by the engine

    lib = USGSLibrary()
    index = {}
    for r in lib.records:
        index.setdefault((r.name, r.sensor), r)

    for rule, recno in RULES.items():
        feats = rf[rule]["diagnostic_features"]
        refspec = np.asarray(refs[recno] if recno in refs else refs[str(recno)], float)
        refspec = refspec[chanels]  # reduce 285 -> 244 valid channels (match wl)
        print(f"\n=== {rule} (ref rec {recno}) ===")
        print(f"  gate f1 endpts={feats[0]['continuum_endpoints']} "
              f"fit_constraint={feats[0]['fit_constraint']}")
        print(f"  score f2 endpts={feats[1]['continuum_endpoints']}")
        print(f"  {'sample':30s} {'gateR2(>=0.65)':>14s} {'scoreR2(>=0.64)':>16s}")
        # reference self-check
        r2g = feat_r2(refspec[np.newaxis, :], refspec, wl, feats[0])
        r2s = feat_r2(refspec[np.newaxis, :], refspec, wl, feats[1])
        print(f"  {'(reference self)':30s} {r2g:14.3f} {r2s:16.3f}")
        for name, sensor in SAMPLES:
            rec = index.get((name, sensor))
            if rec is None:
                continue
            s = resample_lib(lib, rec, w, bp)[chanels][np.newaxis, :]
            r2g = feat_r2(s, refspec, wl, feats[0])
            r2s = feat_r2(s, refspec, wl, feats[1])
            gate = "PASS" if r2g >= 0.65 else "FAIL"
            scr = "PASS" if r2s >= 0.64 else "FAIL"
            print(f"  {name[:26]+' '+sensor:30s} {r2g:7.3f} {gate:>6s} "
                  f"{r2s:9.3f} {scr:>6s}")


if __name__ == "__main__":
    main()
