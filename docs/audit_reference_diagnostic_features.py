#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Audit every CRAMM reference rule and diagnostic feature on 1 nm and EMIT grids."""
from __future__ import annotations

import contextlib
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from cramm.classifier import (  # noqa: E402
    InvalidLeftEndPointError, InvalidRangeError, InvalidRightEndPointError,
    _continuum_constraints_list, _diagnostic_feature, _get_fit,
    _get_quadratic_center,
)
from cramm.mica_engine import MicaEngine  # noqa: E402

OUT = Path(os.environ.get("CRAMM_FEATURE_AUDIT_OUT", ROOT / "output/reference_diagnostic_audit_v3"))
NC = ROOT / "EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
EXC = (InvalidRangeError, InvalidLeftEndPointError, InvalidRightEndPointError)


def center_diagnostics(spec, wl, endpoints):
    """Expose center status without changing the production center result."""
    mask = (wl <= endpoints[3]) & (wl >= endpoints[0])
    left = (wl <= endpoints[1]) & (wl >= endpoints[0])
    right = (wl <= endpoints[3]) & (wl >= endpoints[2])
    x_av = np.array([wl[left].mean(), wl[right].mean()])
    y_av = np.array([spec[0, left].mean(), spec[0, right].mean()])
    continuum = y_av[0] + (y_av[1] - y_av[0]) / (x_av[1] - x_av[0]) * (wl[mask] - x_av[0])
    con = spec[0, mask] / continuum
    index = int(con.argmin())
    if index == 0 or index == len(con) - 1:
        return {"status": "EDGE_MINIMUM", "curvature": np.nan, "inside_triplet": False}
    x1, x2, x3 = wl[mask][index - 1:index + 2]
    y1, y2, y3 = con[index - 1:index + 2]
    with np.errstate(invalid="ignore", divide="ignore"):
        temp = ((y2 - y1) * (x3**2 - x2**2) - (y3 - y2) * (x2**2 - x1**2)) / (
            (y3 - y2) * (x2 - x1) - (y2 - y1) * (x3 - x2)) / 2
        center = -temp
        curvature = ((y3 - y2) / (x3 - x2) - (y2 - y1) / (x2 - x1)) / (x3 - x1)
    if not np.isfinite(center):
        status = "NONFINITE_VERTEX"
    elif not (x1 <= center <= x3):
        status = "OUTSIDE_TRIPLET"
    elif curvature <= 0:
        status = "NEGATIVE_CURVATURE"
    elif not (endpoints[0] <= center <= endpoints[3]):
        status = "OUTSIDE_FEATURE"
    else:
        status = "VALID"
    return {"status": status, "curvature": float(curvature),
            "inside_triplet": bool(x1 <= center <= x3)}


