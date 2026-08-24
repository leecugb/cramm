# -*- coding: utf-8 -*-
"""Save before/after classification index maps for arbitration comparison figures.

Two full-scene classifies (same protocol as arbitration_stats.py):
  A) production rf.json (all windows active) -> num_a
  B) all absorption_center_range stripped (pure argmax) -> num_b
Saves docs/figures/data/num_ab.npz with num_a, num_b, rule index list.
~2.5 min at n_workers=4.
"""
import copy
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cramm import MicaEngine

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
OUT = "docs/figures/data/num_ab.npz"


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    eng = MicaEngine()
    spectrum, lon, lat, w, bp, wl, chanels = eng.load_emit(NC)
    clf = eng._classifier

    t0 = time.time()
    res_a = clf.classify(spectrum, wl, w, bp, chanels, n_workers=4)
    print(f"[run A windowed] {time.time()-t0:.1f}s", flush=True)

    saved_rf = clf.rf
    stripped = copy.deepcopy(saved_rf)
    for rule in stripped.values():
        feats = rule.get("diagnostic_features") or []
        if feats:
            feats[0].pop("absorption_center_range", None)
    try:
        clf.rf = stripped
        clf.invalidate_caches()
        t0 = time.time()
        res_b = clf.classify(spectrum, wl, w, bp, chanels, n_workers=4)
        print(f"[run B pure argmax] {time.time()-t0:.1f}s", flush=True)
    finally:
        clf.rf = saved_rf
        clf.invalidate_caches()

    assert res_a.index == res_b.index
    flips = int((res_a.num != res_b.num).sum())
    print(f"total flips: {flips} (expect 62128)", flush=True)
    np.savez_compressed(
        OUT,
        num_a=res_a.num.reshape(res_a.r, res_a.c).astype(np.int32),
        num_b=res_b.num.reshape(res_b.r, res_b.c).astype(np.int32),
        mus_center_a=res_a.mus_center.reshape(res_a.r, res_a.c),
        index=np.array(res_a.index),
    )
    print(f"saved -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
