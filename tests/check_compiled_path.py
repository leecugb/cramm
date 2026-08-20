#!/usr/bin/env python
# coding: utf-8
"""Bit-exact differential validation: compiled fast path (classify_spectrum) vs direct slow path.

For N real pixels + 2 boundary pixels x 77 rules:
  fast = classify_spectrum (driven by _get_compiled_rules compiled artifacts)
  slow = per-rule _judge_reference_entry (pre=None, reference side computed on the fly)
The mineral name sequences and fit/fd of both must be bit-exact (float64 bit-pattern
comparison, including NaN payloads).

Also validates the compile-time exception path: endpoints beyond the wavelength range ->
captured at compile time, re-raised in place at evaluation time.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root (where the cramm package lives)
import numpy as np
from cramm.classifier import (
    MicaClassifier, _judge_reference_entry, _diagnostic_feature, _precompute_feature,
    InvalidRangeError, InvalidLeftEndPointError, InvalidRightEndPointError,
)
from cramm.emit_reader import EmitReader

EXC = (InvalidRangeError, InvalidLeftEndPointError, InvalidRightEndPointError)


def slow_classify(clf, spec, wl, resampled1, chanels):
    """Non-compiled equivalent of classify_spectrum (per-rule on-the-fly reference-side computation)."""
    out = []
    for key, value in clf.rf.items():
        try:
            fit, fd = _judge_reference_entry(spec, wl, value, resampled1, chanels)
        except EXC:
            continue
        fv, dv = float(fit[0]), float(fd[0])
        if not np.isnan(fv) and fv > 0:
            out.append((key, fv, dv))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def bits(x):
    return np.float64(x).tobytes()


def main():
    clf = MicaClassifier.from_paths()
    spectrum, lon, lat, w, bp, wl, chanels = EmitReader.load(
        "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc")
    resampled1 = clf.get_resample(w, bp)
    rng = np.random.RandomState(7)
    r, c, s = spectrum.shape

    # boundary pixels: all-zero spectrum + known high-reflectance pixel + random pixels
    pixels = [(None, None), (640, 620)]
    pixels += [(rng.randint(r), rng.randint(c)) for _ in range(300)]

    fails = 0
    for t, (i, j) in enumerate(pixels):
        if i is None:
            spec = np.zeros((1, len(chanels)))
        else:
            spec = spectrum[i, j, chanels].reshape(1, -1).astype("float64")
        fast = [(d["name"], d["fit"], d["fd"])
                for d in clf.classify_spectrum(spec, wl, w, bp, chanels, top_n=len(clf.rf))]
        slow = slow_classify(clf, spec, wl, resampled1, chanels)
        tag = f"pix({i},{j})" if i is not None else "pix(zeros)"
        if len(fast) != len(slow):
            print(f"[FAIL] {tag} passing rule count {len(fast)} vs {len(slow)}")
            fails += 1
            continue
        for (nf, ff, df), (ns, fs, ds) in zip(fast, slow):
            if nf != ns or bits(ff) != bits(fs) or bits(df) != bits(ds):
                print(f"[FAIL] {tag} {nf}: fast=({ff!r},{df!r}) slow=({ns},{fs!r},{ds!r})")
                fails += 1

    # second call (compile cache hit) must produce identical results
    spec = spectrum[640, 620, chanels].reshape(1, -1).astype("float64")
    again = [(d["name"], d["fit"], d["fd"])
             for d in clf.classify_spectrum(spec, wl, w, bp, chanels, top_n=len(clf.rf))]
    first = [(d["name"], d["fit"], d["fd"])
             for d in clf.classify_spectrum(spec, wl, w, bp, chanels, top_n=len(clf.rf))]
    if len(again) != len(first) or any(
        a[0] != b[0] or bits(a[1]) != bits(b[1]) or bits(a[2]) != bits(b[2])
        for a, b in zip(again, first)
    ):
        print("[FAIL] results changed after compile cache hit")
        fails += 1

    # compile-time exception path: endpoints beyond wavelength range
    some_id = next(iter(resampled1))
    pre_bad = _precompute_feature(resampled1[some_id][chanels], wl, [99.0, 99.1, 99.2, 99.3])
    if not isinstance(pre_bad.get("exc"), InvalidRangeError):
        print("[FAIL] InvalidRangeError not captured at compile time")
        fails += 1
    else:
        try:
            _diagnostic_feature(spec, None, wl, None, 1.0, pre=pre_bad)
            print("[FAIL] InvalidRangeError not raised at evaluation time")
            fails += 1
        except InvalidRangeError:
            pass

    print("Summary:", f"FAIL x{fails}" if fails else
          f"all passed -- {len(pixels)} pixels x {len(clf.rf)} rules fast/slow bit-exact (incl. cache hit and exception path)")


if __name__ == "__main__":
    main()
