#!/usr/bin/env python
# coding: utf-8
"""Custom rule-library verification: after modifying rf.json — via rf_path at
construction or in-place mutation + invalidate_caches — the program must
execute the NEW rules.

Scenarios:
1. rf_path construction loads a trimmed library (only those rules can win)
2. fit_constraint modification rejects the previously winning rule
3. adding max_depth_ratio_feat1_over_feat0 rejects the rule (d1/d0 >= 0 always)
4. a newly added rule is executed (clone appears, bit-identical fit to its source)
5. cache contract: mutation WITHOUT invalidate_caches is silently stale;
   adding a key WITHOUT invalidate raises KeyError; invalidate fixes both
6. scene level (classify): killing the winner changes the assignment
7. scene level: modifying absorption_center_range windows changes the
   wavelength-arbitrated muscovite attribution

Pure unit suite (synthetic band config + package-bundled splib); no EMIT NC needed.
"""
import copy
import json
import os
import sys
import tempfile
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


def _bytes(x):
    return np.ascontiguousarray(np.float64(x)).tobytes()


# ----------------------------------------------------------------------------
# Shared fixture: synthetic EMIT-like band config (same as test_core.py)
# ----------------------------------------------------------------------------

W = np.linspace(0.381, 2.508, 285)
BP = np.full(285, 0.0074)
CHANELS = np.array([i for i in range(285) if not (126 <= i < 150 or 190 <= i < 210)])
WL = W[CHANELS]

MEDAL = "muscovite_medAl"
MEDHIGH = "muscovite_medhighAl"


def fresh_engine():
    """A private MicaEngine (mutations must not leak between tests)."""
    from cramm import MicaEngine
    return MicaEngine()


def ref_of(e, rule_name):
    """Full-band [285] resampled reference spectrum of a rule (self-ID input)."""
    resampled1 = e.get_resample(W, BP)
    rid = e.rf[rule_name]["reference"]["reflectance_record"]
    return resampled1[rid]


def names_of(results):
    return [x["name"] for x in results]


def results_equal(a, b):
    if names_of(a) != names_of(b):
        return False
    return all(_bytes(x["fit"]) == _bytes(y["fit"]) and _bytes(x["fd"]) == _bytes(y["fd"])
               for x, y in zip(a, b))


def scene_cube(e, rule_name, r=2, c=2):
    """[r, c, 285] float32 cube tiled with the rule's reference spectrum."""
    spec = ref_of(e, rule_name).astype("float32")
    return np.repeat(np.repeat(spec[None, None, :], r, axis=0), c, axis=1)


def assigned_names(result):
    return {result.index[i] for i in result.num}


# ----------------------------------------------------------------------------
# 1. rf_path at construction
# ----------------------------------------------------------------------------

def test_rf_path_construction():
    """A trimmed library loaded via rf_path: only those rules participate."""
    e_full = fresh_engine()
    keep = [MEDAL, "illite_imt1", "kaolinite_wxl"]
    doc = json.loads(json.dumps({"rf": {k: e_full.rf[k] for k in keep},
                                 "mixtures": e_full.mixtures,
                                 "wavelength_map": e_full.wavelength_map}))
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(doc, f)
        tmp = f.name
    try:
        from cramm import MicaEngine
        e = MicaEngine(rf_path=tmp)
        assert set(e.rf) == set(keep), f"loaded rules {sorted(e.rf)} != {keep}"
        res = e.classify_spectrum(ref_of(e_full, MEDAL), WL, W, BP, CHANELS, top_n=10)
        assert res and res[0]["name"] == MEDAL and abs(res[0]["fit"] - 1.0) < 1e-12, \
            f"self-ID broken under trimmed library: {res[:2]}"
        assert set(names_of(res)) <= set(keep), "a trimmed-away rule participated"
    finally:
        os.remove(tmp)


# ----------------------------------------------------------------------------
# 2. constraint modification takes effect
# ----------------------------------------------------------------------------

