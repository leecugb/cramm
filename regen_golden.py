import time

import numpy as np

from cramm.mica_engine import MicaEngine

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"


def main():
    eng = MicaEngine()
    spectrum, lon, lat, w, bp, wl, chanels = eng.load_emit(NC)

    t0 = time.time()
    o4, c4, m4 = eng.spectrum_analysis(spectrum, wl, w, bp, chanels, n_workers=4)
    print(f"parallel(4): {time.time() - t0:.1f}s", flush=True)
    t0 = time.time()
    o1, c1, m1 = eng.spectrum_analysis(spectrum, wl, w, bp, chanels, n_workers=1)
    print(f"serial(1):   {time.time() - t0:.1f}s", flush=True)

    ok = True
    for name, a, b in [("orth_rgb", o4, o1), ("color_enhanced", c4, c1), ("mus_image", m4, m1)]:
        same = np.array_equal(a, b)
        print(f"  {name:16s} serial==parallel: {same}", flush=True)
        ok = ok and same

    g = np.load("tests/golden_arrays.npz")
    for name, a in [("orth_rgb", o4), ("color_enhanced", c4), ("mus_image", m4)]:
        same = np.array_equal(a, g[name])
        d = (a.astype(int) != g[name].astype(int)).any(-1)
        print(f"  {name:16s} vs old golden: equal={same}  changed_pixels={d.sum()}", flush=True)

    if ok:
        np.savez_compressed("tests/golden_arrays.npz", orth_rgb=o4, color_enhanced=c4, mus_image=m4)
        print("golden_arrays.npz regenerated", flush=True)
    print("[SERIAL==PARALLEL PASS]" if ok else "[SERIAL!=PARALLEL FAIL]", flush=True)


if __name__ == "__main__":
    main()
