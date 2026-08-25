#!/usr/bin/env python
# coding: utf-8
"""End-to-end differential audit of the alive-pixel (rows) restriction.

The unit-level piecewise checks live in check_rows_logic.py (each function's
subset result is bit-exact at subset positions). This script audits the claim
at the level where the restriction actually lives: the *chained* alive_rows
lifecycle inside _judge_reference_entry (diagnostic accumulation -> not_abs ->
not_rel -> depth-ratio -> weighted constraints), plus the two public entry
points that embed it (classify serial path and classify_spectrum compiled
path).

Method: A/B differential. Mode A = production (rows restriction on). Mode B =
the three rows-consuming entry points monkeypatched to force rows=None (the
true full computation: every feature evaluated on every pixel). Mode B changes
no arithmetic for alive pixels and leaves NaN to propagate for rejected ones,
so any divergence between A and B is a defect in the alive-set bookkeeping
itself. As a side benefit, mode A exercises the r2-chain scratch buffer
(_r2_buf) with shrinking row counts while mode B holds it at full size, so
buffer-history sensitivity would also surface as an A/B mismatch.

Run from the project root:  python tests/check_alive_restriction.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root
import numpy as np
import cramm.classifier as C
from cramm.emit_reader import EmitReader

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
EXC_TYPES = (C.InvalidRangeError, C.InvalidLeftEndPointError, C.InvalidRightEndPointError)
FAIL = []


def check(name, cond, detail=""):
    print(f"  [{'OK' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        FAIL.append(name)


def bit_eq(a, b):
    """Strict bitwise equality with NaN-payload normalization: NaN==NaN,
    everything else (including +0 vs -0) must be bit-identical."""
    a = np.ascontiguousarray(a, dtype="float64")
    b = np.ascontiguousarray(b, dtype="float64")
    if a.shape != b.shape:
        return False
    return ((a.view(np.uint64) == b.view(np.uint64)) | (np.isnan(a) & np.isnan(b))).all()


def run_all_rules(clf, spec, wl, resampled1, chanels):
    """(fit, fd) for every rule, or the exception type name for endpoint errors."""
    out = {}
    for name, rule in clf.rf.items():
        try:
            out[name] = C._judge_reference_entry(spec, wl, rule, resampled1, chanels)
        except EXC_TYPES as e:
            out[name] = f"EXC:{type(e).__name__}"
    return out


def force_full_computation():
    """Monkeypatch the three rows-consuming functions to ignore the rows
    argument (= the full computation the restriction claims equivalence with).
    Returns a restore closure."""
    orig = (C._diagnostic_feature, C._not_absolute_feature, C._not_relative_feature)

    def wrap(fn):
        return lambda *a, **k: fn(*a, **{**k, "rows": None})

    C._diagnostic_feature = wrap(orig[0])
    C._not_absolute_feature = wrap(orig[1])
    C._not_relative_feature = wrap(orig[2])

    def restore():
        C._diagnostic_feature, C._not_absolute_feature, C._not_relative_feature = orig

    return restore


def main():
    clf = C.MicaClassifier.from_paths()
    spectrum, lon, lat, w, bp, wl, chanels = EmitReader.load(NC)
    r, c, s = spectrum.shape
    resampled1 = clf.get_resample(w, bp)

    # Two tiles for mineralogical diversity: the chlorite-rich tile anchored
    # by test_chl_center_product, plus a mixed-cover scene-edge strip.
    tile_a = spectrum[440:540, 160:260, :]   # 10k px, chlorite-bearing
    tile_b = spectrum[0:100, 0:200, :]       # 20k px, mixed cover
    spec = np.concatenate([tile_a.reshape(-1, s), tile_b.reshape(-1, s)])[:, chanels]
    print(f"A/B pixels: {len(spec)} (tile A 100x100 + tile B 100x200), rules: {len(clf.rf)}")

    print("== 1. _judge_reference_entry: rows-on vs forced-full, all rules ==")
    prod = run_all_rules(clf, spec, wl, resampled1, chanels)
    restore = force_full_computation()
    try:
        full = run_all_rules(clf, spec, wl, resampled1, chanels)
    finally:
        restore()
    n_cmp = n_exc = 0
    for name in clf.rf:
        a, b = prod[name], full[name]
        if isinstance(a, str) or isinstance(b, str):
            check(f"{name}: same endpoint exception both modes", a == b, f"{a} vs {b}")
            n_exc += 1
            continue
        ok_fit = bit_eq(a[0], b[0])
        ok_fd = bit_eq(a[1], b[1])
        check(f"{name}: fit/fd bit-exact", ok_fit and ok_fd,
              "" if ok_fit and ok_fd else f"fit={ok_fit} fd={ok_fd}")
        n_cmp += 1
    print(f"  compared {n_cmp} rules, {n_exc} endpoint-exception rules")

    print("== 2. weight-0 feature keeps pixels alive (r == 0.0, not NaN) ==")
    # Rules whose 1st feature has weight 0 but is followed by more features:
    # if the alive set were recomputed from something other than ~isnan(weighted r)
    # these pixels would wrongly drop out before the later features.
    n_alive0_total = 0
    for name in ["gypsum", "alunite_K_250C", "clinochlore", "thuringite", "chlorite_lowFe"]:
        rule = clf.rf[name]
        f0 = rule["diagnostic_features"][0]
        assert f0["feature_weight"] == 0.0, f"{name} feat0 weight != 0"
        r0 = C._diagnostic_feature(
            spec, resampled1[rule["reference"]["reflectance_record"]][chanels], wl,
            f0["continuum_endpoints"], f0["feature_weight"],
            C._continuum_constraints_list(f0["continuum_constraints"]),
            f0["fit_constraint"], f0["depth_constraints"])[0]
        n_alive0 = int(((r0 == 0.0) & ~np.isnan(r0)).sum())
        n_alive0_total += n_alive0
        print(f"    {name}: {n_alive0} pixels alive through weight-0 feature")
    check("weight-0 alive path exercised on real data", n_alive0_total > 0,
          f"total {n_alive0_total}")

    print("== 3. classify() end-to-end (serial), both tiles ==")
    for label, tile in [("A(chlorite)", tile_a), ("B(edge)", tile_b)]:
        res_prod = clf.classify(tile, wl, w, bp, chanels, n_workers=1)
        restore = force_full_computation()
        try:
            res_full = clf.classify(tile, wl, w, bp, chanels, n_workers=1)
        finally:
            restore()
        check(f"classify {label}: num identical",
              np.array_equal(res_prod.num, res_full.num),
              f"diff px={int((res_prod.num != res_full.num).sum())}")
        for field in ["fit", "depth", "mus_center", "chl_center", "cal_center"]:
            check(f"classify {label}: {field} bit-exact",
                  bit_eq(getattr(res_prod, field), getattr(res_full, field)))

    print("== 4. classify_spectrum (compiled path) A/B on sampled pixels ==")
    rng = np.random.RandomState(7)
    sample = spec[rng.choice(len(spec), 200, replace=False)]
    n_diff = 0
    for i, sp in enumerate(sample):
        sp2 = sp.reshape(1, -1)  # classify_spectrum wants [1, len(chanels)]
        a = clf.classify_spectrum(sp2, wl, w, bp, chanels, top_n=5)
        restore = force_full_computation()
        try:
            b = clf.classify_spectrum(sp2, wl, w, bp, chanels, top_n=5)
        finally:
            restore()
        same = ([x["name"] for x in a] == [x["name"] for x in b]
                and all(bit_eq(x["fit"], y["fit"]) and bit_eq(x["fd"], y["fd"])
                        for x, y in zip(a, b)))
        if not same:
            n_diff += 1
            print(f"    pixel {i}: {[(x['name'], x['fit']) for x in a]} vs {[(x['name'], x['fit']) for x in b]}")
    check("compiled path: 200 sampled spectra top-5 identical", n_diff == 0, f"diff={n_diff}")

    print()
    print("Summary:", "FAIL: " + ", ".join(FAIL) if FAIL else
          "all passed -- alive-pixel restriction bit-exact with full computation end-to-end")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
