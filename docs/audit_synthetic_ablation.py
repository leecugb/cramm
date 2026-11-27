#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Audit arbitration degradations and depth-ratio changes on synthetic EMIT data."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "repo" / "src"))
from cramm.classifier import _diagnostic_feature  # noqa: E402
from cramm.mica_engine import MicaEngine  # noqa: E402


def center_details(spectrum_full, chanels, w, rule):
    """Reproduce the quadratic center and expose its triplet/curvature gates."""
    wl = w[chanels]
    spectrum = spectrum_full[chanels].reshape(1, -1)
    endpoints = rule["diagnostic_features"][0]["continuum_endpoints"]
    mask = (wl <= endpoints[3]) & (wl >= endpoints[0])
    left = (wl <= endpoints[1]) & (wl >= endpoints[0])
    right = (wl <= endpoints[3]) & (wl >= endpoints[2])
    x_av = np.array([wl[left].mean(), wl[right].mean()])
    y_av = np.array([spectrum[0, left].mean(), spectrum[0, right].mean()])
    continuum = y_av[0] + (y_av[1] - y_av[0]) / (x_av[1] - x_av[0]) * (wl[mask] - x_av[0])
    con = spectrum[0, mask] / continuum
    index = int(con.argmin())
    if index == 0 or index == len(con) - 1:
        return {"center_um": float("nan"), "inside_bracket": False,
                "positive_curvature": False, "curvature": float("nan")}
    x1, x2, x3 = wl[mask][index - 1:index + 2]
    y1, y2, y3 = con[index - 1:index + 2]
    with np.errstate(invalid="ignore", divide="ignore"):
        temp = ((y2 - y1) * (x3**2 - x2**2) - (y3 - y2) * (x2**2 - x1**2)) / (
            (y3 - y2) * (x2 - x1) - (y2 - y1) * (x3 - x2)) / 2
        center = -temp
        curvature = ((y3 - y2) / (x3 - x2) - (y2 - y1) / (x2 - x1)) / (x3 - x1)
    return {
        "center_um": float(center), "x1_um": float(x1), "x2_um": float(x2), "x3_um": float(x3),
        "y1": float(y1), "y2": float(y2), "y3": float(y3),
        "curvature": float(curvature), "positive_curvature": bool(curvature > 0),
        "inside_bracket": bool(x1 <= center <= x3),
    }


