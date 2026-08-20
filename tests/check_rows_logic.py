#!/usr/bin/env python
# coding: utf-8
"""Unit-level differential audit of rows logic: subset computation must be bit-exact
with full computation at subset positions.

Coverage:
1. _diagnostic_feature: rows=None vs rows=subset -> 4 return values bit-identical at subset positions
2. _get_fit: same (returns len(rows) arrays, compared against full at corresponding positions)
3. _not_absolute/_not_relative: exclusion set with rows=subset == full exclusion set intersected with subset
4. Robustness against duplicate/unordered rows indices (defensive, not an actual call path)
5. Empty rows does not crash (defensive)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root (where the cramm package lives)
import numpy as np
from cramm.classifier import (
    MicaClassifier, _diagnostic_feature, _get_fit,
    _not_absolute_feature, _not_relative_feature, _continuum_constraints_list,
)
from cramm.emit_reader import EmitReader

FAIL = []


def check(name, cond, detail=""):
    print(f"  [{'OK' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        FAIL.append(name)


def main():
    clf = MicaClassifier.from_paths()
    spectrum, lon, lat, w, bp, wl, chanels = EmitReader.load(
        "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc")
    r, c, s = spectrum.shape
    resampled1 = clf.get_resample(w, bp)
    spec = spectrum[:80].reshape([-1, s])[:, chanels]
    N = len(spec)
    rng = np.random.RandomState(42)

    # pick a rule with multiple features + not_abs + not_rel + ratio constraints all present (calcite family)
    rule = clf.rf["calcite"]
    ref = resampled1[rule["reference"]["reflectance_record"]][chanels]

    print("== 1. _diagnostic_feature: rows subset vs full ==")
    for fi, feat in enumerate(rule["diagnostic_features"]):
        args = (spec, ref, wl, feat["continuum_endpoints"], feat["feature_weight"],
                _continuum_constraints_list(feat["continuum_constraints"]),
                feat["fit_constraint"], feat["depth_constraints"])
        full = _diagnostic_feature(*args)
        # simulate the alive set: alive rows of diag0 (use a random subset for diag0 itself)
        if fi == 0:
            rows = np.sort(rng.choice(N, N // 3, replace=False))
        else:
            rows = np.nonzero(~np.isnan(full[0]))[0][: max(1, N // 5)]
        sub = _diagnostic_feature(*args, rows=rows)
        for vi, vn in enumerate(["r2*w", "d*w", "fd", "raw_d"]):
            a, b = full[vi][rows], sub[vi][rows]
            same = np.array_equal(a, b, equal_nan=True)
            check(f"diag[{fi}].{vn} subset bit-exact", same)
            # outside the subset must be all NaN (style-A contract)
            outside = np.ones(N, bool); outside[rows] = False
            check(f"diag[{fi}].{vn} all NaN outside subset", np.isnan(sub[vi][outside]).all())

    print("== 2. _get_fit: rows subset vs full ==")
    na = rule["not_absolute_features"][0]
    ref2 = resampled1[na["reflectance_record"]][chanels]
    rows = np.sort(rng.choice(N, N // 2, replace=False))
    r2f, df = _get_fit(spec, ref2, wl, na["continuum_endpoints"])
    r2s, ds = _get_fit(spec, ref2, wl, na["continuum_endpoints"], rows=rows)
    check("_get_fit r2 subset bit-exact", np.array_equal(r2f[rows], r2s, equal_nan=True))
    check("_get_fit depth subset bit-exact", np.array_equal(df[rows], ds, equal_nan=True))

    print("== 3. not_abs / not_rel: exclusion set == full intersected with subset ==")
    bad_full = _not_absolute_feature(spec, ref2, wl, na["continuum_endpoints"],
                                     na["fit_constraint"], na["absolute_depth_constraint"])
    bad_sub = _not_absolute_feature(spec, ref2, wl, na["continuum_endpoints"],
                                    na["fit_constraint"], na["absolute_depth_constraint"], rows=rows)
    expect = np.intersect1d(bad_full, rows)
    check("not_abs exclusion set == full ∩ subset", np.array_equal(np.sort(bad_sub), np.sort(expect)),
          f"sub={len(bad_sub)} expect={len(expect)}")

    nr = rule["not_relative_features"][0]
    ref3 = resampled1[nr["reflectance_record"]][chanels]
    # RELATIVE_FEATURE_DEPTH: use diag0 raw depth (full)
    raw0 = _diagnostic_feature(spec, ref, wl, rule["diagnostic_features"][0]["continuum_endpoints"],
                               rule["diagnostic_features"][0]["feature_weight"],
                               _continuum_constraints_list(rule["diagnostic_features"][0]["continuum_constraints"]),
                               rule["diagnostic_features"][0]["fit_constraint"],
                               rule["diagnostic_features"][0]["depth_constraints"])[3]
    bad_full = _not_relative_feature(spec, ref3, wl, nr["continuum_endpoints"],
                                     nr["fit_constraint"], raw0, nr["relative_depth_threshold"])
    # subset must take diag0 alive rows (real call semantics: rows ⊆ diag-alive -> threshold non-NaN)
    rows_alive = np.nonzero(~np.isnan(raw0))[0]
    rows2 = rows_alive[: len(rows_alive) // 2]
    bad_sub = _not_relative_feature(spec, ref3, wl, nr["continuum_endpoints"],
                                    nr["fit_constraint"], raw0, nr["relative_depth_threshold"], rows=rows2)
    expect = np.intersect1d(bad_full, rows2)
    check("not_rel exclusion set == full ∩ subset", np.array_equal(np.sort(bad_sub), np.sort(expect)),
          f"sub={len(bad_sub)} expect={len(expect)}")

    print("== 4. Defensive: unordered/duplicate/empty rows ==")
    rows_dup = np.array([5, 3, 3, 9, 1])
    try:
        out = _diagnostic_feature(spec, ref, wl, rule["diagnostic_features"][0]["continuum_endpoints"],
                                  1.0, _continuum_constraints_list(rule["diagnostic_features"][0]["continuum_constraints"]),
                                  rule["diagnostic_features"][0]["fit_constraint"],
                                  rule["diagnostic_features"][0]["depth_constraints"], rows=rows_dup)
        full0 = _diagnostic_feature(spec, ref, wl, rule["diagnostic_features"][0]["continuum_endpoints"],
                                    1.0, _continuum_constraints_list(rule["diagnostic_features"][0]["continuum_constraints"]),
                                    rule["diagnostic_features"][0]["fit_constraint"],
                                    rule["diagnostic_features"][0]["depth_constraints"])
        check("unordered duplicate rows do not crash and values are correct",
              np.array_equal(out[0][rows_dup], full0[0][rows_dup], equal_nan=True))
    except Exception as e:
        check("unordered duplicate rows do not crash", False, str(e))
    try:
        out = _get_fit(spec, ref2, wl, na["continuum_endpoints"], rows=np.array([], dtype=int))
        check("empty rows returns empty arrays", len(out[0]) == 0)
    except Exception as e:
        check("empty rows does not crash", False, repr(e))

    print()
    print("Summary:", "FAIL: " + ", ".join(FAIL) if FAIL else "all passed -- rows subset semantics bit-exact with full computation")


if __name__ == "__main__":
    main()
