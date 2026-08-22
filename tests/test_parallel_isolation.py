#!/usr/bin/env python
# coding: utf-8
"""Parallel/shared-state isolation verification (no EMIT NC needed).

Proves the parallel computation logic cannot fail through shared variables:

1. worker isolation (mini golden): serial vs parallel on a synthetic cube are
   bit-identical on all four outputs (fit/depth/num/mus_center) — shared-state
   corruption across worker processes would show up here
2. r2-chain scratch buffer is thread-local: two threads get distinct buffers;
   the same thread reuses its own
3. concurrent classify_spectrum from two threads == sequential baseline
   (byte-identical)
4. concurrent parallel classify from two threads is serialized by the env
   lock and stays bit-identical to the sequential baseline
5. BLAS env override is restored after a parallel run (set and unset vars)
6. the temporary memmap file is removed after a parallel run

Synthetic band config + package-bundled splib; cross-platform.
"""
import glob
import os
import sys
import tempfile
import threading
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root

RESULTS = []


class SkipTest(Exception):
    pass


def run(name, fn):
    try:
        fn()
    except SkipTest as e:
        RESULTS.append(("SKIP", name))
        print(f"[SKIP] {name}: {e}")
    except BaseException as e:
        RESULTS.append(("FAIL", name))
        print(f"[FAIL] {name}: {e}")
        traceback.print_exc()
    else:
        RESULTS.append(("OK", name))
        print(f"[ OK ] {name}")


# ----------------------------------------------------------------------------
# Shared fixture: synthetic EMIT-like band config (same as test_core.py)
# ----------------------------------------------------------------------------

W = np.linspace(0.381, 2.508, 285)
BP = np.full(285, 0.0074)
CHANELS = np.array([i for i in range(285) if not (126 <= i < 150 or 190 <= i < 210)])
WL = W[CHANELS]

BLAS_VARS = ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")

_ENG = None


def eng():
    global _ENG
    if _ENG is None:
        from cramm import MicaEngine
        _ENG = MicaEngine()
    return _ENG


def ref_of(e, rule_name):
    resampled1 = e.get_resample(W, BP)
    return resampled1[e.rf[rule_name]["reference"]["reflectance_record"]]


def mixed_cube(e, r=6, c=4):
    """[r, c, 285] float32 cube: rows alternate muscovite_medAl / illite_imt1
    reference spectra (covers the muscovite second pass + a plain rule).
    r=6 -> segments (0,2),(2,4),(4,6), exercising all three segments."""
    a = ref_of(e, "muscovite_medAl").astype("float32")
    b = ref_of(e, "illite_imt1").astype("float32")
    rows = [(a if i % 2 == 0 else b) for i in range(r)]
    return np.stack(rows, axis=0)[:, None, :].repeat(c, axis=1)  # [r, c, 285]


def result_bytes(res):
    return (res.fit.tobytes(), res.depth.tobytes(),
            res.num.tobytes(), res.mus_center.tobytes())


# ----------------------------------------------------------------------------
# 1. worker isolation: serial vs parallel mini golden
# ----------------------------------------------------------------------------

def test_serial_vs_parallel_bitexact():
    """n_workers=1 vs n_workers=3 on the synthetic cube: bit-identical outputs
    (any shared-variable corruption across worker processes would break this)."""
    e = eng()
    cube = mixed_cube(e)
    base = e._classifier.classify(cube, WL, W, BP, CHANELS, n_workers=1)
    par = e._classifier.classify(cube, WL, W, BP, CHANELS, n_workers=3)
    for label, x, y in zip(("fit", "depth", "num", "mus_center"),
                           result_bytes(base), result_bytes(par)):
        assert x == y, f"serial vs parallel mismatch in {label}"
    # sanity: both muscovite-group and plain-rule pixels actually classified
    names = {base.index[i] for i in base.num}
    assert "muscovite_medAl" in names and "illite_imt1" in names, f"unexpected assignment {names}"
    assert (base.mus_center[base.num == base.index_d["muscovite_medAl"]] > 2.19).all()


# ----------------------------------------------------------------------------
# 2. thread-local r2 buffer
# ----------------------------------------------------------------------------

def test_r2_buf_thread_local():
    """_r2_buf: distinct threads get distinct underlying buffers; the same thread
    reuses its own (the return value is a fresh slice VIEW each call, so the
    comparison must go through .base)."""
    from cramm.classifier import _r2_buf
    main_view = _r2_buf(4, 8)
    assert _r2_buf(4, 8).base is main_view.base, "same thread should reuse its buffer"
    other = []

    def worker():
        other.append(_r2_buf(4, 8))

    t = threading.Thread(target=worker)
    t.start(); t.join()
    assert other and other[0].base is not main_view.base, "worker thread must get its own buffer"
    # contents are independent scratch space
    main_view[:] = 1.0
    t = threading.Thread(target=lambda: other[0].__setitem__(slice(None), 2.0))
    t.start(); t.join()
    assert (main_view == 1.0).all() and (other[0] == 2.0).all(), "buffers must not share memory"


# ----------------------------------------------------------------------------
# 3. concurrent classify_spectrum from two threads
# ----------------------------------------------------------------------------

