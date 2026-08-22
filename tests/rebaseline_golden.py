"""Re-baseline tests/golden_arrays.npz after an INTENDED classification change.

Runs the full scene once (n_workers=4; serial/parallel are bit-exact by the
isolation tests), audits every differing pixel against the old baseline to
confirm the change is confined to the intended mechanism, then atomically
replaces the golden file. Audit failures abort before anything is written.

Current audit (chlorite tolerant-window arbitration, 2026-08): class flips
are only allowed among the three pure-chlorite rules, whose mapping colors
are chlorite_lowFe [235,25,0] and clinochlore/clinochlore_Fe [255,20,20];
mus_image must stay bit-identical (muscovite path untouched).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from cramm.mica_engine import MicaEngine

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_arrays.npz")

ALLOWED_COLORS = {(235, 25, 0), (255, 20, 20)}  # chlorite_lowFe, clinochlore/clinochlore_Fe


def main():
    eng = MicaEngine()
    spectrum, lon, lat, w, bp, wl, chanels = eng.load_emit(NC)
    t0 = time.time()
    orth, color, mus, chl = eng.spectrum_analysis(
        spectrum, wl, w, bp, chanels, n_workers=4,
        progress_callback=lambda p: print(f"  progress {p}% @ {time.time()-t0:.1f}s", flush=True),
    )

    with np.load(GOLDEN) as z:  # eager load + close: Windows cannot replace an open file
        g = {k: z[k] for k in z.files}
    # 1) muscovite path untouched
    assert np.array_equal(mus, g["mus_image"]), "mus_image changed -- aborting, this re-baseline only covers chlorite arbitration"

    # 2) every orth_rgb diff is a chlorite-family color on BOTH sides
    diff = (orth != g["orth_rgb"]).any(axis=2)
    print(f"orth_rgb diff pixels: {diff.sum()}")
    old_colors = {tuple(c) for c in g["orth_rgb"][diff]}
    new_colors = {tuple(c) for c in orth[diff]}
    print(f"  old colors at diffs: {sorted(old_colors)}")
    print(f"  new colors at diffs: {sorted(new_colors)}")
    assert old_colors <= ALLOWED_COLORS and new_colors <= ALLOWED_COLORS, "non-chlorite color changed -- aborting"

    # 3) color_enhanced diffs must be a superset of the orth diffs (same class
    #    color, changed fit/depth brightness) and involve only chlorite px
    diff_c = (color != g["color_enhanced"]).any(axis=2)
    print(f"color_enhanced diff pixels: {diff_c.sum()}")
    assert (diff_c >= diff).all()
    oc = {tuple(c) for c in g["orth_rgb"][diff_c]}
    nc_ = {tuple(c) for c in orth[diff_c]}
    print(f"  orth colors over enhanced-diff region: old={sorted(oc)} new={sorted(nc_)}")
    assert oc <= ALLOWED_COLORS and nc_ <= ALLOWED_COLORS, "enhanced diff outside chlorite class -- aborting"

    # 4) write new baseline (4 arrays: chl_image joins the golden contract)
    tmp = GOLDEN.replace("golden_arrays.npz", "golden_arrays_tmp.npz")  # savez requires .npz suffix
    np.savez_compressed(tmp, orth_rgb=orth, color_enhanced=color, mus_image=mus, chl_image=chl)
    os.replace(tmp, GOLDEN)
    print(f"[OK] golden re-baselined -> {GOLDEN} (keys: orth_rgb, color_enhanced, mus_image, chl_image)")


if __name__ == "__main__":
    main()
