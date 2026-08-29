# -*- coding: utf-8 -*-
"""Production arbitration statistics for the paper archive (docs/arbitration_stats.md).

Method: two full-scene classifies —
  A) production rf.json (all absorption_center_range windows active)
  B) same rules with every absorption_center_range stripped (pure argmax MICA)
The NUM diff A-vs-B gives the exact production flip statistics for all three
wavelength-arbitrated families (muscovite / chlorite / carbonate) in one shot:
every differing pixel is a flip performed by _reassign_by_absorption_center.
Also archives per-rule winner counts and center-layer ranges from run A.

Run from the repo root (NC path is relative). ~3 min at n_workers=4.
"""
import copy
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cramm import MicaEngine
from cramm.classifier import MUSCOVITE_MINERALS, CHLORITE_MINERALS, CARBONATE_MINERALS

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
OUT_MD = "docs/arbitration_stats.md"
OUT_JSON = "docs/arbitration_stats.json"

FAMILIES = {
    "muscovite": (MUSCOVITE_MINERALS, "mus_center"),
    "chlorite": (CHLORITE_MINERALS, "chl_center"),
    "carbonate": (CARBONATE_MINERALS, "cal_center"),
}


def strip_windows(rf):
    out = copy.deepcopy(rf)
    n = 0
    for rule in out.values():
        feats = rule.get("diagnostic_features") or []
        if feats and feats[0].pop("absorption_center_range", None) is not None:
            n += 1
    return out, n


def main():
    eng = MicaEngine()
    spectrum, lon, lat, w, bp, wl, chanels = eng.load_emit(NC)
    clf = eng._classifier

    t0 = time.time()
    res_a = clf.classify(spectrum, wl, w, bp, chanels, n_workers=4)
    t_a = time.time() - t0
    print(f"[run A: production, windowed] {t_a:.1f}s", flush=True)

    saved_rf = clf.rf
    stripped, n_stripped = strip_windows(saved_rf)
    print(f"[stripped absorption_center_range from {n_stripped} rules]", flush=True)
    try:
        clf.rf = stripped
        clf.invalidate_caches()
        t0 = time.time()
        res_b = clf.classify(spectrum, wl, w, bp, chanels, n_workers=4)
        t_b = time.time() - t0
        print(f"[run B: pure argmax, no windows] {t_b:.1f}s", flush=True)
    finally:
        clf.rf = saved_rf
        clf.invalidate_caches()

    assert res_a.index == res_b.index, "rule sets must be identical"
    index = res_a.index
    num_a, num_b = res_a.num, res_b.num
    flip_mask = num_a != num_b
    print(f"total flips: {flip_mask.sum()}", flush=True)

    stats = {"scene": os.path.basename(NC), "runtime_s": {"windowed": round(t_a, 1),
             "pure_argmax": round(t_b, 1)}, "total_flips": int(flip_mask.sum()),
             "families": {}}

    lines = []
    lines.append("# Wavelength-arbitration production statistics\n")
    lines.append(f"Scene: `{os.path.basename(NC)}` ({res_a.r}x{res_a.c})")
    lines.append(f"Method: production rf.json (all windows) vs the same rules with every "
                 f"`absorption_center_range` stripped (pure argmax MICA); every NUM diff is a "
                 f"production flip by `_reassign_by_absorption_center`.")
    lines.append(f"Runtime: windowed {t_a:.1f}s, pure-argmax {t_b:.1f}s (n_workers=4; "
                 f"wall times are machine-load dependent -- the controlled benchmark "
                 f"measurement is 59.8s vs 60.0s, docs/benchmark.json).\n")
    lines.append(f"**Total flips: {int(flip_mask.sum())}**\n")

    for fam, (members, cen_attr) in FAMILIES.items():
        mem_idx = {n: res_a.index_d[n] for n in members if n in res_a.index_d}
        cen = getattr(res_a, cen_attr)
        lines.append(f"## {fam} family\n")
        lines.append("| rule | window | winners (A) | flips in | flips out | center range (um) |")
        lines.append("|---|---|---|---|---|---|")
        fam_stat = {}
        for n, gi in mem_idx.items():
            win = (saved_rf[n]["diagnostic_features"][0].get("absorption_center_range")
                   or "-")
            winners_a = int((num_a == gi).sum())
            flips_in = int(((num_a == gi) & flip_mask).sum())
            flips_out = int(((num_b == gi) & flip_mask).sum())
            cvals = cen[(num_a == gi) & (cen > 0)]
            crange = (f"[{cvals.min():.5f}, {cvals.max():.5f}]" if len(cvals) else "-")
            lines.append(f"| {n} | {win} | {winners_a} | {flips_in} | {flips_out} | {crange} |")
            fam_stat[n] = {"window": win, "winners": winners_a, "flips_in": flips_in,
                           "flips_out": flips_out, "center_range": crange}
        # from->to flip pairs inside/involving this family
        fam_gidx = set(mem_idx.values())
        fam_flip = flip_mask & (np.isin(num_b, list(fam_gidx)) | np.isin(num_a, list(fam_gidx)))
        pairs = {}
        for a, b in zip(num_a[fam_flip], num_b[fam_flip]):
            key = f"{index[b]} -> {index[a]}"
            pairs[key] = pairs.get(key, 0) + 1
        if pairs:
            lines.append("\nflip pairs (pure-argmax attribution -> arbitrated attribution):")
            for k, v in sorted(pairs.items(), key=lambda kv: -kv[1]):
                lines.append(f"- {k}: {v}")
        else:
            lines.append("\nno flips involving this family.")
        lines.append("")
        fam_stat["flip_pairs"] = pairs
        stats["families"][fam] = fam_stat

    # any flip NOT involving any family member (should be impossible)
    all_idx = [res_a.index_d[n] for members, _ in FAMILIES.values() for n in members
               if n in res_a.index_d]
    outside = flip_mask & ~np.isin(num_a, all_idx) & ~np.isin(num_b, all_idx)
    lines.append(f"## sanity\n\nflips not involving any arbitrated family: {int(outside.sum())} "
                 "(must be 0)\n")
    stats["flips_outside_families"] = int(outside.sum())

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"archived -> {OUT_MD} / {OUT_JSON}", flush=True)


if __name__ == "__main__":
    main()