def test_concurrent_classify_spectrum_threads():
    """Two threads running classify_spectrum concurrently on the same engine:
    byte-identical to the sequential baseline (thread-local scratch)."""
    e = eng()
    spec_a = ref_of(e, "muscovite_medAl")
    spec_b = ref_of(e, "illite_imt1")
    # warm caches in the main thread (the cache-build race is benign but this
    # keeps the threaded section purely read-only)
    base_a = e.classify_spectrum(spec_a, WL, W, BP, CHANELS, top_n=10)
    base_b = e.classify_spectrum(spec_b, WL, W, BP, CHANELS, top_n=10)
    out = {}

    def call(tag, spec):
        # repeat several times to widen the race window
        for _ in range(5):
            out[tag] = e.classify_spectrum(spec, WL, W, BP, CHANELS, top_n=10)

    ta = threading.Thread(target=call, args=("a", spec_a))
    tb = threading.Thread(target=call, args=("b", spec_b))
    ta.start(); tb.start(); ta.join(); tb.join()

    def same(x, y):
        return [r["name"] for r in x] == [r["name"] for r in y] and all(
            np.float64(a["fit"]).tobytes() == np.float64(b["fit"]).tobytes()
            and np.float64(a["fd"]).tobytes() == np.float64(b["fd"]).tobytes()
            for a, b in zip(x, y))

    assert same(out["a"], base_a), "threaded result A differs from sequential baseline"
    assert same(out["b"], base_b), "threaded result B differs from sequential baseline"


# ----------------------------------------------------------------------------
# 4. concurrent parallel classify from two threads (env-lock serialization)
# ----------------------------------------------------------------------------

def test_concurrent_parallel_classify_threads():
    """Two threads running parallel classify concurrently: serialized by the
    env lock; each result bit-identical to the sequential baseline."""
    e = eng()
    cube = mixed_cube(e)
    base = e._classifier.classify(cube, WL, W, BP, CHANELS, n_workers=1)
    out, errs = {}, []

    def call(tag):
        try:
            out[tag] = e._classifier.classify(cube, WL, W, BP, CHANELS, n_workers=2)
        except BaseException as ex:
            errs.append(ex)

    ta = threading.Thread(target=call, args=("t1",))
    tb = threading.Thread(target=call, args=("t2",))
    ta.start(); tb.start(); ta.join(); tb.join()
    assert not errs, f"threaded classify raised: {errs}"
    for tag in ("t1", "t2"):
        for label, x, y in zip(("fit", "depth", "num", "mus_center"),
                               result_bytes(base), result_bytes(out[tag])):
            assert x == y, f"{tag}: threaded parallel result differs from baseline in {label}"


# ----------------------------------------------------------------------------
# 5. BLAS env restore
# ----------------------------------------------------------------------------

def test_env_vars_restored():
    """The 5 BLAS env vars are byte-identical before/after a parallel run —
    for vars that were set (custom value) and vars that were unset."""
    e = eng()
    cube = mixed_cube(e)
    saved = {v: os.environ.get(v) for v in BLAS_VARS}
    os.environ["MKL_NUM_THREADS"] = "7"  # sentinel: must be restored exactly
    os.environ.pop("OMP_NUM_THREADS", None)  # sentinel: must stay absent
    try:
        e._classifier.classify(cube, WL, W, BP, CHANELS, n_workers=2)
        assert os.environ.get("MKL_NUM_THREADS") == "7", "set var not restored"
        assert "OMP_NUM_THREADS" not in os.environ, "unset var leaked back into environ"
        for v in BLAS_VARS[2:]:
            assert os.environ.get(v) == saved[v], f"{v} changed"
    finally:
        for v in BLAS_VARS:
            if saved[v] is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = saved[v]


# ----------------------------------------------------------------------------
# 6. memmap temp file cleanup
# ----------------------------------------------------------------------------

def test_memmap_temp_cleanup():
    """No mica_spec_*.npy leftovers in the temp dir after a parallel run."""
    e = eng()
    cube = mixed_cube(e)
    pat = os.path.join(tempfile.gettempdir(), "mica_spec_*.npy")
    before = set(glob.glob(pat))
    e._classifier.classify(cube, WL, W, BP, CHANELS, n_workers=2)
    after = set(glob.glob(pat))
    leaked = after - before
    assert not leaked, f"temp memmap files leaked: {leaked}"


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    print("== parallel / shared-state isolation (synthetic bands, no NC) ==", flush=True)
    run("worker isolation: serial == parallel (bit-exact)", test_serial_vs_parallel_bitexact)
    run("r2 scratch buffer is thread-local", test_r2_buf_thread_local)
    run("concurrent classify_spectrum (2 threads) == baseline", test_concurrent_classify_spectrum_threads)
    run("concurrent parallel classify (2 threads) == baseline", test_concurrent_parallel_classify_threads)
    run("BLAS env vars restored after parallel run", test_env_vars_restored)
    run("memmap temp file cleaned up", test_memmap_temp_cleanup)

    n_ok = sum(1 for s, _ in RESULTS if s == "OK")
    n_skip = sum(1 for s, _ in RESULTS if s == "SKIP")
    n_fail = sum(1 for s, _ in RESULTS if s == "FAIL")
    print(f"\nSummary: {n_ok} passed / {n_skip} skipped / {n_fail} failed")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
