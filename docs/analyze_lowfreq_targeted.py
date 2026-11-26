#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stratify targeted white-mica/confuser ablations by fraction and confuser."""
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "output/synthetic_emit_lowfreq_v1"
PRED = ROOT / "output/synthetic_emit_lowfreq_ablation_v1"
OUT = ROOT / "output/synthetic_emit_lowfreq_targeted_audit_v1"


def mean(x):
    return float(np.mean(x)) if len(x) else None


def metrics(pred, ci, mask, dominant_eligible):
    result = {"n": int(mask.sum())}
    for key in ("fired", "dominant_hit", "component_recall", "component_exact",
                "white_mica_detected", "confuser_detected"):
        values = pred[key][ci, mask]
        if key == "dominant_hit":
            values = values[dominant_eligible[mask]]
        result[key] = mean(values)
    return result


def main():
    OUT.mkdir(exist_ok=True)
    if any(OUT.iterdir()):
        raise SystemExit(f"Output directory must be empty: {OUT}")
    with (DATA / "truth.csv").open(encoding="utf-8") as f:
        truth = list(csv.DictReader(f))
    pred = np.load(PRED / "predictions.npz", allow_pickle=False)
    configs = list(pred["config"])
    i00, i10 = configs.index("M00"), configs.index("M10")
    targeted = np.array([r.get("targeted_mix") == "True" for r in truth])
    fractions = np.array([float(r["fraction_1"]) for r in truth])
    families = np.array([r["family_set_2"] for r in truth])
    rules = np.array([r["source_rule_2"] for r in truth])
    dominant_eligible = np.array([bool(r["dominant_rule"]) for r in truth])

    all_rows = []

    def write_groups(filename, values):
        rows = []
        for value in sorted(set(values[targeted])):
            mask = targeted & (values == value)
            row = {"group": value}
            for config, ci in (("M00", i00), ("M10", i10)):
                m = metrics(pred, ci, mask, dominant_eligible)
                for key in ("fired", "dominant_hit", "component_recall",
                            "component_exact", "white_mica_detected", "confuser_detected"):
                    row[f"{config}_{key}"] = m[key]
            changed = mask & (pred["predicted_rule"][i00] != pred["predicted_rule"][i10])
            row["changed"] = int(changed.sum())
            row["dominant_improved"] = int((mask & ~pred["dominant_hit"][i00] & pred["dominant_hit"][i10]).sum())
            row["dominant_degraded"] = int((mask & pred["dominant_hit"][i00] & ~pred["dominant_hit"][i10]).sum())
            row["white_detect_improved"] = int((mask & ~pred["white_mica_detected"][i00] & pred["white_mica_detected"][i10]).sum())
            row["white_detect_degraded"] = int((mask & pred["white_mica_detected"][i00] & ~pred["white_mica_detected"][i10]).sum())
            row["confuser_detect_improved"] = int((mask & ~pred["confuser_detected"][i00] & pred["confuser_detected"][i10]).sum())
            row["confuser_detect_degraded"] = int((mask & pred["confuser_detected"][i00] & ~pred["confuser_detected"][i10]).sum())
            row["component_exact_improved"] = int((mask & ~pred["component_exact"][i00] & pred["component_exact"][i10]).sum())
            row["component_exact_degraded"] = int((mask & pred["component_exact"][i00] & ~pred["component_exact"][i10]).sum())
            row["fire_lost"] = int((mask & pred["fired"][i00] & ~pred["fired"][i10]).sum())
            rows.append(row)
        with (OUT / filename).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
        all_rows.extend({"level": filename, **r} for r in rows)
        return rows

    by_fraction = write_groups("targeted_by_fraction.csv", fractions)
    by_family = write_groups("targeted_by_confuser_family.csv", families)
    by_rule = write_groups("targeted_by_confuser_rule.csv", rules)
    summary = {
        "evidence_scope": "Reference-derived low-frequency targeted-mixture audit; not independent validation.",
        "n_targeted": int(targeted.sum()),
        "by_fraction": by_fraction,
        "by_confuser_family": by_family,
        "by_confuser_rule": by_rule,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"by_fraction": by_fraction, "by_confuser_family": by_family}, ensure_ascii=False, indent=2))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
