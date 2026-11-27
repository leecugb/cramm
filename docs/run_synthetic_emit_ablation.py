#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run paired CRAMM ablations on reference-derived spectra on actual EMIT bands.

Configurations:
  M00 = depth ratio off, wavelength arbitration off
  M10 = depth ratio on,  wavelength arbitration off
  M01 = depth ratio off, wavelength arbitration on
  M11 = depth ratio on,  wavelength arbitration on

The data use CRAMM's own reference spectra. Results are self-consistency and
algorithm-development evidence, not independent or unbiased accuracy estimates.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "repo" / "src"))
sys.path.insert(0, str(REPO / "docs"))
from crosslib_benchmark import RULE_FAMILY  # noqa: E402
from cramm.mica_engine import MicaEngine  # noqa: E402

CONFIGS = {
    "M00": (False, False),
    "M10": (True, False),
    "M01": (False, True),
    "M11": (True, True),
}
SUBTYPE_RULES = {
    "muscovite_lowAl", "muscovite_medAl", "muscovite_medhighAl", "muscovite_Fe-rich",
    "chlorite_lowFe", "clinochlore", "clinochlore_Fe", "thuringite",
    "calcite_abundant", "calcite", "dolomite_abundant", "dolomite",
}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def family_set(rule: str) -> set:
    return set() if not rule else set(RULE_FAMILY[rule])


