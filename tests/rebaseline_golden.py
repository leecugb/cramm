"""Re-baseline tests/golden_arrays.npz after an INTENDED classification change.

Runs the full scene once (n_workers=4; serial/parallel are bit-exact by the
isolation tests), audits every differing pixel against the old baseline to
confirm the change is confined to the intended mechanism, then atomically
replaces the golden file. Audit failures abort before anything is written.

Current audit (carbonate cal_center product line, 2026-08): the calcite and
dolomite abundant+plain pairs carry identical absorption_center_range
windows, so every in-window center hits two rules -> ambiguous -> keep. The
carbonate arbitration therefore NEVER flips by construction (pinned by
test_carbonate_window_arbitration), and all four existing golden arrays must
be BIT-IDENTICAL; only cal_image changes. Latest change: the windowless
mixture calcite.5+dolomite.5 joined CARBONATE_MINERALS, so its winner pixels
now carry a quadratic center (they never enter window-flip arbitration).
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

    # 1) zero-flip audit: the four existing arrays must be bit-identical
    for name, arr in [("orth_rgb", orth), ("color_enhanced", color),
                      ("mus_image", mus), ("chl_image", chl)]:
        same = np.array_equal(arr, g[name])
        print(f"{name:16s} bit-identical: {same}")
        assert same, (f"{name} changed -- aborting: carbonate arbitration is "
                      "zero-flip by construction; investigate the diff first")

    # 2) cal_image sanity: non-black pixels must exist (scene has ~78.7k pure
    #    carbonate-rule winners; carbonate-bearing mixture rules mostly carry
    #    no center -- only calcite.5+dolomite.5 does, as a CARBONATE_MINERALS
    #    member, adding its winner pixels to the colored set)
    nonblack = int((cal.any(axis=2)).sum())
    print(f"cal_image non-black pixels: {nonblack}")
    assert nonblack > 50_000, "cal_image unexpectedly sparse -- investigate before re-baselining"

    # 3) write new baseline (5 arrays: cal_image joins the golden contract)
    tmp = GOLDEN.replace("golden_arrays.npz", "golden_arrays_tmp.npz")  # savez requires .npz suffix
    np.savez_compressed(tmp, orth_rgb=orth, color_enhanced=color, mus_image=mus,
                        chl_image=chl, cal_image=cal)
    os.replace(tmp, GOLDEN)
    print(f"[OK] golden re-baselined -> {GOLDEN} (keys: orth_rgb, color_enhanced, mus_image, chl_image, cal_image)")


if __name__ == "__main__":
    main()
