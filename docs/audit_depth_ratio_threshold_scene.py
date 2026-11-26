#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Full-scene A/B audit for kaolinite-muscovite depth-ratio threshold 0.4 vs 0.55."""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from cramm.mica_engine import MicaEngine  # noqa: E402

NC = ROOT / "EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
OLD = ROOT / "output/lowfe_window_scene_v1/scene_arrays.npz"
OUT = ROOT / "output/depth_ratio_threshold_scene_v1"
RULES = ["kaolinite.5+muscoviteMedAl.5", "kaolinite.5+muscoviteMedhighAl.5",
         "kaolinite+muscovite_mix_intimate"]


def main():
    OUT.mkdir(exist_ok=True)
    if any(OUT.iterdir()):
        raise SystemExit(f"Output directory must be empty: {OUT}")
    old_data = np.load(OLD, allow_pickle=False)
    old_num = old_data["new_num"]  # current engine at 0.4 before threshold update
    names = list(old_data["index"])
    engine = MicaEngine()
    assert all(engine.rf[r]["max_depth_ratio_feat1_over_feat0"] == 0.55 for r in RULES)
    spectrum, _, _, w, bp, wl, chanels = engine.load_emit(str(NC))
    result = engine._classifier.classify(spectrum, wl, w, bp, chanels, n_workers=4)
    new_num = result.num.reshape(1280, 1242)
    changed = old_num != new_num
    transitions = Counter()
    for r, c in np.argwhere(changed):
        transitions[f"{names[old_num[r, c]]}→{names[new_num[r, c]]}"] += 1
    summary = {
        "scene": NC.name,
        "old_config": "current engine with kaolinite-muscovite threshold 0.4",
        "new_config": "current engine with kaolinite-muscovite threshold 0.55",
        "old_array_provenance": str(OLD),
        "changed_labels": int(changed.sum()),
        "transitions": dict(sorted(transitions.items(), key=lambda x: (-x[1], x[0]))),
        "note": "Label changes are controlled A/B evidence, not independent scene accuracy validation.",
    }
    np.savez_compressed(OUT / "scene_arrays.npz", index=np.asarray(names, dtype="U42"),
                        old_num=old_num, new_num=new_num)
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