def mean(values):
    values = list(values)
    return float(np.mean(values)) if values else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path,
                        default=REPO / "output/synthetic_emit_v1")
    parser.add_argument("--output", type=Path,
                        default=REPO / "output/synthetic_emit_ablation_v1")
    parser.add_argument("--n-workers", type=int, default=1)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise SystemExit(f"Output directory must be empty: {out}")

    data = args.data.resolve()
    z = np.load(data / "spectra.npz", allow_pickle=False)
    with (data / "truth.csv").open(encoding="utf-8") as f:
        truth = list(csv.DictReader(f))
    spectra = z["reflectance"]
    masks = z["valid_mask"]
    w = z["band_centers_um"]
    bp = z["fwhm_um"]
    n = len(truth)
    if spectra.shape != (n, len(w)) or masks.shape != spectra.shape:
        raise ValueError("Input spectra/truth shape mismatch")

    groups = defaultdict(list)
    for i, mask in enumerate(masks):
        groups[mask.tobytes()].append(i)
    config_names = list(CONFIGS)
    predicted_rule = np.full((len(CONFIGS), n), "", dtype="U42")
    predicted_num = np.zeros((len(CONFIGS), n), dtype=np.uint8)
    fit = np.zeros((len(CONFIGS), n), dtype=np.float64)
    fd = np.zeros((len(CONFIGS), n), dtype=np.float64)
    mus_center = np.zeros((len(CONFIGS), n), dtype=np.float64)
    chl_center = np.zeros((len(CONFIGS), n), dtype=np.float64)
    cal_center = np.zeros((len(CONFIGS), n), dtype=np.float64)
    fired = np.zeros((len(CONFIGS), n), dtype=bool)
    runtimes = {}
    field_counts = {}

    for ci, (config, (depth_enabled, arbitration_enabled)) in enumerate(CONFIGS.items()):
        engine = MicaEngine()
        depth_fields = 0
        arbitration_windows = 0
        for rule in engine.rf.values():
            if "max_depth_ratio_feat1_over_feat0" in rule:
                depth_fields += 1
                if not depth_enabled:
                    rule.pop("max_depth_ratio_feat1_over_feat0")
            for feature in rule.get("diagnostic_features", []):
                if "absorption_center_range" in feature:
                    arbitration_windows += 1
                    if not arbitration_enabled:
                        feature.pop("absorption_center_range")
        engine.invalidate_caches()
        field_counts[config] = {
            "depth_ratio_enabled": depth_enabled,
            "arbitration_enabled": arbitration_enabled,
            "depth_ratio_fields_retained": depth_fields if depth_enabled else 0,
            "arbitration_windows_retained": arbitration_windows if arbitration_enabled else 0,
        }
        t0 = time.perf_counter()
        for mask_bytes, indices_list in groups.items():
            indices = np.asarray(indices_list, dtype=int)
            chanels = np.flatnonzero(masks[indices[0]])
            wl = w[chanels]
            cube = np.ascontiguousarray(spectra[indices][:, None, :])
            result = engine._classifier.classify(
                cube, wl, w, bp, chanels, n_workers=args.n_workers
            )
            num = np.asarray(result.num, dtype=np.uint8)
            result_fit = np.asarray(result.fit, dtype=np.float64)
            result_fired = result_fit > 0
            names = np.asarray(result.index, dtype="U42")
            predicted_num[ci, indices] = num
            predicted_rule[ci, indices] = np.where(result_fired, names[num], "")
            fit[ci, indices] = result_fit
            fd[ci, indices] = result.depth
            mus_center[ci, indices] = result.mus_center
            chl_center[ci, indices] = result.chl_center
            cal_center[ci, indices] = result.cal_center
            fired[ci, indices] = result_fired
        runtimes[config] = time.perf_counter() - t0
        print(f"{config}: {runtimes[config]:.2f}s, fired {fired[ci].sum()}/{n}", flush=True)

    truth_components = []
    pure_mineral = np.zeros(n, dtype=bool)
    supported_subtype = np.zeros(n, dtype=bool)
    single = np.zeros(n, dtype=bool)
    binary = np.zeros(n, dtype=bool)
    dominant_family_hit_eligible = np.zeros(n, dtype=bool)
    targeted = np.zeros(n, dtype=bool)
    high_ratio_targeted = np.zeros(n, dtype=bool)
    low_ratio_targeted = np.zeros(n, dtype=bool)
    for i, rec in enumerate(truth):
        f1 = set(filter(None, rec["family_set_1"].split(";")))
        f2 = set(filter(None, rec["family_set_2"].split(";")))
        components = f1 | f2
        truth_components.append(components)
        single[i] = rec["sample_kind"] == "single_reference"
        binary[i] = rec["sample_kind"] == "binary_areal"
        label = rec["source_label_1"].lower()
        physical = not label.startswith("synth") and not label.endswith(("[amx]", "[alias]"))
        pure_mineral[i] = single[i] and len(f1) == 1 and f1 != {"other"} and physical
        supported_subtype[i] = single[i] and rec["source_rule_1"] in SUBTYPE_RULES
        dominant_family_hit_eligible[i] = binary[i] and bool(rec["dominant_rule"])
        targeted[i] = rec.get("targeted_mix", "") == "True"
        high_ratio_targeted[i] = rec.get("targeted_group", "") == "high_ratio_confuser"
        low_ratio_targeted[i] = rec.get("targeted_group", "") == "low_ratio_clay"

    exact_rule = np.zeros((len(CONFIGS), n), dtype=bool)
    family_hit = np.zeros((len(CONFIGS), n), dtype=bool)
    family_overlap = np.zeros((len(CONFIGS), n), dtype=bool)
    dominant_hit = np.zeros((len(CONFIGS), n), dtype=bool)
    component_recall = np.zeros((len(CONFIGS), n), dtype=np.float64)
    component_jaccard = np.zeros((len(CONFIGS), n), dtype=np.float64)
    component_exact = np.zeros((len(CONFIGS), n), dtype=bool)
    white_mica_detected = np.zeros((len(CONFIGS), n), dtype=bool)
    confuser_detected = np.zeros((len(CONFIGS), n), dtype=bool)
    for ci, config in enumerate(CONFIGS):
        for i, rec in enumerate(truth):
            pred = family_set(str(predicted_rule[ci, i]))
            source_rule = rec["source_rule_1"]
            source_family = set(filter(None, rec["family_set_1"].split(";")))
            exact_rule[ci, i] = single[i] and fired[ci, i] and predicted_rule[ci, i] == source_rule
            family_hit[ci, i] = fired[ci, i] and len(source_family) == 1 and source_family <= pred
            family_overlap[ci, i] = fired[ci, i] and bool(truth_components[i] & pred)
            if dominant_family_hit_eligible[i]:
                dominant_hit[ci, i] = fired[ci, i] and family_set(rec["dominant_rule"]) <= pred
            if fired[ci, i] and truth_components[i]:
                component_recall[ci, i] = len(truth_components[i] & pred) / len(truth_components[i])
                component_jaccard[ci, i] = len(truth_components[i] & pred) / len(truth_components[i] | pred)
                component_exact[ci, i] = pred == truth_components[i]
            if targeted[i]:
                white_mica_detected[ci, i] = fired[ci, i] and bool(source_family & pred)
                confuser_detected[ci, i] = fired[ci, i] and bool(
                    set(filter(None, rec["family_set_2"].split(";"))) & pred
                )

    masks_by_name = {
        "all": np.ones(n, dtype=bool),
        "single_reference": single,
        "physical_pure_mineral": pure_mineral,
        "supported_subtypes": supported_subtype,
        "binary_areal": binary,
        "targeted_white_mica_confuser": targeted,
        "targeted_high_ratio_confuser": high_ratio_targeted,
        "targeted_low_ratio_clay": low_ratio_targeted,
    }
    snr_values = np.asarray([rec["snr_db_target"] or "clean" for rec in truth])
    for level in ("clean", "40.0", "25.0", "15.0"):
        level_mask = snr_values == level
        masks_by_name[f"snr_{level}"] = level_mask
        for subset in ("physical_pure_mineral", "supported_subtypes", "binary_areal",
                       "targeted_white_mica_confuser", "targeted_high_ratio_confuser",
                       "targeted_low_ratio_clay"):
            masks_by_name[f"{subset}_snr_{level}"] = masks_by_name[subset] & level_mask

    def metrics(ci: int, mask: np.ndarray) -> dict:
        count = int(mask.sum())
        if not count:
            return {"n": 0}
        eligible = mask & dominant_family_hit_eligible
        binary_mask = mask & binary
        return {
            "n": count,
            "fire_rate": mean(fired[ci, mask]),
            "exact_rule_rate": mean(exact_rule[ci, mask & single]),
            "exact_rule_n": int((mask & single).sum()),
            "single_family_hit_rate": mean(family_hit[ci, mask & pure_mineral]),
            "family_overlap_rate": mean(family_overlap[ci, mask]),
            "dominant_family_hit_rate": mean(dominant_hit[ci, eligible]),
            "dominant_n": int(eligible.sum()),
            "binary_component_recall": mean(component_recall[ci, binary_mask]),
            "binary_component_jaccard": mean(component_jaccard[ci, binary_mask]),
            "binary_component_set_exact_rate": mean(component_exact[ci, binary_mask]),
            "white_mica_detected_rate": mean(white_mica_detected[ci, mask & targeted]),
            "confuser_detected_rate": mean(confuser_detected[ci, mask & targeted]),
        }

    summary = {
        "date": str(date.today()),
        "evidence_scope": (
            "CRAMM-reference-derived self-consistency and paired development test; "
            "not independent accuracy evidence."
        ),
        "input": {
            "spectra_npz": str(data / "spectra.npz"),
            "spectra_sha256": file_sha256(data / "spectra.npz"),
            "truth_sha256": file_sha256(data / "truth.csv"),
            "n_spectra": n,
            "unique_valid_masks": len(groups),
            "perturbation_model": (str(z["perturbation_model"][0])
                                   if "perturbation_model" in z.files else "white"),
            "targeted_mixtures": int(targeted.sum()),
            "high_ratio_targeted_mixtures": int(high_ratio_targeted.sum()),
            "low_ratio_targeted_mixtures": int(low_ratio_targeted.sum()),
            "sensor": "actual EMIT L2A wavelengths/FWHM/good_wavelengths",
        },
        "configurations": field_counts,
        "runtime_seconds": runtimes,
        "metrics": {
            config: {name: metrics(ci, mask) for name, mask in masks_by_name.items()}
            for ci, config in enumerate(CONFIGS)
        },
        "paired_comparisons": {},
    }

    for target, baseline in (("M10", "M00"), ("M01", "M00"), ("M11", "M00")):
        ti, bi = config_names.index(target), config_names.index(baseline)
        comparison = {}
        for name, mask in masks_by_name.items():
            if not mask.any():
                continue
            single_mask = mask & single
            pure_mask = mask & pure_mineral
            dominant_mask = mask & dominant_family_hit_eligible
            target_metrics = summary["metrics"][target][name]
            baseline_metrics = summary["metrics"][baseline][name]
            comparison[name] = {
                "n": int(mask.sum()),
                "changed_rule": int((predicted_rule[ti, mask] != predicted_rule[bi, mask]).sum()),
                "exact_rule_improved": int((~exact_rule[bi, single_mask] & exact_rule[ti, single_mask]).sum()),
                "exact_rule_degraded": int((exact_rule[bi, single_mask] & ~exact_rule[ti, single_mask]).sum()),
                "family_hit_improved": int((~family_hit[bi, pure_mask] & family_hit[ti, pure_mask]).sum()),
                "family_hit_degraded": int((family_hit[bi, pure_mask] & ~family_hit[ti, pure_mask]).sum()),
                "dominant_hit_improved": int((~dominant_hit[bi, dominant_mask] & dominant_hit[ti, dominant_mask]).sum()),
                "dominant_hit_degraded": int((dominant_hit[bi, dominant_mask] & ~dominant_hit[ti, dominant_mask]).sum()),
                "fire_gained": int((~fired[bi, mask] & fired[ti, mask]).sum()),
                "fire_lost": int((fired[bi, mask] & ~fired[ti, mask]).sum()),
                "delta_exact_rule_rate": (
                    target_metrics["exact_rule_rate"] - baseline_metrics["exact_rule_rate"]
                    if target_metrics["exact_rule_rate"] is not None else None
                ),
                "delta_family_hit_rate": (
                    target_metrics["single_family_hit_rate"]
                    - baseline_metrics["single_family_hit_rate"]
                    if target_metrics["single_family_hit_rate"] is not None else None
                ),
                "delta_dominant_hit_rate": (
                    target_metrics["dominant_family_hit_rate"]
                    - baseline_metrics["dominant_family_hit_rate"]
                    if target_metrics["dominant_family_hit_rate"] is not None else None
                ),
                "delta_component_recall": (
                    target_metrics["binary_component_recall"]
                    - baseline_metrics["binary_component_recall"]
                    if target_metrics["binary_component_recall"] is not None else None
                ),
                "delta_white_mica_detected_rate": (
                    target_metrics["white_mica_detected_rate"]
                    - baseline_metrics["white_mica_detected_rate"]
                    if target_metrics["white_mica_detected_rate"] is not None else None
                ),
                "delta_confuser_detected_rate": (
                    target_metrics["confuser_detected_rate"]
                    - baseline_metrics["confuser_detected_rate"]
                    if target_metrics["confuser_detected_rate"] is not None else None
                ),
                "delta_fire_rate": (
                    target_metrics["fire_rate"] - baseline_metrics["fire_rate"]
                ),
            }
        summary["paired_comparisons"][f"{target}_minus_{baseline}"] = comparison

    np.savez_compressed(
        out / "predictions.npz",
        config=np.asarray(config_names, dtype="U4"),
        sample_id=z["sample_id"],
        predicted_rule=predicted_rule,
        predicted_num=predicted_num,
        fit=fit,
        fd=fd,
        fired=fired,
        mus_center=mus_center,
        chl_center=chl_center,
        cal_center=cal_center,
        exact_rule=exact_rule,
        family_hit=family_hit,
        family_overlap=family_overlap,
        dominant_hit=dominant_hit,
        component_recall=component_recall,
        component_jaccard=component_jaccard,
        component_exact=component_exact,
        white_mica_detected=white_mica_detected,
        confuser_detected=confuser_detected,
    )
    with (out / "predictions.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["config", "sample_id", "sample_kind", "source_rule_1", "source_rule_2",
                  "snr_db_target", "continuum_slope_per_um", "predicted_rule", "fired",
                  "fit", "fd", "exact_rule", "family_hit", "family_overlap",
                  "dominant_hit", "component_recall", "component_jaccard", "component_exact",
                  "white_mica_detected", "confuser_detected",
                  "mus_center", "chl_center", "cal_center"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for ci, config in enumerate(CONFIGS):
            for i, rec in enumerate(truth):
                writer.writerow({
                    "config": config, "sample_id": rec["sample_id"],
                    "sample_kind": rec["sample_kind"],
                    "source_rule_1": rec["source_rule_1"], "source_rule_2": rec["source_rule_2"],
                    "snr_db_target": rec["snr_db_target"] or "clean",
                    "continuum_slope_per_um": rec["continuum_slope_per_um"],
                    "predicted_rule": predicted_rule[ci, i], "fired": int(fired[ci, i]),
                    "fit": fit[ci, i], "fd": fd[ci, i],
                    "exact_rule": int(exact_rule[ci, i]), "family_hit": int(family_hit[ci, i]),
                    "family_overlap": int(family_overlap[ci, i]),
                    "dominant_hit": int(dominant_hit[ci, i]),
                    "component_recall": component_recall[ci, i],
                    "component_jaccard": component_jaccard[ci, i],
                    "component_exact": int(component_exact[ci, i]),
                    "white_mica_detected": int(white_mica_detected[ci, i]),
                    "confuser_detected": int(confuser_detected[ci, i]),
                    "mus_center": mus_center[ci, i], "chl_center": chl_center[ci, i],
                    "cal_center": cal_center[ci, i],
                })

    summary["files"] = {
        name: {"sha256": file_sha256(out / name), "bytes": (out / name).stat().st_size}
        for name in ("predictions.npz", "predictions.csv")
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# CRAMM reference-derived EMIT ablation", "",
        "**Self-consistency/development evidence only; not independent accuracy.**", "",
        f"Actual EMIT bands; {n} spectra; {len(groups)} valid-mask groups; n_workers={args.n_workers}.", "",
        "## Core metrics", "",
        "| Config | Subset | n | Fire | Exact rule | Pure-family hit | Dominant-family hit | Mixture component recall |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for config in CONFIGS:
        for name in ("physical_pure_mineral", "supported_subtypes", "binary_areal"):
            m = summary["metrics"][config][name]
            def fmt(key):
                value = m.get(key)
                return "—" if value is None else f"{value:.4f}"
            lines.append(
                f"| {config} | {name} | {m['n']} | {fmt('fire_rate')} | "
                f"{fmt('exact_rule_rate')} | {fmt('single_family_hit_rate')} | "
                f"{fmt('dominant_family_hit_rate')} | {fmt('binary_component_recall')} |"
            )
    lines.extend(["", "## Physical pure minerals by SNR", "",
                  "| Config | SNR | n | Fire | Exact rule | Family hit |",
                  "|---|---|---:|---:|---:|---:|"])
    for config in CONFIGS:
        for level in ("clean", "40.0", "25.0", "15.0"):
            m = summary["metrics"][config][f"physical_pure_mineral_snr_{level}"]
            lines.append(
                f"| {config} | {level} | {m['n']} | {m['fire_rate']:.4f} | "
                f"{m['exact_rule_rate']:.4f} | {m['single_family_hit_rate']:.4f} |"
            )
    lines.extend(["", "## Supported subtypes by SNR", "",
                  "| Config | SNR | n | Fire | Exact subtype |",
                  "|---|---|---:|---:|---:|"])
    for config in CONFIGS:
        for level in ("clean", "40.0", "25.0", "15.0"):
            m = summary["metrics"][config][f"supported_subtypes_snr_{level}"]
            lines.append(
                f"| {config} | {level} | {m['n']} | {m['fire_rate']:.4f} | "
                f"{m['exact_rule_rate']:.4f} |"
            )
    lines.extend(["", "## Binary mixtures by SNR", "",
                  "| Config | SNR | n | Fire | Dominant-family hit | Component recall |",
                  "|---|---|---:|---:|---:|---:|"])
    for config in CONFIGS:
        for level in ("clean", "40.0", "25.0", "15.0"):
            m = summary["metrics"][config][f"binary_areal_snr_{level}"]
            lines.append(
                f"| {config} | {level} | {m['n']} | {m['fire_rate']:.4f} | "
                f"{m['dominant_family_hit_rate']:.4f} | {m['binary_component_recall']:.4f} |"
            )
    if targeted.any():
        lines.extend(["", "## Targeted white-mica/confuser mixtures", "",
                      "| Config | n | Fire | Dominant hit | Component recall | White-mica detected | Confuser detected |",
                      "|---|---:|---:|---:|---:|---:|---:|"])
        for config in CONFIGS:
            m = summary["metrics"][config]["targeted_white_mica_confuser"]
            lines.append(
                f"| {config} | {m['n']} | {m['fire_rate']:.4f} | "
                f"{m['dominant_family_hit_rate']:.4f} | {m['binary_component_recall']:.4f} | "
                f"{m['white_mica_detected_rate']:.4f} | {m['confuser_detected_rate']:.4f} |"
            )
        lines.extend(["", "Targeted mixtures by SNR", "",
                      "| Config | SNR | n | Fire | Dominant hit | White-mica detected |",
                      "|---|---|---:|---:|---:|---:|"])
        for config in CONFIGS:
            for level in ("clean", "40.0", "25.0", "15.0"):
                m = summary["metrics"][config][f"targeted_white_mica_confuser_snr_{level}"]
                lines.append(
                    f"| {config} | {level} | {m['n']} | {m['fire_rate']:.4f} | "
                    f"{m['dominant_family_hit_rate']:.4f} | {m['white_mica_detected_rate']:.4f} |"
                )
    for selected_mask, title in (
        (high_ratio_targeted, "High-ratio confuser mixtures"),
        (low_ratio_targeted, "Low-ratio clay mixtures"),
    ):
        if selected_mask.any():
            name = ("targeted_high_ratio_confuser" if title.startswith("High")
                    else "targeted_low_ratio_clay")
            lines.extend(["", f"## {title}", "",
                          "| Config | n | Fire | Dominant hit | Component recall | Component set exact | White-mica detected | Clay/confuser detected |",
                          "|---|---:|---:|---:|---:|---:|---:|---:|"])
            for config in CONFIGS:
                m = summary["metrics"][config][name]
                lines.append(
                    f"| {config} | {m['n']} | {m['fire_rate']:.4f} | "
                    f"{m['dominant_family_hit_rate']:.4f} | {m['binary_component_recall']:.4f} | "
                    f"{m['binary_component_set_exact_rate']:.4f} | "
                    f"{m['white_mica_detected_rate']:.4f} | {m['confuser_detected_rate']:.4f} |"
                )
    lines.extend(["", "## Paired changes", "",
                  "| Comparison | Subset | Changed | Exact +/- | Pure family +/- | Dominant +/- | Fire +/- |",
                  "|---|---|---:|---:|---:|---:|---:|"])
    for comparison, groups_out in summary["paired_comparisons"].items():
        paired_subsets = ["physical_pure_mineral", "supported_subtypes", "binary_areal"]
        if targeted.any():
            paired_subsets.append("targeted_white_mica_confuser")
        if high_ratio_targeted.any():
            paired_subsets.append("targeted_high_ratio_confuser")
        if low_ratio_targeted.any():
            paired_subsets.append("targeted_low_ratio_clay")
        for name in paired_subsets:
            m = groups_out[name]
            lines.append(
                f"| {comparison} | {name} | {m['changed_rule']} | "
                f"+{m['exact_rule_improved']} / -{m['exact_rule_degraded']} | "
                f"+{m['family_hit_improved']} / -{m['family_hit_degraded']} | "
                f"+{m['dominant_hit_improved']} / -{m['dominant_hit_degraded']} | "
                f"+{m['fire_gained']} / -{m['fire_lost']} |"
            )
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("WROTE", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
