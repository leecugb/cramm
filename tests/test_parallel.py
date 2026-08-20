import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root (where the cramm package lives)
import numpy as np
from cramm.mica_engine import MicaEngine

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"


def run(nw):
    print(f"[init] n_workers={nw}", flush=True)
    eng = MicaEngine()
    t0 = time.time()
    spectrum, lon, lat, w, bp, wl, chanels = eng.load_emit(NC)
    print(f"[load_emit] {time.time()-t0:.1f}s  spectrum={spectrum.shape} {spectrum.dtype}", flush=True)

    t1 = time.time()
    orth, color, mus = eng.spectrum_analysis(
        spectrum, wl, w, bp, chanels,
        n_workers=nw,
        progress_callback=lambda p: print(f"  progress {p}% @ {time.time()-t1:.1f}s", flush=True),
        log_callback=lambda m: print(f"  [LOG] {m}", flush=True),
    )
    dt = time.time() - t1
    print(f"[spectrum_analysis] {dt:.1f}s (n_workers={nw})", flush=True)

    g = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_arrays.npz"))
    ok = True
    for name, arr in [("orth_rgb", orth), ("color_enhanced", color), ("mus_image", mus)]:
        same = np.array_equal(arr, g[name])
        print(f"  {name:16s} array_equal={same}", flush=True)
        if not same:
            d = np.abs(arr.astype(int) - g[name].astype(int))
            print(f"    diff pixels={(d>0).sum()}/{d.size} max={d.max()}", flush=True)
            ok = False
    print("[PASS]" if ok else "[FAIL]", flush=True)


if __name__ == "__main__":
    nw = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    run(nw)
