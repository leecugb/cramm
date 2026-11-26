#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Re-evaluate synthetic ablations under CRAMM's rule-attribution semantics."""
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs"))
from crosslib_benchmark import RULE_FAMILY  # noqa: E402
from cramm.classifier import _diagnostic_feature  # noqa: E402
from cramm.mica_engine import MicaEngine  # noqa: E402

DATA = Path(os.environ.get("CRAMM_SEMANTIC_DATA", ROOT / "output/synthetic_emit_lowfreq_v1"))
PRED = Path(os.environ.get("CRAMM_SEMANTIC_PRED", ROOT / "output/synthetic_emit_lowfreq_ablation_v1"))
OUT = Path(os.environ.get("CRAMM_SEMANTIC_OUT", ROOT / "output/semantic_reassessment_v2"))
PURE_MICA = {
    "muscovite_lowAl", "muscovite_medAl", "muscovite_medhighAl",
    "muscovite_Fe-rich", "illite_imt1", "illite_gds4",
}
PURE_CONFUSERS = {
    "calcite", "dolomite", "chlorite_lowFe", "clinochlore",
    "clinochlore_Fe", "thuringite", "epidote",
}
KAOLINITE_MIXTURES = {
    "kaolinite.5+muscoviteMedAl.5", "kaolinite.5+muscoviteMedhighAl.5",
    "kaolinite+muscovite_mix_intimate",
}
KAOLINITE_PURE = {"kaolinite_wxl", "kaolinite_pxl", "kaolinite_or_dickite"}


def fams(rule):
    return set() if not rule else set(RULE_FAMILY[rule])


