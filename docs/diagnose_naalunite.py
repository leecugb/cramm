# -*- coding: utf-8 -*-
"""Why do the Na-alunites classify as pyrophyllite.25+kaolinite.75?

Two questions:
  A. Do the alunite rules FIRE for these samples at all (appear in Top-77),
     or does the 1.44-1.55 um gating feature knock them out before ranking?
  B. What does the 2.0-2.4 um Al-OH region look like vs the references
     (K-alunite 596, Na-alunite 655, pyrophyllite 7893, kaolinite 5088)?

Context from rf.json:
  alunite_K_250C / alunite_Na_450C : STRICT, gated. Feature 1 (weight 0,
      fit_constraint 0.65) spans 1.44-1.55 um; feature 2 (weight 1) spans
      2.02-2.27 um. Both must match the specific reference.
  pyrophyllite (7893) / pyrophyllite.25+kaolinite.75 (mix_7737) : LOOSE,
      single feature 2.09-2.255 um, depth>=0.03, NO gate, NO not-features.
"""
import sys

import numpy as np

sys.path.insert(0, "repo/src")
from cramm import MicaEngine
from cramm.classifier import _resample_
from usgs_splib import USGSLibrary

NC = "EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"

REFS = {"alunite_K_250C": 596, "alunite_Na_450C": 655,
        "pyrophyllite": 7893, "kaolinite_wxl": 5088}
WATCH = ["alunite_K_250C", "alunite_Na_450C", "pyrophyllite",
         "pyrophyllite.25+kaolinite.75"]

SAMPLES = [  # the genuine Na-alunite misses (NIC4 / ASDNG strata)
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


def continuum_min(w, s, lo, hi, search_lo, search_hi):
    """Linear continuum removal over [lo,hi]; return min position in search."""
    m = (w >= lo) & (w <= hi) & (s > 0)
    if m.sum() < 3:
        return float("nan"), float("nan")
    ww, ss = w[m], s[m]
    cont = ss[0] + (ss[-1] - ss[0]) * (ww - ww[0]) / (ww[-1] - ww[0])
    cr = ss / np.where(cont == 0, np.nan, cont)
    sm = (ww >= search_lo) & (ww <= search_hi)
    if sm.sum() == 0:
        return float("nan"), float("nan")
    i = np.flatnonzero(sm)[np.argmin(cr[sm])]
    return ww[i], cr[i]


def main():
    eng = MicaEngine()
    _, _, _, w, bp, wl, chanels = eng.load_emit(NC)
    refs = eng.get_resample(w, bp)
    refs = {k: np.asarray(v, float) for k, v in refs.items()}
    # mixture reference is keyed 'mix_7737'; map friendly names -> spectrum
    def ref(name):
        return refs[str(REFS[name])] if str(REFS[name]) in refs else refs[REFS[name]]
    mix = refs["mix_7737"]  # pyrophyllite.25+kaolinite.75 (actual engine ref)

    lib = USGSLibrary()
    index = {}
    for r in lib.records:
        index.setdefault((r.name, r.sensor), r)

    print("=== A. do the alunite rules FIRE? (rank:fit in Top-77) ===")
    hdr = f"  {'sample':34s} {'sensor':6s} " + " ".join(
        f"{c[:14]:>15s}" for c in ["alun_K", "alun_Na", "pyro", "pyr.25+ka.75"])
    print(hdr)
    for name, sensor in SAMPLES:
        rec = index.get((name, sensor))
        if rec is None:
            print(f"  {name:34s} {sensor:6s}  (no record)")
            continue
        res = resample_lib(lib, rec, w, bp)
        top = eng.classify_spectrum(res, wl, w, bp, chanels, top_n=77)
        pos = {t["name"]: (rk, t["fit"]) for rk, t in enumerate(top, 1)}
        cells = []
        for cname in WATCH:
            if cname in pos:
                rk, ft = pos[cname]
                cells.append(f"r{rk:<2d}:{ft:0.3f}")
            else:
                cells.append("-- (no fire)")
        print(f"  {name:34s} {sensor:6s} " + " ".join(f"{c:>15s}" for c in cells))

    print("\n=== B. 2.0-2.4 um band minima (continuum-removed) ===")
    print("  (alunite K ref~2.175um singlet + 2.32um SO4; kaolinite 2.16/2.21 doublet)")
    rows = [("REF alunite_K_250C(596)", ref("alunite_K_250C")),
            ("REF alunite_Na_450C(655)", ref("alunite_Na_450C")),
            ("REF pyrophyllite(7893)", ref("pyrophyllite")),
            ("REF kaolinite_wxl(5088)", ref("kaolinite_wxl")),
            ("REF mix_7737 pyr.25+ka.75", mix)]
    for name, sensor in SAMPLES:
        rec = index.get((name, sensor))
        if rec is not None:
            rows.append((f"SMP {name[:26]} {sensor}", resample_lib(lib, rec, w, bp)))
    for label, s in rows:
        c1, d1 = continuum_min(w, s, 2.0, 2.4, 2.12, 2.22)   # main Al-OH
        c2, d2 = continuum_min(w, s, 2.0, 2.4, 2.28, 2.38)   # 2.32 SO4 / 2.29 region
        print(f"  {label:30s} main={c1:.4f}um(d={d1:.3f})  "
              f"2.3x={c2:.4f}um(d={d2:.3f})")

    print("\n=== C. 1.4-1.6 um gating region (alunite rule feature 1) ===")
    for label, s in rows:
        c1, d1 = continuum_min(w, s, 1.38, 1.62, 1.40, 1.60)
        print(f"  {label:30s} min={c1:.4f}um(depth={d1:.3f})")


if __name__ == "__main__":
    main()