def shared_boundary(source_rule, target_rule, rf):
    if target_rule not in rf:
        return float("nan")
    a = rf[source_rule]["diagnostic_features"][0]["absorption_center_range"]
    b = rf[target_rule]["diagnostic_features"][0]["absorption_center_range"]
    if abs(a[1] - b[0]) < 1e-12:
        return float(a[1])
    if abs(b[1] - a[0]) < 1e-12:
        return float(b[1])
    return float("nan")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=REPO / "output/synthetic_emit_v1")
    parser.add_argument("--predictions", type=Path,
                        default=REPO / "output/synthetic_emit_ablation_v2")
    parser.add_argument("--output", type=Path,
                        default=REPO / "output/synthetic_emit_ablation_audit_v1")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise SystemExit(f"Output directory must be empty: {out}")

    with (args.data / "truth.csv").open(encoding="utf-8") as f:
        truth = list(csv.DictReader(f))
    data = np.load(args.data / "spectra.npz", allow_pickle=False)
    pred = np.load(args.predictions / "predictions.npz", allow_pickle=False)
    configs = list(pred["config"])
    i00, i10, i01 = configs.index("M00"), configs.index("M10"), configs.index("M01")
    reflectance = data["reflectance"]
    noise_free = data["noise_free_reflectance"]
    masks = data["valid_mask"]
    w, bp = data["band_centers_um"], data["fwhm_um"]
    engine = MicaEngine()
    rf = engine.rf

    def clean_single_index(rec):
        return next(j for j, other in enumerate(truth)
                    if other["sample_kind"] == "single_reference"
                    and other["source_rule_1"] == rec["source_rule_1"]
                    and other["snr_db_target"] == "")

    arbitration_rows = []
    for i, rec in enumerate(truth):
        if rec["sample_kind"] != "single_reference":
            continue
        source = rec["source_rule_1"]
        if not (pred["exact_rule"][i00, i] and not pred["exact_rule"][i01, i]):
            continue
        target = str(pred["predicted_rule"][i01, i])
        if source not in {
            "muscovite_lowAl", "muscovite_medAl", "muscovite_medhighAl", "muscovite_Fe-rich",
            "chlorite_lowFe", "clinochlore", "clinochlore_Fe", "thuringite",
        }:
            continue
        chanels = np.flatnonzero(masks[i])
        noisy = center_details(reflectance[i], chanels, w, rf[source])
        same_clean = center_details(noise_free[i], chanels, w, rf[source])
        base_i = clean_single_index(rec)
        base_channels = np.flatnonzero(masks[base_i])
        base_clean = center_details(reflectance[base_i], base_channels, w, rf[source])
        boundary = shared_boundary(source, target, rf)
        center_field = "mus_center" if source.startswith("muscovite") else "chl_center"
        stored = float(pred[center_field][i00, i])
        row = {
            "sample_id": rec["sample_id"], "snr_db": rec["snr_db_target"],
            "continuum_slope_per_um": rec["continuum_slope_per_um"],
            "source_rule": source, "arbitrated_rule": target, "boundary_um": boundary,
            "baseline_clean_center_um": base_clean["center_um"],
            "same_condition_noise_free_center_um": same_clean["center_um"],
            "noisy_center_um": noisy["center_um"],
            "stored_M00_center_um": stored,
            "center_storage_abs_diff_um": abs(stored - noisy["center_um"]),
            "continuum_shift_nm": 1000 * (same_clean["center_um"] - base_clean["center_um"]),
            "noise_shift_nm": 1000 * (noisy["center_um"] - same_clean["center_um"]),
            "total_shift_nm": 1000 * (noisy["center_um"] - base_clean["center_um"]),
            "noisy_distance_to_boundary_nm": 1000 * abs(noisy["center_um"] - boundary),
            "baseline_distance_to_boundary_nm": 1000 * abs(base_clean["center_um"] - boundary),
            "baseline_to_noisy_crosses_boundary": bool(
                (base_clean["center_um"] - boundary) * (noisy["center_um"] - boundary) <= 0),
            "positive_curvature": noisy["positive_curvature"],
            "inside_bracket": noisy["inside_bracket"],
            "curvature": noisy["curvature"],
            "x1_um": noisy.get("x1_um"), "x2_um": noisy.get("x2_um"), "x3_um": noisy.get("x3_um"),
            "M00_fit": float(pred["fit"][i00, i]), "M01_fit": float(pred["fit"][i01, i]),
        }
        arbitration_rows.append(row)

    # Independent engines reproduce the two depth-ratio configurations.
    off = MicaEngine()
    for rule in off.rf.values():
        rule.pop("max_depth_ratio_feat1_over_feat0", None)
    off.invalidate_caches()
    on = MicaEngine()

    def accepted(engine, i):
        chanels = np.flatnonzero(masks[i])
        wl = w[chanels]
        result = engine.classify_spectrum(
            reflectance[i].reshape(1, -1), wl, w, bp, chanels, top_n=len(engine.rf))
        return result

    def ratio_details(engine, i, rule_name, spectrum):
        chanels = np.flatnonzero(masks[i])
        wl = w[chanels]
        selected = spectrum[chanels].reshape(1, -1)
        compiled = engine._classifier._get_compiled_rules(w, bp, wl, chanels)[rule_name]
        raw = []
        for pre, weight, cc, fc, dc in compiled["diag"][:2]:
            _, _, _, depth = _diagnostic_feature(
                selected, None, wl, None, weight, cc, fc, dc, pre=pre)
            raw.append(float(depth[0]))
        ratio = raw[1] / raw[0] if raw[0] and np.isfinite(raw[0]) else float("nan")
        threshold = compiled["ratio_max"]
        explained = bool(np.isfinite(raw[0]) and np.isfinite(raw[1])
                         and raw[0] > 0 and ratio >= threshold)
        return {"raw0": raw[0], "raw1": raw[1], "ratio": ratio,
                "threshold": threshold, "reject_explained": explained}

    depth_change_rows = []
    depth_rejection_rows = []
    top1_mismatches = []
    for i, rec in enumerate(truth):
        old_rule = str(pred["predicted_rule"][i00, i])
        new_rule = str(pred["predicted_rule"][i10, i])
        if old_rule == new_rule and pred["fired"][i00, i] == pred["fired"][i10, i]:
            continue
        before = accepted(off, i)
        after = accepted(on, i)
        before_names = {r["name"] for r in before}
        after_names = {r["name"] for r in after}
        before_top = before[0]["name"] if before else ""
        after_top = after[0]["name"] if after else ""
        if before_top != old_rule or after_top != new_rule:
            top1_mismatches.append(rec["sample_id"])
        rejected = sorted(before_names - after_names)
        added = sorted(after_names - before_names)
        old_exact = bool(pred["exact_rule"][i00, i])
        new_exact = bool(pred["exact_rule"][i10, i])
        old_dominant = bool(pred["dominant_hit"][i00, i])
        new_dominant = bool(pred["dominant_hit"][i10, i])
        if old_exact and not new_exact:
            outcome = "true_reference_rule_suppressed"
        elif not old_exact and new_exact:
            outcome = "false_positive_suppressed_reference_recovered"
        elif old_dominant and not new_dominant:
            outcome = "dominant_family_suppressed_or_displaced"
        elif not old_dominant and new_dominant:
            outcome = "non_dominant_assignment_suppressed_dominant_recovered"
        elif not new_rule:
            outcome = "all_output_suppressed_without_truth_recovery"
        else:
            outcome = "winner_rejected_other_assignment"
        depth_change_rows.append({
            "sample_id": rec["sample_id"], "sample_kind": rec["sample_kind"],
            "snr_db": rec["snr_db_target"] or "clean",
            "continuum_slope_per_um": rec["continuum_slope_per_um"],
            "source_rule_1": rec["source_rule_1"], "source_rule_2": rec["source_rule_2"],
            "fraction_1": rec["fraction_1"], "M00_rule": old_rule, "M10_rule": new_rule,
            "M00_fired": int(pred["fired"][i00, i]), "M10_fired": int(pred["fired"][i10, i]),
            "rejected_candidates": ";".join(rejected), "added_candidates": ";".join(added),
            "M00_winner_rejected": old_rule in rejected,
            "M00_winner_retained_but_changed": old_rule not in rejected and old_rule != new_rule,
            "outcome": outcome,
        })
        for rule_name in rejected:
            noisy = ratio_details(on, i, rule_name, reflectance[i])
            clean = ratio_details(on, i, rule_name, noise_free[i])
            if np.isfinite(clean["ratio"]) and np.isfinite(noisy["ratio"]):
                if clean["ratio"] < clean["threshold"] and noisy["ratio"] >= noisy["threshold"]:
                    crossing = "noise_induced_threshold_crossing"
                elif clean["ratio"] >= clean["threshold"] and noisy["ratio"] >= noisy["threshold"]:
                    crossing = "already_above_threshold_without_noise"
                else:
                    crossing = "other_ratio_pattern"
            else:
                crossing = "invalid_clean_or_noisy_depth"
            depth_rejection_rows.append({
                "sample_id": rec["sample_id"], "sample_kind": rec["sample_kind"],
                "snr_db": rec["snr_db_target"] or "clean",
                "continuum_slope_per_um": rec["continuum_slope_per_um"],
                "source_rule_1": rec["source_rule_1"], "source_rule_2": rec["source_rule_2"],
                "M00_rule": old_rule, "M10_rule": new_rule, "rejected_rule": rule_name,
                "was_M00_winner": rule_name == old_rule,
                "noisy_raw0": noisy["raw0"], "noisy_raw1": noisy["raw1"],
                "noisy_ratio": noisy["ratio"], "threshold": noisy["threshold"],
                "noise_free_raw0": clean["raw0"], "noise_free_raw1": clean["raw1"],
                "noise_free_ratio": clean["ratio"], "ratio_crossing": crossing,
                "noisy_reject_explained": noisy["reject_explained"],
                "outcome": outcome,
            })

    with (out / "arbitration_degradations.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(arbitration_rows[0]))
        writer.writeheader(); writer.writerows(arbitration_rows)
    with (out / "depth_ratio_changes.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(depth_change_rows[0]))
        writer.writeheader(); writer.writerows(depth_change_rows)
    with (out / "depth_ratio_rejections.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(depth_rejection_rows[0]))
        writer.writeheader(); writer.writerows(depth_rejection_rows)

    summary = {
        "evidence_scope": "Reference-derived synthetic EMIT audit; not independent validation.",
        "arbitration": {
            "n_degradations": len(arbitration_rows),
            "all_at_40dB": all(r["snr_db"] == "40.0" for r in arbitration_rows),
            "positive_curvature_count": sum(r["positive_curvature"] for r in arbitration_rows),
            "inside_bracket_count": sum(r["inside_bracket"] for r in arbitration_rows),
            "boundary_crossed_count": sum(r["baseline_to_noisy_crosses_boundary"] for r in arbitration_rows),
            "max_center_storage_abs_diff_um": max(r["center_storage_abs_diff_um"] for r in arbitration_rows),
            "median_abs_noise_shift_nm": float(np.median([abs(r["noise_shift_nm"]) for r in arbitration_rows])),
            "median_distance_to_boundary_nm": float(np.median([r["noisy_distance_to_boundary_nm"] for r in arbitration_rows])),
            "by_transition": dict(Counter(f"{r['source_rule']}→{r['arbitrated_rule']}" for r in arbitration_rows)),
        },
        "depth_ratio": {
            "n_changed_samples": len(depth_change_rows),
            "n_rejected_candidates": len(depth_rejection_rows),
            "winner_rejected_count": sum(r["M00_winner_rejected"] for r in depth_change_rows),
            "winner_retained_but_changed_count": sum(r["M00_winner_retained_but_changed"] for r in depth_change_rows),
            "added_candidate_samples": sum(bool(r["added_candidates"]) for r in depth_change_rows),
            "top1_reproduction_mismatches": top1_mismatches,
            "unexplained_rejections": sum(not r["noisy_reject_explained"] for r in depth_rejection_rows),
            "outcomes": dict(Counter(r["outcome"] for r in depth_change_rows)),
            "ratio_crossing": dict(Counter(r["ratio_crossing"] for r in depth_rejection_rows)),
            "no_fire_after_count": sum(not r["M10_rule"] for r in depth_change_rows),
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Synthetic EMIT ablation audit", "",
        "**Reference-derived development evidence only.**", "",
        "## Arbitration degradations", "",
        f"N = {len(arbitration_rows)}; positive curvature = {summary['arbitration']['positive_curvature_count']}; "
        f"inside bracket = {summary['arbitration']['inside_bracket_count']}; "
        f"boundary crossed = {summary['arbitration']['boundary_crossed_count']}.", "",
        "| Sample | Transition | SNR | Baseline center | Noisy center | Noise shift nm | Boundary distance nm | Curvature>0 | Inside |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in arbitration_rows:
        lines.append(
            f"| {r['sample_id']} | {r['source_rule']}→{r['arbitrated_rule']} | {r['snr_db']} | "
            f"{r['baseline_clean_center_um']:.6f} | {r['noisy_center_um']:.6f} | "
            f"{r['noise_shift_nm']:.3f} | {r['noisy_distance_to_boundary_nm']:.3f} | "
            f"{r['positive_curvature']} | {r['inside_bracket']} |"
        )
    lines.extend(["", "## Depth-ratio changes", "",
                  "| Sample | Kind | SNR | M00 → M10 | Rejected candidates | Outcome |",
                  "|---|---|---:|---|---|---|"])
    for r in depth_change_rows:
        lines.append(
            f"| {r['sample_id']} | {r['sample_kind']} | {r['snr_db']} | "
            f"{r['M00_rule'] or 'NO_FIRE'}→{r['M10_rule'] or 'NO_FIRE'} | "
            f"{r['rejected_candidates']} | {r['outcome']} |"
        )
    lines.extend(["", "## Reproduction checks", "",
                  f"Top-1 mismatches: {len(top1_mismatches)}; "
                  f"unexplained ratio rejections: {summary['depth_ratio']['unexplained_rejections']}; "
                  f"winner retained but changed: {summary['depth_ratio']['winner_retained_but_changed_count']}.", ""])
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("WROTE", out)


if __name__ == "__main__":
    main()
