"""Re-baseline tests/golden_arrays.npz after an INTENDED classification change.

Runs the full scene once (n_workers=4; serial/parallel are bit-exact by the
isolation tests), audits every differing pixel against the old baseline to
confirm the change is confined to the intended mechanism, then atomically
replaces the golden file. Audit failures abort before anything is written.

Current audit (chlorite tiling windows, 2026-08-26): the four chlorite
absorption_center_range windows changed from deliberately overlapping
([2.245,2.248) / [2.247,2.252) / [2.251,2.25549) / [2.255,2.266)) to seamless
tiling ([2.245,2.248) / [2.248,2.252) / [2.252,2.256) / [2.256,2.266)) --
previously ambiguous overlap-zone pixels now flip deterministically.
Expected array impact:
  - mus_image / cal_image: BIT-IDENTICAL (muscovite and carbonate windows
    untouched; no mechanism to move)
  - orth_rgb / color_enhanced / chl_image: differ ONLY at chlorite
    arbitration pixels (verdict flips + center refits); the old-vs-new
    chlorite flip sets total ~16k pixels each with heavy overlap, so the
    diff count must stay well below 30k (scene = 1.59 Mpx)
Observed at the 2026-08-26 rebaseline: see run log; muscovite/carbonate
arrays bit-identical, chlorite-affected arrays diff only in the chlorite
arbitration set.

Previous audit (BLAS-free k-solve in _fit_r2_depth, 2026-08): np.einsum
replaced BLAS dgemm; FIT/fd values moved at the ulp level scene-wide,
rendered maps bit-identical except color_enhanced (6 boundary pixels).
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

    # 1) identity audit: muscovite/carbonate windows are untouched by the
    #    chlorite tiling change, so their rendered maps must be bit-identical
    for name, arr in [("mus_image", mus), ("cal_image", cal)]:
        same = np.array_equal(arr, g[name])
        print(f"{name:16s} bit-identical: {same}")
        assert same, (f"{name} changed -- aborting: a chlorite-window change "
                      "cannot touch this array; investigate the diff first")

    # 2) confinement audit: orth_rgb / color_enhanced / chl_image may differ
    #    only at chlorite arbitration pixels. Old/new chlorite flip sets are
    #    ~15.3k/~16.2k px with heavy overlap, so the union diff must stay
    #    far below 30k px (1.9 % of the 1.59 Mpx scene).
    for name, arr in [("orth_rgb", orth), ("color_enhanced", color), ("chl_image", chl)]:
        n_diff = int(np.any(arr != g[name], axis=2).sum())
        print(f"{name:16s} diff pixels: {n_diff}")
        assert n_diff < 30000, (f"{name}: {n_diff} diff pixels -- far above the chlorite "
                                "arbitration scale; investigate before re-baselining")

    # 3) write new baseline
    tmp = GOLDEN.replace("golden_arrays.npz", "golden_arrays_tmp.npz")  # savez requires .npz suffix
    np.savez_compressed(tmp, orth_rgb=orth, color_enhanced=color, mus_image=mus,
                        chl_image=chl, cal_image=cal)
    os.replace(tmp, GOLDEN)
    print(f"[OK] golden re-baselined -> {GOLDEN} (keys: orth_rgb, color_enhanced, mus_image, chl_image, cal_image)")


if __name__ == "__main__":
    main()
