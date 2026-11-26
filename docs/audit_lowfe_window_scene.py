#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Controlled full-scene audit of the lowFe [2.244,2.248) window update."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from cramm.classifier import CHLORITE_MINERALS  # noqa: E402
from cramm.mica_engine import MicaEngine  # noqa: E402

NC = REPO / "EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
OLD = REPO / "docs/figures/data/num_ab.npz"
OUT = REPO / "output/lowfe_window_scene_v1"


def transitions(before, after, indices, selected, names):
    counts = Counter()
    for i in indices:
        mask = selected & (before == i)
        if not mask.any():
            continue
        for j in np.unique(after[mask]):
            counts[f"{names[i]}→{names[j]}"] += int((after[mask] == j).sum())
    return dict(sorted(counts.items()))


def main():
    OUT.mkdir(exist_ok=True)
    if any(OUT.iterdir()):
        raise SystemExit(f"Output directory must be empty: {OUT}")
    engine = MicaEngine()
    spectrum, _, _, w, bp, wl, chanels = engine.load_emit(str(NC))
    new = engine._classifier.classify(spectrum, wl, w, bp, chanels, n_workers=4)
    pure_engine = MicaEngine()
    for name in CHLORITE_MINERALS:
        pure_engine.rf[name]["diagnostic_features"][0].pop("absorption_center_range", None)
    pure_engine.invalidate_caches()
    pure = pure_engine._classifier.classify(spectrum, wl, w, bp, chanels, n_workers=4)

    shape = (1280, 1242)
    new_num = new.num.reshape(shape)
    pure_num = pure.num.reshape(shape)
    old = np.load(OLD, allow_pickle=False)
    old_index = list(old["index"])
    current_index = list(new.index)
    if old_index != current_index:
        raise ValueError("Archived and current rule order differ")
    old_num_a = old["num_a"]
    old_num_b = old["num_b"]
    chl_indices = [current_index.index(n) for n in CHLORITE_MINERALS]
    old_chl = np.isin(old_num_b, chl_indices)
    current_chl = np.isin(pure_num, chl_indices)
    old_pure_equal = bool(np.array_equal(old_num_b[current_chl], pure_num[current_chl]))
    old_pure_mask_equal = bool(np.array_equal(old_chl, current_chl))

    old_changes = old_num_b != old_num_a
    new_changes = pure_num != new_num
    summary = {
        "scene": NC.name,
        "new_window": [2.244, 2.248],
        "old_archived_window": [2.245, 2.248],
        "old_archive": "docs/figures/data/num_ab.npz",
        "old_pure_chlorite_mask_equal_current": old_pure_mask_equal,
        "old_pure_chlorite_labels_equal_current": old_pure_equal,
        "old_archived_chlorite_flip_count": int((old_changes & old_chl).sum()),
        "new_chlorite_flip_count": int((new_changes & current_chl).sum()),
        "old_archived_transitions": transitions(
            old_num_b, old_num_a, chl_indices, old_chl, current_index),
        "new_transitions": transitions(pure_num, new_num, chl_indices, current_chl, current_index),
        "current_new_vs_pure_changed_chlorite_labels": int((new_changes & current_chl).sum()),
        "old_archived_vs_new_window_label_changes": int((old_num_a != new_num).sum()),
        "old_archived_vs_new_window_transitions": transitions(
            old_num_a, new_num, chl_indices, np.isin(old_num_a, chl_indices), current_index),
        "cross_family_chlorite_changes": int((
            np.isin(pure_num, chl_indices) != np.isin(new_num, chl_indices)).sum()),
    }
    np.savez_compressed(
        OUT / "scene_arrays.npz",
        index=np.asarray(current_index, dtype="U42"),
        pure_num=pure_num,
        new_num=new_num,
        pure_chl_center=pure.chl_center.reshape(shape),
        new_chl_center=new.chl_center.reshape(shape),
    )
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
