#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Audit carbonate per-tier arbitration and post-refit consistency on a full EMIT scene."""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "repo" / "src"))
from cramm.classifier import (  # noqa: E402
    CARBONATE_ABUNDANT_MINERALS, CARBONATE_MINERALS, CARBONATE_PLAIN_MINERALS,
    _get_quadratic_center, _judge_reference_entry,
)
from cramm.mica_engine import MicaEngine  # noqa: E402

NC = REPO / "EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
OUT = REPO / "output/carbonate_arbitration_scene_v1"
ABUNDANT = set(CARBONATE_ABUNDANT_MINERALS)
PLAIN = set(CARBONATE_PLAIN_MINERALS)


def transition_counts(before, after, names, indices, selected):
    counts = Counter()
    for i in indices:
        mask = selected & (before == i)
        for j in np.unique(after[mask]):
            counts[f"{names[i]}→{names[j]}"] += int((after[mask] == j).sum())
    return dict(sorted(counts.items()))


def main():
    reuse = "--reuse" in sys.argv
    OUT.mkdir(exist_ok=True)
    if not reuse and any(OUT.iterdir()):
        raise SystemExit(f"Output directory must be empty: {OUT}")
    engine = MicaEngine()
    spectrum, _, _, w, bp, wl, chanels = engine.load_emit(str(NC))
    shape = (1280, 1242)
    if reuse:
        saved = np.load(OUT / "scene_arrays.npz", allow_pickle=False)
        current_num = saved["current_num"]
        pure_num = saved["pure_num"]
        current_center = saved["current_cal_center"]
        pure_center = saved["pure_cal_center"]
        names = list(saved["index"])
    else:
        current = engine._classifier.classify(spectrum, wl, w, bp, chanels, n_workers=4)
        pure_engine = MicaEngine()
        for name in CARBONATE_ABUNDANT_MINERALS + CARBONATE_PLAIN_MINERALS:
            pure_engine.rf[name]["diagnostic_features"][0].pop("absorption_center_range", None)
        pure_engine.invalidate_caches()
        pure = pure_engine._classifier.classify(spectrum, wl, w, bp, chanels, n_workers=4)
        current_num = current.num.reshape(shape)
        pure_num = pure.num.reshape(shape)
        current_center = current.cal_center.reshape(shape)
        pure_center = pure.cal_center.reshape(shape)
        names = list(current.index)
        np.savez_compressed(
            OUT / "scene_arrays.npz", index=np.asarray(names, dtype="U42"),
            pure_num=pure_num, current_num=current_num,
            pure_cal_center=pure_center, current_cal_center=current_center,
        )
    abundant_indices = [names.index(n) for n in CARBONATE_ABUNDANT_MINERALS]
    plain_indices = [names.index(n) for n in CARBONATE_PLAIN_MINERALS]
    carbonate_indices = [names.index(n) for n in CARBONATE_MINERALS]
    abundant_mask = np.isin(pure_num, abundant_indices)
    plain_mask = np.isin(pure_num, plain_indices)
    carbonate_mask = np.isin(pure_num, carbonate_indices)
    changed = current_num != pure_num

    def tier_labels(num):
        labels = np.full(num.shape, "non-carbonate", dtype="U16")
        labels[np.isin(num, abundant_indices)] = "abundant"
        labels[np.isin(num, plain_indices)] = "plain"
        return labels

    cross_tier = tier_labels(current_num) != tier_labels(pure_num)
    rows, cols = np.nonzero(changed & carbonate_mask)
    resampled = engine.get_resample(w, bp)
    verification = []
    for r, c in zip(rows, cols):
        before_name = names[pure_num[r, c]]
        after_name = names[current_num[r, c]]
        endpoints = engine.rf[after_name]["diagnostic_features"][0]["continuum_endpoints"]
        expected = float(_get_quadratic_center(
            spectrum[r, c, chanels][None, :], wl, endpoints, np.array([True]))[0])
        lo, hi = engine.rf[after_name]["diagnostic_features"][0]["absorption_center_range"]
        target_fit_array, _ = _judge_reference_entry(
            spectrum[r, c, chanels][None, :], wl,
            engine.rf[after_name], resampled, chanels,
        )
        target_fit = float(target_fit_array[0])
        target_accepted = bool(np.isfinite(target_fit) and target_fit > 0)
        expected_inside = bool(lo <= expected < hi)
        post = float(current_center[r, c])
        pre = float(pure_center[r, c])
        fallback = not expected_inside and post == pre
        consistent = (post == expected) if expected_inside else (post == pre)
        verification.append({
            "row": int(r), "col": int(c), "before": before_name, "after": after_name,
            "pre_center_um": pre, "expected_refit_center_um": expected,
            "post_center_um": post, "expected_inside_target": expected_inside,
            "target_fit": target_fit, "target_accepted": target_accepted,
            "fallback_to_pre_center": fallback, "consistent": consistent,
        })

    with (OUT / "refit_verification.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(verification[0])) if verification else None
        if writer:
            writer.writeheader(); writer.writerows(verification)

    summary = {
        "scene": NC.name,
        "verification_input": "reused scene_arrays.npz" if reuse else "fresh classification",
        "current_configuration": "per-tier carbonate arbitration with post-refit target-window fallback",
        "changed_carbonate_labels": int((changed & carbonate_mask).sum()),
        "abundant_flips": int((changed & abundant_mask).sum()),
        "plain_flips": int((changed & plain_mask).sum()),
        "abundant_transitions": transition_counts(
            pure_num, current_num, names, abundant_indices, abundant_mask),
        "plain_transitions": transition_counts(
            pure_num, current_num, names, plain_indices, plain_mask),
        "cross_tier_changes": int(cross_tier.sum()),
        "non_carbonate_label_changes": int((changed & ~carbonate_mask).sum()),
        "refit_verified_changes": len(verification),
        "target_acceptance_failures": sum(not r["target_accepted"] for r in verification),
        "refit_fallbacks": sum(r["fallback_to_pre_center"] for r in verification),
        "post_target_inconsistencies": sum(not r["consistent"] for r in verification),
        "inconsistent_examples": [r for r in verification if not r["consistent"]][:10],
        "fallback_examples": [r for r in verification if r["fallback_to_pre_center"]][:10],
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
