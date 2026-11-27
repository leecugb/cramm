#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Grid-search CRAMM depth-ratio thresholds using cached candidate matrices."""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "repo" / "src"))
sys.path.insert(0, str(ROOT / "docs"))
from crosslib_benchmark import RULE_FAMILY  # noqa: E402
from cramm.classifier import (  # noqa: E402
    InvalidLeftEndPointError, InvalidRangeError, InvalidRightEndPointError,
    _diagnostic_feature, _judge_reference_entry,
)
from cramm.mica_engine import MicaEngine  # noqa: E402

DATA = ROOT / "output/synthetic_emit_lowfreq_extended_v1"
PRED = ROOT / "output/synthetic_emit_lowfreq_extended_ablation_v1"
OUT = Path(os.environ.get("CRAMM_THRESHOLD_OUT", ROOT / "output/depth_ratio_threshold_optimization_v1"))
PURE = ["muscovite_lowAl", "muscovite_medAl", "muscovite_medhighAl",
        "muscovite_Fe-rich", "illite_imt1", "illite_gds4"]
CLAY_MIX = ["kaolinite.5+muscoviteMedAl.5", "kaolinite.5+muscoviteMedhighAl.5",
            "kaolinite+muscovite_mix_intimate"]
RATIO_RULES = PURE + CLAY_MIX


def fams(rule):
    return set() if not rule else set(RULE_FAMILY[rule])