def test_fit_constraint_modification():
    """Tightening every diagnostic fit_constraint to 1.01 (r2 <= 1) kills the rule."""
    e = fresh_engine()
    spec = ref_of(e, MEDAL)
    base = e.classify_spectrum(spec, WL, W, BP, CHANELS, top_n=10)
    assert base[0]["name"] == MEDAL, f"baseline Top-1 should be {MEDAL}, got {base[0]}"
    for feat in e.rf[MEDAL]["diagnostic_features"]:
        feat["fit_constraint"] = 1.01
    e.invalidate_caches()
    res = e.classify_spectrum(spec, WL, W, BP, CHANELS, top_n=10)
    assert MEDAL not in names_of(res), f"{MEDAL} should be rejected, still in {names_of(res)}"
    assert res[0]["name"] == MEDHIGH, f"new Top-1 should be {MEDHIGH}, got {res[0]}"


# ----------------------------------------------------------------------------
# 3. depth-ratio constraint takes effect
# ----------------------------------------------------------------------------

def test_depth_ratio_constraint():
    """Adding max_depth_ratio_feat1_over_feat0=0.0 rejects unconditionally (d1/d0 >= 0)."""
    e = fresh_engine()
    spec = ref_of(e, MEDAL)
    rule = e.rf[MEDAL]
    assert len(rule["diagnostic_features"]) >= 2, "test needs >= 2 diagnostic features"
    saved = rule.pop("max_depth_ratio_feat1_over_feat0")
    e.invalidate_caches()
    base = e.classify_spectrum(spec, WL, W, BP, CHANELS, top_n=10)
    assert base[0]["name"] == MEDAL, "baseline (constraint removed) should self-ID"
    rule["max_depth_ratio_feat1_over_feat0"] = 0.0  # any d1/d0 >= 0 -> REJECT
    e.invalidate_caches()
    res = e.classify_spectrum(spec, WL, W, BP, CHANELS, top_n=10)
    assert MEDAL not in names_of(res), f"{MEDAL} should be rejected by ratio 0.0"
    assert res[0]["name"] == MEDHIGH, f"new Top-1 should be {MEDHIGH}, got {res[0]}"
    _ = saved


# ----------------------------------------------------------------------------
# 4. a newly added rule is executed
# ----------------------------------------------------------------------------

def test_new_rule_execution():
    """Cloned rule under a new key appears in results with bit-identical fit/fd."""
    e = fresh_engine()
    spec = ref_of(e, MEDAL)
    base = e.classify_spectrum(spec, WL, W, BP, CHANELS, top_n=len(e.rf))
    assert "zz_test_medAl_clone" not in names_of(base)
    e.rf["zz_test_medAl_clone"] = copy.deepcopy(e.rf[MEDAL])
    e.invalidate_caches()
    res = e.classify_spectrum(spec, WL, W, BP, CHANELS, top_n=len(e.rf))
    by_name = {x["name"]: x for x in res}
    assert "zz_test_medAl_clone" in by_name, "new rule was not executed"
    a, b = by_name[MEDAL], by_name["zz_test_medAl_clone"]
    assert _bytes(a["fit"]) == _bytes(b["fit"]) and _bytes(a["fd"]) == _bytes(b["fd"]), \
        "clone and source should score bit-identically"
    assert abs(a["fit"] - 1.0) < 1e-12, f"{MEDAL} self-ID should be fit=1"


# ----------------------------------------------------------------------------
# 5. cache contract: the stale trap and the escape hatch
# ----------------------------------------------------------------------------

def test_cache_contract():
    """Without invalidate_caches: constraint mutation is silently stale; a new key
    raises KeyError. invalidate_caches makes both effective."""
    e = fresh_engine()
    spec = ref_of(e, MEDAL)
    base = e.classify_spectrum(spec, WL, W, BP, CHANELS, top_n=10)
    assert base[0]["name"] == MEDAL

    # (a) mutation without invalidate -> silently stale (byte-identical results)
    for feat in e.rf[MEDAL]["diagnostic_features"]:
        feat["fit_constraint"] = 1.01
    stale = e.classify_spectrum(spec, WL, W, BP, CHANELS, top_n=10)
    assert results_equal(base, stale), \
        "mutation leaked into results without invalidate_caches (cache key must stay rule-agnostic)"

    # (b) adding a key without invalidate -> KeyError (compiled dict lacks the key)
    # (clone an UNMUTATED rule so that step (c) can verify the new key is judged)
    e.rf["zz_test_illite_clone"] = copy.deepcopy(e.rf["illite_imt1"])
    try:
        e.classify_spectrum(spec, WL, W, BP, CHANELS)
        raise AssertionError("adding a rule without invalidate_caches should raise KeyError")
    except KeyError:
        pass

    # (c) invalidate -> mutation effective (medAl killed) AND new key judged
    # (clone scores bit-identically to its source rule)
    e.invalidate_caches()
    res = e.classify_spectrum(spec, WL, W, BP, CHANELS, top_n=len(e.rf))
    assert MEDAL not in names_of(res), "mutation did not take effect after invalidate_caches"
    by_name = {x["name"]: x for x in res}
    assert "zz_test_illite_clone" in by_name, "new rule missing after invalidate_caches"
    a, b = by_name["illite_imt1"], by_name["zz_test_illite_clone"]
    assert _bytes(a["fit"]) == _bytes(b["fit"]) and _bytes(a["fd"]) == _bytes(b["fd"])


