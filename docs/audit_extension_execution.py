#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Prove execution of depth-ratio and arbitration gates on all synthetic spectra."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from cramm.classifier import (  # noqa: E402
    CARBONATE_ABUNDANT_MINERALS, CARBONATE_PLAIN_MINERALS, CHLORITE_MINERALS,
    MUSCOVITE_MINERALS, InvalidLeftEndPointError, InvalidRangeError,
    InvalidRightEndPointError, _judge_reference_entry,
)
from cramm.mica_engine import MicaEngine  # noqa: E402


def accepted(fit):
    return np.isfinite(fit) & (fit > 0)


def winners(fit, names):
    score = np.where(np.isfinite(fit), fit, 0.0)
    num = score.argmax(axis=1)
    fired = score.max(axis=1) > 0
    return np.where(fired, names[num], ""), fired


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=REPO / "output/synthetic_emit_v1")
    parser.add_argument("--predictions", type=Path,
                        default=REPO / "output/synthetic_emit_ablation_v2")
    parser.add_argument("--output", type=Path,
                        default=REPO / "output/synthetic_execution_audit_v1")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise SystemExit(f"Output directory must be empty: {out}")

    data = np.load(args.data / "spectra.npz", allow_pickle=False)
    pred = np.load(args.predictions / "predictions.npz", allow_pickle=False)
    spectra, masks = data["reflectance"], data["valid_mask"]
    w, bp = data["band_centers_um"], data["fwhm_um"]
    n = len(spectra)
    on_engine = MicaEngine()
    off_engine = MicaEngine()
    for rule in off_engine.rf.values():
        rule.pop("max_depth_ratio_feat1_over_feat0", None)
    off_engine.invalidate_caches()
    names = np.asarray(list(on_engine.rf), dtype="U42")
    nr = len(names)
    fit_on = np.full((n, nr), np.nan)
    fit_off = np.full((n, nr), np.nan)
    fit_compiled = np.full((n, nr), np.nan)
    direct_compiled_errors = Counter()
    groups = defaultdict(list)
    for i, mask in enumerate(masks):
        groups[mask.tobytes()].append(i)

    for mask_bytes, indices_list in groups.items():
        indices = np.asarray(indices_list, dtype=int)
        chanels = np.flatnonzero(masks[indices[0]])
        wl = w[chanels]
        selected = np.ascontiguousarray(spectra[indices][:, chanels])
        resampled_on = on_engine.get_resample(w, bp)
        resampled_off = off_engine.get_resample(w, bp)
        compiled = on_engine._classifier._get_compiled_rules(w, bp, wl, chanels)
        for k, name in enumerate(names):
            for mode in ("direct_on", "direct_off", "compiled_on"):
                try:
                    if mode == "direct_on":
                        fit, _ = _judge_reference_entry(
                            selected, wl, on_engine.rf[str(name)], resampled_on, chanels)
                    elif mode == "direct_off":
                        fit, _ = _judge_reference_entry(
                            selected, wl, off_engine.rf[str(name)], resampled_off, chanels)
                    else:
                        fit, _ = _judge_reference_entry(
                            selected, wl, None, None, chanels, compiled=compiled[str(name)])
                except (InvalidRangeError, InvalidLeftEndPointError, InvalidRightEndPointError):
                    direct_compiled_errors[mode] += 1
                    continue
                if mode == "direct_on":
                    fit_on[indices, k] = fit
                elif mode == "direct_off":
                    fit_off[indices, k] = fit
                else:
                    fit_compiled[indices, k] = fit

    on_ok, off_ok, compiled_ok = accepted(fit_on), accepted(fit_off), accepted(fit_compiled)
    both_on = on_ok & off_ok
    checks = {
        "compiled_direct_bit_exact": bool(np.array_equal(fit_on, fit_compiled, equal_nan=True)),
        "depth_ratio_only_removes_candidates": bool(not (on_ok & ~off_ok).any()),
        "retained_candidate_fit_bit_exact": bool(np.array_equal(
            fit_on[both_on], fit_off[both_on], equal_nan=True)),
    }
    pre_off, fired_off = winners(fit_off, names)
    pre_on, fired_on = winners(fit_on, names)
    configs = list(pred["config"])
    checks["off_direct_top1_matches_M00"] = bool(np.array_equal(
        pre_off, pred["predicted_rule"][configs.index("M00")]))
    checks["on_direct_top1_matches_M10"] = bool(np.array_equal(
        pre_on, pred["predicted_rule"][configs.index("M10")]))
    checks["off_direct_fire_matches_M00"] = bool(np.array_equal(
        fired_off, pred["fired"][configs.index("M00")]))
    checks["on_direct_fire_matches_M10"] = bool(np.array_equal(
        fired_on, pred["fired"][configs.index("M10")]))

    arbitration = {}
    for before_name, after_name, before_fit, before_pred in (
        ("M00", "M01", fit_off, pre_off),
        ("M10", "M11", fit_on, pre_on),
    ):
        after_pred = pred["predicted_rule"][configs.index(after_name)]
        after_fired = pred["fired"][configs.index(after_name)]
        changed = before_pred != after_pred
        target_ok = []
        for i in np.flatnonzero(changed & (after_pred != "")):
            target_k = int(np.flatnonzero(names == after_pred[i])[0])
            target_ok.append(bool(accepted(before_fit[i:i + 1, target_k])[0]))
        family_counts = Counter()
        for i in np.flatnonzero(changed):
            target = str(after_pred[i])
            if target in MUSCOVITE_MINERALS:
                family_counts["muscovite"] += 1
            elif target in CHLORITE_MINERALS:
                family_counts["chlorite"] += 1
            elif target in CARBONATE_ABUNDANT_MINERALS + CARBONATE_PLAIN_MINERALS:
                family_counts["carbonate"] += 1
            elif not target:
                family_counts["no_fire"] += 1
            else:
                family_counts["other"] += 1
        arbitration[f"{before_name}_to_{after_name}"] = {
            "changed_predictions": int(changed.sum()),
            "target_accepted_before_arbitration": int(sum(target_ok)),
            "target_acceptance_failures": int(len(target_ok) - sum(target_ok)),
            "fire_state_changes": int((fired_on != after_fired).sum()
                                      if before_name == "M10" else (fired_off != after_fired).sum()),
            "by_target_family": dict(family_counts),
            "transitions": dict(Counter(
                f"{before_pred[i]}→{after_pred[i]}" for i in np.flatnonzero(changed)
            )),
        }
    checks["all_arbitration_targets_preaccepted"] = all(
        x["target_acceptance_failures"] == 0 for x in arbitration.values())
    checks["arbitration_preserves_fire_state"] = all(
        x["fire_state_changes"] == 0 for x in arbitration.values())

    rejected = off_ok & ~on_ok
    rejection_counts = rejected.sum(axis=0)
    by_rule = []
    for k, name in enumerate(names):
        if "max_depth_ratio_feat1_over_feat0" not in on_engine.rf[str(name)]:
            continue
        by_rule.append({
            "rule": str(name),
            "threshold": on_engine.rf[str(name)]["max_depth_ratio_feat1_over_feat0"],
            "baseline_accepted": int(off_ok[:, k].sum()),
            "rejected_by_depth_ratio": int(rejection_counts[k]),
            "retained": int(on_ok[:, k].sum()),
        })
    with (out / "depth_ratio_execution_by_rule.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(by_rule[0]))
        writer.writeheader(); writer.writerows(by_rule)

    np.savez_compressed(out / "candidate_fit_matrices.npz",
                        rule=names, fit_depth_off=fit_off,
                        fit_depth_on=fit_on, fit_depth_on_compiled=fit_compiled)
    summary = {
        "evidence_scope": "Execution audit on CRAMM-reference-derived synthetic EMIT data.",
        "n_spectra": n, "n_rules": nr, "valid_mask_groups": len(groups),
        "checks": checks,
        "invalid_range_events_by_path": dict(direct_compiled_errors),
        "depth_ratio": {
            "baseline_accepted_candidates": int(off_ok.sum()),
            "accepted_after_depth_ratio": int(on_ok.sum()),
            "rejected_by_depth_ratio": int(rejected.sum()),
            "rules_with_actual_rejections": sum(r["rejected_by_depth_ratio"] > 0 for r in by_rule),
            "by_rule": by_rule,
        },
        "arbitration": arbitration,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("WROTE", out)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