def main():
    OUT.mkdir(exist_ok=True)
    if any(OUT.iterdir()):
        raise SystemExit(f"Output directory must be empty: {OUT}")
    data = np.load(DATA / "spectra.npz", allow_pickle=False)
    pred = np.load(PRED / "predictions.npz", allow_pickle=False)
    with (DATA / "truth.csv").open(encoding="utf-8") as f:
        truth = list(csv.DictReader(f))
    spectra, masks = data["reflectance"], data["valid_mask"]
    w, bp = data["band_centers_um"], data["fwhm_um"]
    n = len(spectra)
    off_engine = MicaEngine()
    for rule in off_engine.rf.values():
        rule.pop("max_depth_ratio_feat1_over_feat0", None)
    off_engine.invalidate_caches()
    on_engine = MicaEngine()
    names = list(on_engine.rf)
    name_to_k = {name: k for k, name in enumerate(names)}
    ratio_k = np.array([name_to_k[r] for r in RATIO_RULES])
    base_fit = np.full((n, len(names)), np.nan)
    ratios = np.full((n, len(RATIO_RULES)), np.nan)
    valid_ratio = np.zeros((n, len(RATIO_RULES)), dtype=bool)

    groups = defaultdict(list)
    for i, mask in enumerate(masks):
        groups[mask.tobytes()].append(i)
    for indices_list in groups.values():
        indices = np.asarray(indices_list, dtype=int)
        chanels = np.flatnonzero(masks[indices[0]])
        wl = w[chanels]
        selected = np.ascontiguousarray(spectra[indices][:, chanels])
        resampled = off_engine.get_resample(w, bp)
        compiled = on_engine._classifier._get_compiled_rules(w, bp, wl, chanels)
        for k, name in enumerate(names):
            try:
                fit, _ = _judge_reference_entry(
                    selected, wl, off_engine.rf[name], resampled, chanels)
            except (InvalidRangeError, InvalidLeftEndPointError, InvalidRightEndPointError):
                continue
            base_fit[indices, k] = fit
        for j, name in enumerate(RATIO_RULES):
            raw = []
            try:
                for pre, weight, cc, fc, dc in compiled[name]["diag"][:2]:
                    *_, depth = _diagnostic_feature(
                        selected, None, wl, None, weight, cc, fc, dc, pre=pre)
                    raw.append(depth)
            except (InvalidRangeError, InvalidLeftEndPointError, InvalidRightEndPointError):
                continue
            raw0, raw1 = raw
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = raw1 / raw0
            ratios[indices, j] = ratio
            valid_ratio[indices, j] = (~np.isnan(raw0)) & (~np.isnan(raw1)) & (raw0 > 0)

    np.savez_compressed(OUT / "threshold_simulation_cache.npz",
                        rule=np.asarray(names, dtype="U42"), ratio_rule=np.asarray(RATIO_RULES, dtype="U42"),
                        base_fit=base_fit, ratio=ratios, valid_ratio=valid_ratio)

    targeted = np.array([r.get("targeted_mix") == "True" for r in truth])
    targeted_high = np.array([r.get("targeted_group") == "high_ratio_confuser" for r in truth])
    targeted_low = np.array([r.get("targeted_group") == "low_ratio_clay" for r in truth])
    single = np.array([r["sample_kind"] == "single_reference" for r in truth])
    source1 = np.array([r["source_rule_1"] for r in truth])
    pure_ref = single & np.isin(source1, PURE + CLAY_MIX)
    pure_confuser = single & np.isin(source1, [
        "calcite", "dolomite", "chlorite_lowFe", "clinochlore",
        "clinochlore_Fe", "thuringite", "epidote",
    ])
    truth_components = [set(filter(None, r["family_set_1"].split(";"))) |
                        set(filter(None, r["family_set_2"].split(";"))) for r in truth]
    pair_keys = np.array(["|".join(sorted((r["source_rule_1"], r["source_rule_2"]))) for r in truth])
    pair_groups = defaultdict(list)
    for i in np.flatnonzero(targeted):
        pair_groups[pair_keys[i]].append(i)
    pair_fold = {}
    for group in (targeted_high, targeted_low):
        keys = sorted({pair_keys[i] for i in np.flatnonzero(group)})
        for j, key in enumerate(keys):
            pair_fold[key] = j % 5
    folds = np.array([pair_fold.get(k, -1) for k in pair_keys])

    def simulate(tpure, tclay):
        modified = base_fit.copy()
        for j, threshold in enumerate([tpure] * len(PURE) + [tclay] * len(CLAY_MIX)):
            reject = valid_ratio[:, j] & (ratios[:, j] >= threshold)
            modified[reject, ratio_k[j]] = np.nan
        score = np.where(np.isfinite(modified), modified, 0.0)
        num = score.argmax(axis=1)
        fired = score.max(axis=1) > 0
        winner = np.where(fired, np.asarray(names)[num], "")
        return winner, fired

    def metrics(tpure, tclay, selected=None):
        selected = np.ones(n, dtype=bool) if selected is None else selected
        winner, fired = simulate(tpure, tclay)
        target_mask = selected & targeted
        exact = np.zeros(n, dtype=bool)
        for i in np.flatnonzero(target_mask):
            exact[i] = fams(str(winner[i])) == truth_components[i]
        ref_mask = selected & pure_ref
        ref_exact = winner[ref_mask] == source1[ref_mask]
        return {
            "correct_total": int(exact[target_mask].sum()),
            "correct_high": int(exact[selected & targeted_high].sum()),
            "correct_low": int(exact[selected & targeted_low].sum()),
            "targeted_n": int(target_mask.sum()),
            "pure_ref_exact": int(ref_exact.sum()),
            "pure_ref_n": int(ref_mask.sum()),
            "pure_mica_winners": int((target_mask & np.isin(winner, PURE)).sum()),
            "no_fire": int((target_mask & ~fired).sum()),
            "confuser_pure_mica": int((selected & pure_confuser & np.isin(winner, PURE)).sum()),
            "winner": winner,
            "fired": fired,
            "component_exact": exact,
        }

    baseline = metrics(0.6, 0.4)
    checks = {
        "M00_winner_reproduced_without_ratio": bool(np.array_equal(
            simulate(np.nan, np.nan)[0], pred["predicted_rule"][list(pred["config"]).index("M00")])),
        "M10_winner_reproduced_at_current_thresholds": bool(np.array_equal(
            baseline["winner"], pred["predicted_rule"][list(pred["config"]).index("M10")])),
        "M10_component_exact_reproduced": bool(np.array_equal(
            baseline["component_exact"][targeted], pred["component_exact"][list(pred["config"]).index("M10"), targeted])),
    }
    if not all(checks.values()):
        raise AssertionError(f"Threshold simulation mismatch: {checks}")

    pure_grid = np.round(np.arange(0.50, 0.8001, 0.025), 3)
    clay_grid = np.round(np.arange(0.30, 0.6001, 0.025), 3)
    candidates = []
    for tpure in pure_grid:
        for tclay in clay_grid:
            m = metrics(float(tpure), float(tclay))
            m = {k: v for k, v in m.items() if k not in ("winner", "fired", "component_exact")}
            candidates.append({"threshold_pure": float(tpure), "threshold_clay": float(tclay), **m})
    with (OUT / "candidate_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(candidates[0]))
        writer.writeheader(); writer.writerows(candidates)

    eligible = [c for c in candidates if c["pure_ref_exact"] >= baseline["pure_ref_exact"]]
    best_correct = max(c["correct_total"] for c in eligible)
    best = [c for c in eligible if c["correct_total"] == best_correct]
    best_pure = max(c["pure_ref_exact"] for c in best)
    best = [c for c in best if c["pure_ref_exact"] == best_pure]
    min_mica = min(c["pure_mica_winners"] for c in best)
    best = [c for c in best if c["pure_mica_winners"] == min_mica]
    min_fire = min(c["no_fire"] for c in best)
    best = [c for c in best if c["no_fire"] == min_fire]
    best.sort(key=lambda c: (abs(c["threshold_pure"] - 0.6) + abs(c["threshold_clay"] - 0.4),
                             c["threshold_pure"], c["threshold_clay"]))
    chosen = best[0]

    fold_rows = []
    for fold in range(5):
        selected = targeted & (folds == fold)
        for label, tpure, tclay in (("baseline", 0.6, 0.4),
                                    ("selected", chosen["threshold_pure"], chosen["threshold_clay"])):
            m = metrics(tpure, tclay, selected=selected)
            fold_rows.append({
                "fold": fold, "config": label, "n": int(selected.sum()),
                "correct_total": m["correct_total"], "correct_high": m["correct_high"],
                "correct_low": m["correct_low"], "pure_mica_winners": m["pure_mica_winners"],
                "no_fire": m["no_fire"], "confuser_pure_mica": m["confuser_pure_mica"],
            })
    with (OUT / "fold_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fold_rows[0]))
        writer.writeheader(); writer.writerows(fold_rows)

    recommendation = {
        "evidence_scope": "Reference-derived development optimization; not independent validation.",
        "selection_rule": (
            "Maximize correct targeted mixture component sets, subject to pure-reference exact "
            "retention >= current 0.6/0.4 baseline; ties maximize pure-reference retention, "
            "then minimize pure-mica winners and no-fire. Closest-to-current breaks final ties."
        ),
        "current": {"threshold_pure": 0.6, "threshold_clay": 0.4,
                    **{k: v for k, v in baseline.items() if k not in ("winner", "fired", "component_exact")}},
        "selected": chosen,
        "simulation_checks": checks,
        "grid": {"pure": [float(pure_grid[0]), float(pure_grid[-1]), 0.025],
                 "clay": [float(clay_grid[0]), float(clay_grid[-1]), 0.025]},
        "fold_metrics_file": "fold_metrics.csv",
    }
    (OUT / "recommendation.json").write_text(
        json.dumps(recommendation, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(recommendation, ensure_ascii=False, indent=2))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