def main():
    OUT.mkdir(exist_ok=True)
    if any(OUT.iterdir()):
        raise SystemExit(f"Output directory must be empty: {OUT}")
    with (DATA / "truth.csv").open(encoding="utf-8") as f:
        truth = list(csv.DictReader(f))
    pred = np.load(PRED / "predictions.npz", allow_pickle=False)
    configs = list(pred["config"])
    i00, i10 = configs.index("M00"), configs.index("M10")
    n = len(truth)
    targeted = np.array([r.get("targeted_mix") == "True" for r in truth])
    single = np.array([r["sample_kind"] == "single_reference" for r in truth])
    source1 = np.array([r["source_rule_1"] for r in truth])
    source2 = np.array([r["source_rule_2"] for r in truth])
    if any(r.get("targeted_group") for r in truth):
        low_ratio_clay = np.array([r.get("targeted_group") == "low_ratio_clay" for r in truth])
    else:
        low_ratio_clay = ((np.array([r["sample_kind"] == "binary_areal" for r in truth]))
                          & np.isin(source1, list(PURE_MICA)) & np.isin(source2, list(KAOLINITE_PURE)))
    clean = np.array([not r["snr_db_target"] for r in truth])
    truth_components = [set(filter(None, r["family_set_1"].split(";"))) |
                        set(filter(None, r["family_set_2"].split(";"))) for r in truth]
    confuser_family = [set(filter(None, r["family_set_2"].split(";"))) for r in truth]

    def outcome_counts(ci, selected):
        counts = Counter()
        for i in np.flatnonzero(selected):
            rule = str(pred["predicted_rule"][ci, i])
            pf = fams(rule)
            if not rule:
                outcome = "no_fire"
            elif pred["component_exact"][ci, i]:
                outcome = "correct_mixture_component_set"
            elif rule in PURE_MICA:
                outcome = "pure_white_mica_or_illite"
            elif len(pf) == 1 and pf == confuser_family[i]:
                outcome = "pure_actual_confuser_family"
            elif len(pf) > 1 and pf & truth_components[i]:
                outcome = "other_mixture_partial_overlap"
            elif len(pf) > 1:
                outcome = "other_mixture_no_overlap"
            else:
                outcome = "other_pure_rule"
            counts[outcome] += 1
        return dict(sorted(counts.items()))

    outcomes = {c: outcome_counts(ci, targeted) for c, ci in (("M00", i00), ("M10", i10))}
    low_ratio_outcomes = {c: outcome_counts(ci, low_ratio_clay)
                          for c, ci in (("M00", i00), ("M10", i10))}
    high_ratio_confuser = np.array([
        r.get("targeted_group") == "high_ratio_confuser" for r in truth
    ])
    high_ratio_outcomes = {c: outcome_counts(ci, high_ratio_confuser)
                           for c, ci in (("M00", i00), ("M10", i10))}
    for counts in outcomes.values():
        assert sum(counts.values()) == int(targeted.sum())
    for counts in low_ratio_outcomes.values():
        assert sum(counts.values()) == int(low_ratio_clay.sum())
    for counts in high_ratio_outcomes.values():
        assert sum(counts.values()) == int(high_ratio_confuser.sum())

    # Pure-reference retention and false pure-mica assignment.
    reference_metrics = {}
    for name, mask in (
        ("pure_white_mica_illite", single & np.isin(source1, list(PURE_MICA))),
        ("pure_confuser_references", single & np.isin(source1, list(PURE_CONFUSERS))),
        ("kaolinite_muscovite_references", single & np.isin(source1, list(KAOLINITE_MIXTURES))),
    ):
        reference_metrics[name] = {"n": int(mask.sum())}
        for config, ci in (("M00", i00), ("M10", i10)):
            winner = pred["predicted_rule"][ci]
            reference_metrics[name][config] = {
                "fire_rate": float(pred["fired"][ci, mask].mean()),
                "exact_rule_rate": float(pred["exact_rule"][ci, mask].mean()),
                "pure_mica_winner_count": int((mask & np.isin(winner, list(PURE_MICA))).sum()),
            }
        reference_metrics[name]["clean_n"] = int((mask & clean).sum())
        reference_metrics[name]["clean_M00_exact"] = int((mask & clean & pred["exact_rule"][i00]).sum())
        reference_metrics[name]["clean_M10_exact"] = int((mask & clean & pred["exact_rule"][i10]).sum())

    # Recompute the actual ratio for pure-mica winners before/after the gate.
    engine = MicaEngine()
    data = np.load(DATA / "spectra.npz")
    w, bp = data["band_centers_um"], data["fwhm_um"]
    ratio_rows = []

    def ratio_for(i, rule):
        chanels = np.flatnonzero(data["valid_mask"][i])
        wl = w[chanels]
        spectrum = data["reflectance"][i, chanels][None, :]
        compiled = engine._classifier._get_compiled_rules(w, bp, wl, chanels)[rule]
        raw = []
        for pre, weight, cc, fc, dc in compiled["diag"][:2]:
            *_, depth = _diagnostic_feature(
                spectrum, None, wl, None, weight, cc, fc, dc, pre=pre)
            raw.append(float(depth[0]))
        ratio = raw[1] / raw[0]
        return ratio, float(compiled["ratio_max"]), raw[0], raw[1]

    for i in np.flatnonzero(targeted):
        before = str(pred["predicted_rule"][i00, i])
        after = str(pred["predicted_rule"][i10, i])
        if before not in PURE_MICA and after not in PURE_MICA:
            continue
        before_values = ratio_for(i, before) if before in PURE_MICA else (np.nan, np.nan, np.nan, np.nan)
        after_values = ratio_for(i, after) if after in PURE_MICA else (np.nan, np.nan, np.nan, np.nan)
        ratio_rows.append({
            "sample_id": truth[i]["sample_id"], "before_rule": before, "after_rule": after,
            "before_ratio": before_values[0], "before_threshold": before_values[1],
            "before_high": before_values[0] >= before_values[1],
            "after_ratio": after_values[0], "after_threshold": after_values[1],
            "after_high": after_values[0] >= after_values[1],
            "before_pure_mica": before in PURE_MICA, "after_pure_mica": after in PURE_MICA,
            "before_raw0": before_values[2], "before_raw1": before_values[3],
            "after_raw0": after_values[2], "after_raw1": after_values[3],
        })

    before_pure = [r for r in ratio_rows if r["before_pure_mica"]]
    after_pure = [r for r in ratio_rows if r["after_pure_mica"]]
    ratio_checks = {
        "before_pure_mica_n": len(before_pure),
        "before_high_ratio_n": sum(r["before_high"] for r in before_pure),
        "before_high_ratio_removed_from_pure_n": sum(
            r["before_high"] and not r["after_pure_mica"] for r in before_pure),
        "before_high_ratio_retained_in_pure_n": sum(
            r["before_high"] and r["after_pure_mica"] for r in before_pure),
        "before_low_ratio_but_changed_n": sum(
            not r["before_high"] and r["before_rule"] != r["after_rule"]
            for r in before_pure),
        "after_pure_mica_n": len(after_pure),
        "after_pure_high_ratio_n": sum(r["after_high"] for r in after_pure),
        "after_pure_emerged_from_nonpure_n": sum(not r["before_pure_mica"] for r in after_pure),
    }

    with (OUT / "ratio_gate_semantics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(ratio_rows[0]))
        writer.writeheader(); writer.writerows(ratio_rows)

    clay_ratio_rows = []
    for i in np.flatnonzero(low_ratio_clay):
        before = str(pred["predicted_rule"][i00, i])
        after = str(pred["predicted_rule"][i10, i])
        if before not in KAOLINITE_MIXTURES and after not in KAOLINITE_MIXTURES:
            continue
        before_values = ratio_for(i, before) if before in KAOLINITE_MIXTURES else (np.nan, np.nan, np.nan, np.nan)
        after_values = ratio_for(i, after) if after in KAOLINITE_MIXTURES else (np.nan, np.nan, np.nan, np.nan)
        clay_ratio_rows.append({
            "sample_id": truth[i]["sample_id"], "before_rule": before, "after_rule": after,
            "before_ratio": before_values[0], "before_threshold": before_values[1],
            "before_high": before_values[0] >= before_values[1],
            "after_ratio": after_values[0], "after_threshold": after_values[1],
            "after_high": after_values[0] >= after_values[1],
            "before_kaolinite_muscovite": before in KAOLINITE_MIXTURES,
            "after_kaolinite_muscovite": after in KAOLINITE_MIXTURES,
        })
    clay_before = [r for r in clay_ratio_rows if r["before_kaolinite_muscovite"]]
    clay_after = [r for r in clay_ratio_rows if r["after_kaolinite_muscovite"]]
    clay_ratio_checks = {
        "before_kaolinite_muscovite_n": len(clay_before),
        "before_high_ratio_n": sum(r["before_high"] for r in clay_before),
        "before_high_ratio_removed_n": sum(
            r["before_high"] and not r["after_kaolinite_muscovite"] for r in clay_before),
        "before_high_ratio_retained_n": sum(
            r["before_high"] and r["after_kaolinite_muscovite"] for r in clay_before),
        "before_low_ratio_but_changed_n": sum(
            not r["before_high"] and r["before_rule"] != r["after_rule"] for r in clay_before),
        "after_kaolinite_muscovite_n": len(clay_after),
        "after_high_ratio_n": sum(r["after_high"] for r in clay_after),
    }
    with (OUT / "clay_ratio_gate_semantics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(clay_ratio_rows[0]))
        writer.writeheader(); writer.writerows(clay_ratio_rows)
    summary = {
        "evidence_scope": "CRAMM-reference-derived semantic reassessment; not independent validation.",
        "targeted_outcomes": outcomes,
        "low_ratio_clay_n": int(low_ratio_clay.sum()),
        "low_ratio_clay_outcomes": low_ratio_outcomes,
        "high_ratio_confuser_n": int(high_ratio_confuser.sum()),
        "high_ratio_confuser_outcomes": high_ratio_outcomes,
        "clay_ratio_gate_checks": clay_ratio_checks,
        "pure_reference_metrics": reference_metrics,
        "ratio_gate_checks": ratio_checks,
        "semantic_rules": {
            "pure_mica_illite": "ratio >= 0.6 rejects pure-rule attribution, not the existence of a mica component",
            "kaolinite_muscovite_mixture": "ratio >= the rule-specific threshold rejects that mixture-rule attribution",
            "arbitration": "post-best-match within-family or within-tier reassignment",
            "no_fire": "no admissible rule, neither automatic error nor automatic mixture recovery",
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
