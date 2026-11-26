#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Detailed audit of the low-ratio white-mica/illite–clay synthetic group."""
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "docs"))
from crosslib_benchmark import RULE_FAMILY  # noqa: E402

DATA = ROOT / "output/synthetic_emit_lowfreq_extended_v1"
PRED = ROOT / "output/synthetic_emit_lowfreq_extended_ablation_v1"
OUT = Path(os.environ.get("CRAMM_CLAY_AUDIT_OUT", ROOT / "output/low_ratio_clay_detailed_v1"))
KAOLINITE_MIXTURES = {
    "kaolinite.5+muscoviteMedAl.5", "kaolinite.5+muscoviteMedhighAl.5",
    "kaolinite+muscovite_mix_intimate",
}


def fams(rule):
    return set() if not rule else set(RULE_FAMILY[rule])


def mean(x):
    return float(np.mean(x)) if len(x) else None


def main():
    OUT.mkdir(exist_ok=True)
    if any(OUT.iterdir()):
        raise SystemExit(f"Output directory must be empty: {OUT}")
    with (DATA / "truth.csv").open(encoding="utf-8") as f:
        truth = list(csv.DictReader(f))
    pred = np.load(PRED / "predictions.npz", allow_pickle=False)
    configs = list(pred["config"])
    i00, i10 = configs.index("M00"), configs.index("M10")
    selected = np.array([r.get("targeted_group") == "low_ratio_clay" for r in truth])
    family = np.array([r["family_set_2"] for r in truth])
    fraction = np.array([float(r["fraction_1"]) for r in truth])
    source1 = np.array([r["source_rule_1"] for r in truth])
    dominant_eligible = np.array([bool(r["dominant_rule"]) for r in truth])
    components = [set(filter(None, r["family_set_1"].split(";"))) |
                  set(filter(None, r["family_set_2"].split(";"))) for r in truth]
    clay_family = [set(filter(None, r["family_set_2"].split(";"))) for r in truth]

    def metric_row(ci, mask):
        eligible = mask & dominant_eligible
        return {
            "n": int(mask.sum()),
            "fire": mean(pred["fired"][ci, mask]),
            "dominant_hit": mean(pred["dominant_hit"][ci, eligible]),
            "component_recall": mean(pred["component_recall"][ci, mask]),
            "component_set_exact": mean(pred["component_exact"][ci, mask]),
            "white_mica_detected": mean(pred["white_mica_detected"][ci, mask]),
            "clay_detected": mean(pred["confuser_detected"][ci, mask]),
        }

    def paired_row(mask):
        before = pred["predicted_rule"][i00]
        after = pred["predicted_rule"][i10]
        return {
            "changed": int((mask & (before != after)).sum()),
            "exact_improved": int((mask & ~pred["component_exact"][i00] & pred["component_exact"][i10]).sum()),
            "exact_degraded": int((mask & pred["component_exact"][i00] & ~pred["component_exact"][i10]).sum()),
            "dominant_improved": int((mask & dominant_eligible & ~pred["dominant_hit"][i00] & pred["dominant_hit"][i10]).sum()),
            "dominant_degraded": int((mask & dominant_eligible & pred["dominant_hit"][i00] & ~pred["dominant_hit"][i10]).sum()),
            "white_detect_improved": int((mask & ~pred["white_mica_detected"][i00] & pred["white_mica_detected"][i10]).sum()),
            "white_detect_degraded": int((mask & pred["white_mica_detected"][i00] & ~pred["white_mica_detected"][i10]).sum()),
            "clay_detect_improved": int((mask & ~pred["confuser_detected"][i00] & pred["confuser_detected"][i10]).sum()),
            "clay_detect_degraded": int((mask & pred["confuser_detected"][i00] & ~pred["confuser_detected"][i10]).sum()),
            "fire_lost": int((mask & pred["fired"][i00] & ~pred["fired"][i10]).sum()),
        }

    def write_groups(filename, values):
        rows = []
        for value in sorted(set(values[selected])):
            mask = selected & (values == value)
            row = {"group": value}
            for config, ci in (("M00", i00), ("M10", i10)):
                for key, val in metric_row(ci, mask).items():
                    row[f"{config}_{key}"] = val
            row.update(paired_row(mask))
            rows.append(row)
        with (OUT / filename).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
        return rows

    by_family = write_groups("by_clay_family.csv", family)
    by_fraction = write_groups("by_white_mica_fraction.csv", fraction)
    by_white_rule = write_groups("by_white_mica_rule.csv", source1)

    transition_counts = Counter()
    for i in np.flatnonzero(selected & (pred["predicted_rule"][i00] != pred["predicted_rule"][i10])):
        transition_counts[f"{pred['predicted_rule'][i00, i]}→{pred['predicted_rule'][i10, i]}"] += 1
    with (OUT / "prediction_transitions.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["transition", "n"])
        writer.writerows(sorted(transition_counts.items(), key=lambda x: (-x[1], x[0])))

    # Join the already recomputed 0.4-ratio gate records to clay family truth.
    with (ROOT / "output/semantic_reassessment_extended_v1/clay_ratio_gate_semantics.csv").open() as f:
        ratio_rows = list(csv.DictReader(f))
    by_id = {r["sample_id"]: r for r in truth}
    ratio_summary = {}
    for fam in ("kaolinite", "smectite"):
        rows = [r for r in ratio_rows if fam in by_id[r["sample_id"]]["family_set_2"].split(";")]
        ratio_summary[fam] = {
            "winner_rows": len(rows),
            "before_high": sum(r["before_high"] == "True" for r in rows),
            "before_high_removed": sum(r["before_high"] == "True" and r["after_kaolinite_muscovite"] == "False" for r in rows),
            "before_low_changed": sum(r["before_high"] != "True" and r["before_rule"] != r["after_rule"] for r in rows),
            "after_high": sum(r["after_high"] == "True" for r in rows),
        }

    summary = {
        "evidence_scope": "Reference-derived low-ratio clay audit; not independent validation.",
        "n": int(selected.sum()),
        "by_clay_family": by_family,
        "by_white_mica_fraction": by_fraction,
        "by_white_mica_rule": by_white_rule,
        "prediction_transitions": dict(transition_counts),
        "kaolinite_mixture_ratio_gate_by_truth_family": ratio_summary,
        "coverage": {
            "kaolinite_pairs": len({
                (r["source_rule_1"], r["source_rule_2"])
                for r, use in zip(truth, selected)
                if use and r["family_set_2"] == "kaolinite"
            }),
            "smectite_pairs": len({
                (r["source_rule_1"], r["source_rule_2"])
                for r, use in zip(truth, selected)
                if use and r["family_set_2"] == "smectite"
            }),
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
