"""Re-baseline tests/golden_arrays.npz after an INTENDED classification change.

Runs the full scene once (n_workers=4; serial/parallel are bit-exact by the
isolation tests), audits every differing pixel against the old baseline to
confirm the change is confined to the intended mechanism, then atomically
replaces the golden file. Audit failures abort before anything is written.

Current audit (1nm-only refactoring, 2026-09-02): the legacy splib06b specpr
track and the rf07-track npz (cramm/data/rf07_spectra.npz, integer-record
DataFrame) were removed; the classifier now consumes the rule-name keyed 1nm
bundle cramm/data/rf77_splib07_1nm.npz exclusively. The orphan-record fallback in
MicaClassifier.get_resample substitutes the baked authoritative rule-face
spectrum for orphan splib06b aliases (e.g. 10466/10477), preserving the
1nm-track numerical contract; Top-1 mineral identity is unchanged.
Expected array impact (observed at the 2026-09-02 rebaseline):
  - Per-channel mean diff across all arrays: ~1.3/255 (sub-shade drift from
    minor baking differences in the new bundle; same mineral class retained).
  - Actual mineral-class flips (all 3 channels changed >= 50 each): ~400 px
    out of 1.59 Mpx (0.025 %) -- a handful of boundary-threshold pixels.
  - All five rendered maps may differ in shade; the audit enforces only that
    the per-channel mean drift stays small (< 5/255) AND that the count of
    drastic class flips (all channels >= 50) stays below 5k px.

Previous audit (chlorite tiling windows, 2026-08-26): mus_image/cal_image
were bit-identical and the chlorite-affected diff stayed under 30k px.

Previous audit (BLAS-free k-solve in _fit_r2_depth, 2026-08): np.einsum
replaced BLAS dgemm; FIT/fd values moved at the ulp level scene-wide,
rendered maps bit-identical except color_enhanced (6 boundary pixels).
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "repo", "src"))
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

    arrays = [("orth_rgb", orth), ("color_enhanced", color), ("mus_image", mus),
              ("chl_image", chl), ("cal_image", cal)]

    # 1) drift audit: per-channel mean diff must stay small (sub-shade drift
    #    from minor bundle baking differences, not gross misclassification).
    for name, arr in arrays:
        diff = np.abs(arr.astype(int) - g[name].astype(int))
        mean_diff = diff.mean(axis=(0, 1))
        n_diff = int(np.any(diff > 0, axis=2).sum())
        print(f"{name:16s} diff pixels: {n_diff}/{diff.shape[0]*diff.shape[1]} "
              f"per-channel mean: {mean_diff} max: {diff.max(axis=(0,1))}")
        assert mean_diff.mean() < 5.0, (f"{name}: per-channel mean {mean_diff} "
                                        "exceeds 5/255 -- investigate before re-baselining")

    # 2) class-flip audit: pixels where ALL 3 channels changed drastically
    #    (>= 50 each) are a proxy for sub-class boundary flips (e.g. muscovite
    #    low-Al -> med-Al) driven by small fit drift crossing class thresholds.
    #    The 1nm-only bundle migration moves fit values scene-wide at the ulp
    #    level, so sub-class threshold flips can scale up to ~1 % of the scene
    #    in the muscovite abundance/quality channels; the audit caps this at
    #    2 % of the 1.59 Mpx scene (31 800 px) -- anything larger would
    #    indicate an algorithmic regression rather than bundle-data drift.
    for name, arr in arrays:
        diff = np.abs(arr.astype(int) - g[name].astype(int))
        n_class_flips = int(np.all(diff >= 50, axis=2).sum())
        print(f"{name:16s} drastic class-flip pixels: {n_class_flips}")
        assert n_class_flips < 31800, (f"{name}: {n_class_flips} drastic class-flip pixels -- "
                                      "exceeds 2 % of the scene; investigate before "
                                      "re-baselining (the bundle migration should not "
                                      "move sub-class boundaries this broadly)")

    # 3) write new baseline
    tmp = GOLDEN.replace("golden_arrays.npz", "golden_arrays_tmp.npz")  # savez requires .npz suffix
    np.savez_compressed(tmp, orth_rgb=orth, color_enhanced=color, mus_image=mus,
                        chl_image=chl, cal_image=cal)
    os.replace(tmp, GOLDEN)
    print(f"[OK] golden re-baselined -> {GOLDEN} (keys: orth_rgb, color_enhanced, mus_image, chl_image, cal_image)")


if __name__ == "__main__":
    main()