def main():
    OUT.mkdir(exist_ok=True)
    if any(OUT.iterdir()):
        raise SystemExit(f"Output directory must be empty: {OUT}")
    engine = MicaEngine()
    rf = engine.rf
    bundle = np.load(ROOT / "cramm/data/rf77_splib07_1nm.npz", allow_pickle=False)
    grid, rules, labels, spectra = (bundle[k] for k in ("grid", "rule", "label", "spectra"))
    with Dataset(NC) as ds:
        group = ds["sensor_band_parameters"]
        w = group["wavelengths"][:].data / 1000.0
        bp = group["fwhm"][:].data / 1000.0
        good = group["good_wavelengths"][:].data == 1
    resampled = engine.get_resample(w, bp)

    def feature_metrics(ref, wavelength, feat, emit):
        endpoints = feat["continuum_endpoints"]
        valid = np.isfinite(ref) & (ref > 0)
        if emit:
            valid &= good
        ch = np.flatnonzero(valid)
        wl = wavelength[ch]
        spec = ref[ch][None, :]
        refsel = ref[ch]
        result = {
            "valid_bands": int(((wavelength >= endpoints[0]) & (wavelength <= endpoints[3]) & valid).sum()),
            "left_endpoint_bands": int(((wavelength >= endpoints[0]) & (wavelength <= endpoints[1]) & valid).sum()),
            "right_endpoint_bands": int(((wavelength >= endpoints[2]) & (wavelength <= endpoints[3]) & valid).sum()),
            "depth": np.nan, "r2": np.nan, "center": np.nan, "self_pass": False,
            "center_inside_feature": False, "center_status": "INVALID_RANGE",
            "center_curvature": np.nan, "center_inside_triplet": False,
        }
        try:
            r2, depth = _get_fit(spec, refsel, wl, endpoints)
            result["r2"], result["depth"] = float(r2[0]), float(depth[0])
            center = _get_quadratic_center(spec, wl, endpoints, np.array([True]))[0]
            result["center"] = float(center)
            result["center_inside_feature"] = bool(endpoints[0] <= center <= endpoints[3])
            diagnostics = center_diagnostics(spec, wl, endpoints)
            result["center_status"] = diagnostics["status"]
            result["center_curvature"] = diagnostics["curvature"]
            result["center_inside_triplet"] = diagnostics["inside_triplet"]
            *_, raw = _diagnostic_feature(
                spec, refsel, wl, endpoints, feat["feature_weight"],
                _continuum_constraints_list(feat["continuum_constraints"]),
                feat["fit_constraint"], feat["depth_constraints"],
            )
            result["self_pass"] = bool(np.isfinite(raw[0]))
        except EXC:
            pass
        return result

    feature_rows = []
    rule_rows = []
    rule_predictions = {}
    with (OUT / "reference_classification.log").open("w", encoding="utf-8") as log:
        with contextlib.redirect_stdout(log):
            for ri, (name, label, ref) in enumerate(zip(rules, labels, spectra)):
                name, label = str(name), str(label)
                native_valid = np.isfinite(ref) & (ref > 0)
                emit_ref = resampled[name]
                emit_valid = good & np.isfinite(emit_ref) & (emit_ref > 0)
                ch = np.flatnonzero(emit_valid)
                wl = w[ch]
                result = engine.classify_spectrum(
                    emit_ref[None, :], wl, w, bp, ch, top_n=len(rf))
                top1 = result[0]["name"] if result else ""
                rank = next((j + 1 for j, r in enumerate(result) if r["name"] == name), None)
                scene = engine._classifier.classify(
                    emit_ref[None, None, :], wl, w, bp, ch, n_workers=1)
                arb_winner = scene.index[int(scene.num[0])] if scene.fit[0] > 0 else ""
                rule_predictions[name] = {"top1": top1, "rank": rank,
                                          "arbitrated_winner": arb_winner}

    duplicate_hashes = defaultdict(list)
    for name, ref in zip(rules, spectra):
        h = hashlib.sha256(np.ascontiguousarray(ref).tobytes()).hexdigest()
        duplicate_hashes[h].append(str(name))
    duplicate_groups = [sorted(v) for v in duplicate_hashes.values() if len(v) > 1]
    duplicate_groups.sort(key=lambda x: list(rules).index(x[0]))
    duplicate_of = {}
    for gi, group in enumerate(duplicate_groups, 1):
        for name in group:
            duplicate_of[name] = f"D{gi:02d}"

    for ri, (name, label, ref) in enumerate(zip(rules, labels, spectra)):
        name, label = str(name), str(label)
        rule = rf[name]
        native_valid = np.isfinite(ref) & (ref > 0)
        emit_ref = resampled[name]
        emit_valid = good & np.isfinite(emit_ref) & (emit_ref > 0)
        intervals = []
        feature_indices = []
        for fi, feat in enumerate(rule["diagnostic_features"]):
            ep = feat["continuum_endpoints"]
            one = feature_metrics(ref, grid, feat, emit=False)
            em = feature_metrics(emit_ref, w, feat, emit=True)
            depth_ratio = em["depth"] / one["depth"] if one["depth"] and np.isfinite(one["depth"]) else np.nan
            shift_nm = 1000 * (em["center"] - one["center"])
            flags = []
            if not em["valid_bands"]:
                flags.append("NO_EMIT_FEATURE_BANDS")
            elif em["valid_bands"] < 3:
                flags.append("LT3_EMIT_FEATURE_BANDS")
            if not em["left_endpoint_bands"] or not em["right_endpoint_bands"]:
                flags.append("MISSING_EMIT_ENDPOINT")
            if not em["self_pass"]:
                flags.append("SELF_CONSTRAINT_REJECT")
            if np.isfinite(em["depth"]) and em["depth"] < 0.01:
                flags.append("WEAK_DEPTH_LT_0.01")
            if np.isfinite(depth_ratio) and depth_ratio < 0.5:
                flags.append("DEPTH_ATTENUATION_LT_0.5")
            if np.isfinite(shift_nm) and abs(shift_nm) > 4:
                flags.append("CENTER_SHIFT_GT_4NM")
            if em["center_status"] == "OUTSIDE_FEATURE":
                flags.append("CENTER_OUTSIDE_FEATURE")
            if em["center_status"] in ("EDGE_MINIMUM", "NONFINITE_VERTEX"):
                flags.append("CENTER_NONFINITE")
            if em["center_status"] == "OUTSIDE_TRIPLET":
                flags.append("CENTER_OUTSIDE_TRIPLET")
            if em["center_status"] == "NEGATIVE_CURVATURE":
                flags.append("CENTER_NEGATIVE_CURVATURE")
            if feat["feature_weight"] == 0:
                flags.append("INFO_WEIGHT_ZERO")
            feature_rows.append({
                "rule": name, "reference_label": label, "feature_index": fi,
                "feature_weight": feat["feature_weight"],
                "continuum_endpoints_um": ";".join(str(x) for x in ep),
                "feature_window_um": f"{ep[0]}:{ep[3]}",
                "fit_constraint": feat["fit_constraint"],
                "depth_min": feat["depth_constraints"][0],
                "depth_max": feat["depth_constraints"][1],
                "continuum_constraint_count": sum(x is not None for x in feat["continuum_constraints"].values()),
                "native_valid_points": int(native_valid.sum()),
                "native_start_um": float(grid[native_valid][0]),
                "native_end_um": float(grid[native_valid][-1]),
                "emit_valid_bands": em["valid_bands"],
                "emit_left_endpoint_bands": em["left_endpoint_bands"],
                "emit_right_endpoint_bands": em["right_endpoint_bands"],
                "depth_1nm": one["depth"], "depth_emit": em["depth"],
                "depth_emit_over_1nm": depth_ratio,
                "center_1nm_um": one["center"], "center_emit_um": em["center"],
                "center_shift_nm": shift_nm,
                "self_r2_emit": em["r2"], "self_pass_1nm": one["self_pass"],
                "self_pass_emit": em["self_pass"],
                "center_inside_feature_emit": em["center_inside_feature"],
                "center_status_1nm": one["center_status"], "center_status_emit": em["center_status"],
                "center_curvature_emit": em["center_curvature"],
                "center_inside_triplet_emit": em["center_inside_triplet"],
                "arbitration_relevant": bool(fi == 0 and feat.get("absorption_center_range")),
                "flags": ";".join(flags),
            })
            intervals.append((ep[0], ep[3], fi))
        overlap_pairs = []
        for a in range(len(intervals)):
            for b in range(a + 1, len(intervals)):
                overlap = min(intervals[a][1], intervals[b][1]) - max(intervals[a][0], intervals[b][0])
                if overlap > 0:
                    overlap_pairs.append((a, b, overlap * 1000))
        pred = rule_predictions[name]
        depths = [r["depth_emit"] for r in feature_rows if r["rule"] == name]
        flags = [r["flags"] for r in feature_rows if r["rule"] == name]
        rule_rows.append({
            "rule": name, "reference_label": label, "rule_index": ri,
            "n_diagnostic_features": len(rule["diagnostic_features"]),
            "n_weight_zero_features": sum(f["feature_weight"] == 0 for f in rule["diagnostic_features"]),
            "native_start_um": float(grid[native_valid][0]),
            "native_end_um": float(grid[native_valid][-1]),
            "native_valid_points": int(native_valid.sum()),
            "emit_valid_bands": int(emit_valid.sum()),
            "min_emit_feature_depth": float(np.nanmin(depths)),
            "n_weak_depth_features": sum("WEAK_DEPTH_LT_0.01" in f for f in flags),
            "n_self_reject_features_emit": sum("SELF_CONSTRAINT_REJECT" in f for f in flags),
            "overlap_pairs": ";".join(f"{a}-{b}" for a, b, _ in overlap_pairs),
            "max_overlap_nm": max((x[2] for x in overlap_pairs), default=0.0),
            "duplicate_group": duplicate_of.get(name, ""),
            "top1_without_arbitration": pred["top1"],
            "self_rank_without_arbitration": pred["rank"],
            "arbitrated_winner": pred["arbitrated_winner"],
            "arbitration_changed_reference": pred["arbitrated_winner"] != pred["top1"],
            "has_depth_ratio": "max_depth_ratio_feat1_over_feat0" in rule,
            "depth_ratio_threshold": rule.get("max_depth_ratio_feat1_over_feat0"),
            "has_arbitration_window": bool(rule["diagnostic_features"] and
                rule["diagnostic_features"][0].get("absorption_center_range")),
            "rule_flags": ";".join(sorted(set(x for f in flags for x in f.split(";") if x))),
        })

    with (OUT / "feature_audit.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(feature_rows[0]))
        writer.writeheader(); writer.writerows(feature_rows)
    with (OUT / "rule_audit.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rule_rows[0]))
        writer.writeheader(); writer.writerows(rule_rows)
    with (OUT / "duplicate_groups.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["group", "rules", "reference_labels"])
        for gi, group in enumerate(duplicate_groups, 1):
            writer.writerow([f"D{gi:02d}", ";".join(group),
                             ";".join(str(labels[list(rules).index(n)]) for n in group)])

    flag_counts = Counter(x for r in feature_rows for x in r["flags"].split(";") if x)
    summary = {
        "evidence_scope": "Reference-derived feature and self-consistency audit; not independent validation.",
        "current_config": {"pure_depth_ratio": 0.6, "kaolinite_muscovite_depth_ratio": 0.55,
                           "lowFe_window": [2.244, 2.248]},
        "n_rules": len(rule_rows), "n_features": len(feature_rows),
        "feature_flag_counts": dict(sorted(flag_counts.items())),
        "center_status_emit": dict(Counter(r["center_status_emit"] for r in feature_rows)),
        "arbitration_relevant_flagged_features": [
            {"rule": r["rule"], "feature_index": r["feature_index"], "flags": r["flags"]}
            for r in feature_rows if r["arbitration_relevant"] and r["flags"]
        ],
        "emit_depth_min": float(np.min([r["depth_emit"] for r in feature_rows])),
        "emit_depth_median": float(np.median([r["depth_emit"] for r in feature_rows])),
        "emit_depth_attenuation_min": float(np.min([r["depth_emit_over_1nm"] for r in feature_rows])),
        "emit_depth_attenuation_median": float(np.median([r["depth_emit_over_1nm"] for r in feature_rows])),
        "center_shift_abs_median_nm": float(np.nanmedian([abs(r["center_shift_nm"]) for r in feature_rows])),
        "center_shift_abs_max_nm": float(np.nanmax([abs(r["center_shift_nm"]) for r in feature_rows])),
        "rules_with_swir_only_native_coverage": sum(r["native_start_um"] > 1.0 for r in rule_rows),
        "top1_self_identification_without_arbitration": sum(r["top1_without_arbitration"] == r["rule"] for r in rule_rows),
        "top5_self_identification_without_arbitration": sum(
            r["self_rank_without_arbitration"] is not None and r["self_rank_without_arbitration"] <= 5 for r in rule_rows),
        "arbitration_changed_reference_count": sum(r["arbitration_changed_reference"] for r in rule_rows),
        "arbitration_improved_to_self": sum(
            r["arbitrated_winner"] == r["rule"] and r["top1_without_arbitration"] != r["rule"] for r in rule_rows),
        "arbitration_degraded_from_self": sum(
            r["top1_without_arbitration"] == r["rule"] and r["arbitrated_winner"] != r["rule"] for r in rule_rows),
        "duplicate_groups": duplicate_groups,
        "known_rule_semantics": {
            "weight_zero": "Feature can still participate in constraints or depth ratio; zero weight is not automatic evidence of uselessness.",
            "weak_depth": "Depth < 0.01 is a review flag, not automatic proof of a bad feature.",
            "duplicate_references": "Rule distinctions may come from constraints, not independent spectral evidence.",
        },
        "files": ["feature_audit.csv", "rule_audit.csv", "duplicate_groups.csv", "reference_classification.log"],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
