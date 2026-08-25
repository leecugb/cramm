"""Re-baseline tests/golden_arrays.npz after an INTENDED classification change.

Runs the full scene once (n_workers=4; serial/parallel are bit-exact by the
isolation tests), audits every differing pixel against the old baseline to
confirm the change is confined to the intended mechanism, then atomically
replaces the golden file. Audit failures abort before anything is written.

Current audit (BLAS-free k-solve in _fit_r2_depth, 2026-08): B.dot(con.T)
went through BLAS dgemm, whose kernel/blocking selection varies with the row
count m and the thread pool (MKL2025: kernel switch below m~150, reblocking
under multithreading), so identical pixels could receive ulp-different k0/k1
in subset vs full calls -- silently breaking the documented bit-exactness of
the alive-pixel restriction and of the serial vs parallel paths. The solve is
now np.einsum("mj,kj->mk") (pure C loop, no BLAS): per-pixel results depend
only on the pixel's own row. This changes FIT/fd VALUES at the ulp level
scene-wide, but cannot change any verdict except where the old value sat
within ulps of a decision boundary (argmax tie / fit tier edge).
Expected array impact:
  - orth_rgb / mus_image / chl_image / cal_image: BIT-IDENTICAL (reflectance
    rendering, argmax verdicts, and the BLAS-free quadratic center fits have
    no mechanism to move; a diff here means a verdict flipped -> investigate)
  - color_enhanced: may differ ONLY at pixels whose old fit sat within ulps
    of a renderer fit-tier boundary -- expected count ~0, hard cap 100
Observed at the 2026-08 rebaseline: color_enhanced 6 diff pixels, all other
arrays bit-identical.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from cramm.mica_engine import MicaEngine

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_arrays.npz")


def main():
    eng = MicaEngine()
    spectrum, lon, lat, w, bp, wl, chanels = eng.load_emit(NC)
    t0 = time.time()
    orth, color, mus, chl, cal = eng.spectrum_analysis(
        spectrum, wl, w, bp, chanels, n_workers=4,
        progress_callback=lambda p: print(f"  progress {p}% @ {time.time()-t0:.1f}s", flush=True),
    )

    with np.load(GOLDEN) as z:  # eager load + close: Windows cannot replace an open file
        g = {k: z[k] for k in z.files}

    # 1) identity audit: arrays with no mechanism to change must be bit-identical
    #    (a k-solve-order change moves values by ulps only; a verdict-level diff
    #    -- argmax tie flip reaching a rendered map -- must be inspected by hand)
    for name, arr in [("orth_rgb", orth), ("mus_image", mus), ("chl_image", chl), ("cal_image", cal)]:
        same = np.array_equal(arr, g[name])
        print(f"{name:16s} bit-identical: {same}")
        assert same, (f"{name} changed -- aborting: an ulp-level k-solve change "
                      "cannot touch this array unless a verdict flipped; investigate the diff first")

    # 2) boundary audit: color_enhanced (fit-tiered) may differ only at pixels
    #    whose old fit sat within ulps of a tier boundary -- expected ~0, cap 100
    diff = np.any(color != g["color_enhanced"], axis=2)
    n_diff = int(diff.sum())
    print(f"color_enhanced diff pixels: {n_diff}")
    if n_diff:
        ys, xs = np.nonzero(diff)
        for y, x in list(zip(ys, xs))[:20]:
            print(f"    ({y},{x}): {g['color_enhanced'][y, x].tolist()} -> {color[y, x].tolist()}")
    assert n_diff < 100, (f"color_enhanced: {n_diff} diff pixels -- far above the ulp-boundary "
                          "scale; investigate before re-baselining")

    # 3) write new baseline
    tmp = GOLDEN.replace("golden_arrays.npz", "golden_arrays_tmp.npz")  # savez requires .npz suffix
    np.savez_compressed(tmp, orth_rgb=orth, color_enhanced=color, mus_image=mus,
                        chl_image=chl, cal_image=cal)
    os.replace(tmp, GOLDEN)
    print(f"[OK] golden re-baselined -> {GOLDEN} (keys: orth_rgb, color_enhanced, mus_image, chl_image, cal_image)")


if __name__ == "__main__":
    main()
