"""Empirical independence check: muscovite vs chlorite vs carbonate arbitration.

Since the family-lock change (2026-08-24) each
_reassign_by_absorption_center call builds its group ONLY from its own
family list (MUSCOVITE/CHLORITE/CARBONATE_MINERALS ∩ windowed rules), so
cross-family flips are structurally impossible. This script remains as
defense-in-depth evidence that the pre-lock assumptions also held
empirically:
    (a) family member lists are disjoint (code-level, checked separately),
    (b) no center ever reaches another family's windows:
    - mus winner with mus_center >= 2.244 would flip INTO a chlorite rule
    - chl winner with chl_center <  2.220 would flip INTO a muscovite rule
    - chl winner with chl_center >= 2.308 would touch a carbonate window
    - cal winner with cal_center <  2.266 would touch a chlorite window
      (cal winners can never flip: the calcite/dolomite duplicate windows
      make every in-window center ambiguous — zero-flip by construction)
Direct stale-center detectors for cross-family flips:
    mus->chl flip leaves num in chlorites with mus_center > 0, chl_center == 0
    chl->mus flip leaves num in muscovite-window rules with chl_center > 0
    chl->cal flip leaves num in carbonates with chl_center > 0, cal_center == 0
    cal->chl flip leaves num in chlorites with cal_center > 0
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "repo", "src"))
import numpy as np
from cramm.mica_engine import MicaEngine
from cramm.classifier import MUSCOVITE_MINERALS, CHLORITE_MINERALS, CARBONATE_MINERALS

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"


def main():
    eng = MicaEngine()
    spectrum, lon, lat, w, bp, wl, chanels = eng.load_emit(NC)
    t0 = time.time()
    res = eng._classifier.classify(spectrum, wl, w, bp, chanels,
                                   n_workers=int(sys.argv[1]) if len(sys.argv) > 1 else 2)
    print(f"[classify] {time.time()-t0:.1f}s", flush=True)

    rf = eng.rf
    mus_win = [n for n in MUSCOVITE_MINERALS
               if (rf[n]["diagnostic_features"][0].get("absorption_center_range"))]
    mus_idx = [res.index_d[n] for n in mus_win]
    chl_idx = [res.index_d[n] for n in CHLORITE_MINERALS]
    cal_idx = [res.index_d[n] for n in CARBONATE_MINERALS]

    is_mus = np.isin(res.num, mus_idx)
    is_chl = np.isin(res.num, chl_idx)
    is_cal = np.isin(res.num, cal_idx)
    print(f"muscovite-window-rule winners: {is_mus.sum()}   chlorite winners: {is_chl.sum()}   carbonate winners: {is_cal.sum()}")

    mc = res.mus_center[is_mus & (res.mus_center > 0)]
    print(f"mus_center on mus winners: n={len(mc)} min={mc.min():.5f} max={mc.max():.5f}")
    print(f"  >= 2.244 (would touch chlorite windows): {(mc >= 2.244).sum()}")
    print(f"  >= 2.220 (outside every mus window):     {(mc >= 2.220).sum()}")

    cc = res.chl_center[is_chl & (res.chl_center > 0)]
    print(f"chl_center on chl winners: n={len(cc)} min={cc.min():.5f} max={cc.max():.5f}")
    print(f"  < 2.220 (would touch muscovite windows): {(cc < 2.220).sum()}")
    print(f"  < 2.244 (below every chlorite window):   {(cc < 2.244).sum()}")
    print(f"  >= 2.308 (would touch carbonate windows): {(cc >= 2.308).sum()}")

    kc = res.cal_center[is_cal & (res.cal_center > 0)]
    print(f"cal_center on cal winners: n={len(kc)} min={kc.min():.5f} max={kc.max():.5f}")
    print(f"  < 2.266 (would touch chlorite windows): {(kc < 2.266).sum()}")
    print(f"  < 2.308 (below every carbonate window):   {(kc < 2.308).sum()}")

    x1 = is_chl & (res.mus_center > 0)
    x2 = is_mus & (res.chl_center > 0)
    x3 = is_cal & (res.chl_center > 0)
    x4 = is_chl & (res.cal_center > 0)
    x5 = is_cal & (res.mus_center > 0)
    x6 = is_mus & (res.cal_center > 0)
    print(f"cross-flip evidence mus->chl (chl winner, stale mus_center>0): {x1.sum()}")
    print(f"cross-flip evidence chl->mus (mus winner, stale chl_center>0): {x2.sum()}")
    print(f"cross-flip evidence chl->cal (cal winner, stale chl_center>0): {x3.sum()}")
    print(f"cross-flip evidence cal->chl (chl winner, stale cal_center>0): {x4.sum()}")
    print(f"cross-flip evidence mus->cal (cal winner, stale mus_center>0): {x5.sum()}")
    print(f"cross-flip evidence cal->mus (mus winner, stale cal_center>0): {x6.sum()}")

    # also: muscovite non-window members (illites, mixtures) must be untouched by design
    nonwin = [n for n in MUSCOVITE_MINERALS if n not in mus_win]
    print("mus family members without windows (never arbitrated):", nonwin)
    cal_win = [n for n in CARBONATE_MINERALS
               if (rf[n]["diagnostic_features"][0].get("absorption_center_range"))]
    print("cal family members with duplicate windows (never flip):", cal_win)
    print("cal family members without windows (never arbitrated):",
          [n for n in CARBONATE_MINERALS if n not in cal_win])


if __name__ == "__main__":
    main()