# ----------------------------------------------------------------------------
# 6. scene level: killing the winner changes the assignment
# ----------------------------------------------------------------------------

def test_scene_rule_modification():
    """classify(): baseline assigns medAl; after ratio=0.0 + invalidate no pixel is medAl."""
    e = fresh_engine()
    cube = scene_cube(e, MEDAL)
    base = e._classifier.classify(cube, WL, W, BP, CHANELS, n_workers=1)
    assert assigned_names(base) == {MEDAL}, f"baseline assignment {assigned_names(base)}"

    e.rf[MEDAL]["max_depth_ratio_feat1_over_feat0"] = 0.0
    e.invalidate_caches()
    res = e._classifier.classify(cube, WL, W, BP, CHANELS, n_workers=1)
    assert MEDAL not in assigned_names(res), f"{MEDAL} still assigned after kill"
    assert assigned_names(res) == {MEDHIGH}, f"expected reassignment-free win of {MEDHIGH}"
    assert (res.fit > 0).all(), "pixels should still be classified"


# ----------------------------------------------------------------------------
# 7. scene level: absorption_center_range window modification re-arbitrates
# ----------------------------------------------------------------------------

def test_absorption_center_window_modification():
    """medAl pixel (fitted center ~2.2021 um): moving the windows so the center
    leaves medAl's range and enters medhighAl's reassigns medAl -> medhighAl."""
    e = fresh_engine()
    cube = scene_cube(e, MEDAL)
    base = e._classifier.classify(cube, WL, W, BP, CHANELS, n_workers=1)
    assert assigned_names(base) == {MEDAL}
    cen = float(base.mus_center[0])
    assert 2.2 <= cen < 2.206, f"fitted center {cen} should sit in the medAl window"

    rule_a, rule_b = e.rf[MEDAL], e.rf[MEDHIGH]
    win_a = rule_a["diagnostic_features"][0]["absorption_center_range"]
    win_b = rule_b["diagnostic_features"][0]["absorption_center_range"]
    # medAl window no longer contains the center; medhighAl window now does
    rule_a["diagnostic_features"][0]["absorption_center_range"] = [2.204, 2.206]
    rule_b["diagnostic_features"][0]["absorption_center_range"] = [2.195, 2.203]
    assert not (2.204 <= cen < 2.206) and (2.195 <= cen < 2.203), "test window setup error"
    e.invalidate_caches()
    res = e._classifier.classify(cube, WL, W, BP, CHANELS, n_workers=1)
    assert assigned_names(res) == {MEDHIGH}, \
        f"wavelength re-arbitration should move pixels to {MEDHIGH}, got {assigned_names(res)}"
    _ = (win_a, win_b)


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    print("== custom rule-library verification (synthetic bands, no NC) ==", flush=True)
    run("rf_path construction loads trimmed library", test_rf_path_construction)
    run("fit_constraint modification kills rule", test_fit_constraint_modification)
    run("depth-ratio constraint addition kills rule", test_depth_ratio_constraint)
    run("newly added rule is executed (bit-identical clone)", test_new_rule_execution)
    run("cache contract: stale trap / KeyError / invalidate", test_cache_contract)
    run("scene: killing winner changes assignment", test_scene_rule_modification)
    run("scene: absorption_center_range window re-arbitration", test_absorption_center_window_modification)

    n_ok = sum(1 for s, _ in RESULTS if s == "OK")
    n_skip = sum(1 for s, _ in RESULTS if s == "SKIP")
    n_fail = sum(1 for s, _ in RESULTS if s == "FAIL")
    print(f"\nSummary: {n_ok} passed / {n_skip} skipped / {n_fail} failed")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
