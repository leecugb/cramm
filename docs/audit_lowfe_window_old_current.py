#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Isolate the lowFe lower-bound effect using the current engine throughout."""
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
NEW = REPO / "output/lowfe_window_scene_v1/scene_arrays.npz"
OUT = REPO / "output/lowfe_window_scene_old_current_v1"


def transitions(before, after, names, indices, selected):
    counts = Counter()
    for i in indices:
        mask = selected & (before == i)
        for j in np.unique(after[mask]):
            counts[f"{names[i]}→{names[j]}"] += int((after[mask] == j).sum())
    return dict(sorted(counts.items()))


def main():
    OUT.mkdir(exist_ok=True)
    if any(OUT.iterdir()):
        raise SystemExit(f"Output directory must be empty: {OUT}")
    saved = np.load(NEW, allow_pickle=False)
    names = list(saved["index"])
    pure_num = saved["pure_num"]
    new_num = saved["new_num"]
    engine = MicaEngine()
    engine.rf["chlorite_lowFe"]["diagnostic_features"][0]["absorption_center_range"] = [2.245, 2.248]
    engine.invalidate_caches()
    spectrum, _, _, w, bp, wl, chanels = engine.load_emit(str(NC))
    old = engine._classifier.classify(spectrum, wl, w, bp, chanels, n_workers=4)
    old_num = old.num.reshape(1280, 1242)
    chl_indices = [names.index(n) for n in CHLORITE_MINERALS]
    selected = np.isin(pure_num, chl_indices)
    direct = old_num != new_num
    summary = {
        "scene": NC.name,
        "comparison": "current engine: lowFe 2.245 vs 2.244 lower bound",
        "old_current_window": [2.245, 2.248],
        "new_window": [2.244, 2.248],
        "old_current_chlorite_flips": int(((pure_num != old_num) & selected).sum()),
        "new_chlorite_flips": int(((pure_num != new_num) & selected).sum()),
        "old_current_transitions": transitions(pure_num, old_num, names, chl_indices, selected),
        "new_transitions": transitions(pure_num, new_num, names, chl_indices, selected),
        "direct_old_to_new_changed_labels": int(direct.sum()),
        "direct_old_to_new_transitions": transitions(old_num, new_num, names, chl_indices, np.isin(old_num, chl_indices)),
        "direct_cross_family_changes": int((np.isin(old_num, chl_indices) != np.isin(new_num, chl_indices)).sum()),
    }
    np.savez_compressed(OUT / "old_current_arrays.npz",
                        old_num=old_num,
                        old_chl_center=old.chl_center.reshape(1280, 1242))
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
