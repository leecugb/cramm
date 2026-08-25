"""Re-baseline tests/golden_arrays.npz after an INTENDED classification change.

Runs the full scene once (n_workers=4; serial/parallel are bit-exact by the
isolation tests), audits every differing pixel against the old baseline to
confirm the change is confined to the intended mechanism, then atomically
replaces the golden file. Audit failures abort before anything is written.

Current audit (thuringite joins the chlorite arbitration, 2026-08): thuringite
entered CHLORITE_MINERALS and carries the new Fe-richest window [2.255, 2.266),
extending the tolerant-window sequence beyond clinochlore_Fe [2.251, 2.25549).
Unlike the zero-flip carbonate scheme this change CAN flip: centers in
thuringite's unique zone (2.25549, 2.266) reassign a chlorite winner to
thuringite (and thuringite winners in another rule's unique zone flip away).
Expected array impact:
  - orth_rgb / mus_image / cal_image: BIT-IDENTICAL (no mechanism touches them)
  - color_enhanced: changes only where a winner flipped among chlorite rules
  - chl_image: changes at flip pixels and at thuringite winners that newly
    carry a center inside the renderer's [2.244, 2.259) bins
Confinement audit: every differing pixel of the two affected arrays must have
its NEW winner inside CHLORITE_MINERALS (checked against a full-scene classify
run; flips only reassign within the windowed-rule group).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from cramm.mica_engine import MicaEngine
from cramm.classifier import CHLORITE_MINERALS

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
    for name, arr in [("orth_rgb", orth), ("mus_image", mus), ("cal_image", cal)]:
        same = np.array_equal(arr, g[name])
        print(f"{name:16s} bit-identical: {same}")
        assert same, (f"{name} changed -- aborting: the thuringite window change "
                      "cannot touch this array; investigate the diff first")

    # 2) confinement audit: color_enhanced / chl_image may differ ONLY at pixels
    #    whose new winner is a chlorite rule (flips reassign within the group)
    diff = {
        "color_enhanced": np.any(color != g["color_enhanced"], axis=2),
        "chl_image": np.any(chl != g["chl_image"], axis=2),
    }
    n_diff = {k: int(v.sum()) for k, v in diff.items()}
    print(f"diff pixels: color_enhanced={n_diff['color_enhanced']}  "
          f"chl_image={n_diff['chl_image']}")
    if any(n_diff.values()):
        res = eng._classifier.classify(spectrum, wl, w, bp, chanels, n_workers=4)
        num2d = res.num.reshape(diff["color_enhanced"].shape)
        names = {i: n for n, i in res.index_d.items()}
        chl_idx = {res.index_d[n] for n in CHLORITE_MINERALS if n in res.index_d}
        for k, m in diff.items():
            if not m.any():
                continue
            win = num2d[m]
            outside = ~np.isin(win, list(chl_idx))
            print(f"  {k}: new winners at diff pixels = "
                  f"{ {names[i]: int((win == i).sum()) for i in np.unique(win)} }")
            assert not outside.any(), (
                f"{k}: {int(outside.sum())} diff pixels have non-chlorite new "
                f"winners {sorted({names[i] for i in win[outside]})} -- the change "
                "escaped the chlorite arbitration; investigate before re-baselining")

    # 3) chl_image sanity: non-black pixels must still exist in bulk (thuringite
    #    gains plus flips can move pixels across the [2.244, 2.259) bins;
    #    scene baseline is ~31k colored chlorite pixels)
    nonblack = int((chl.any(axis=2)).sum())
    print(f"chl_image non-black pixels: {nonblack} (was {int((g['chl_image'].any(axis=2)).sum())})")
    assert nonblack > 20_000, "chl_image unexpectedly sparse -- investigate before re-baselining"

    # 4) write new baseline
    tmp = GOLDEN.replace("golden_arrays.npz", "golden_arrays_tmp.npz")  # savez requires .npz suffix
    np.savez_compressed(tmp, orth_rgb=orth, color_enhanced=color, mus_image=mus,
                        chl_image=chl, cal_image=cal)
    os.replace(tmp, GOLDEN)
    print(f"[OK] golden re-baselined -> {GOLDEN} (keys: orth_rgb, color_enhanced, mus_image, chl_image, cal_image)")


if __name__ == "__main__":
    main()
