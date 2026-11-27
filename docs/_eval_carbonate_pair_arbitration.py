#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""评估碳酸盐仲裁优化提案:abundant 对 / plain 对分别组内竞争。

步骤:
1. 全场景 classify(raw)一次,取 num / cal_center / fit
2. 候选翻转集(上界):赢家在 abundant 对且 cal_center 落入对方窗(反之亦然);
   plain 对同理
3. 对候选像元补算目标规则 fit(_judge_reference_entry),应用完整门控
   (目标 fit 非 NaN 且 >0)→ 精确翻转数
"""
import sys
import time

import numpy as np

sys.path.insert(0, "/home/lee/CRAMM/repo/src")
from cramm.mica_engine import MicaEngine  # noqa: E402
from cramm.classifier import _judge_reference_entry  # noqa: E402

NC = "/home/lee/CRAMM/EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"


def main():
    eng = MicaEngine()
    clf = eng._classifier
    spectrum, lon, lat, w, bp, wl, chanels = eng.load_emit(NC)
    t0 = time.time()
    res = clf.classify(spectrum, wl, w, bp, chanels, n_workers=4)
    print(f"classify: {time.time()-t0:.0f}s", flush=True)

    num = res.num
    cal = res.cal_center
    index = res.index
    idx = {n: i for i, n in enumerate(index)}

    PAIRS = [("calcite_abundant", "dolomite_abundant"), ("calcite", "dolomite")]
    W = {"calcite_abundant": (2.334, 2.350), "calcite": (2.334, 2.350),
         "dolomite_abundant": (2.308, 2.328), "dolomite": (2.308, 2.328)}

    spec2d = spectrum.reshape(-1, spectrum.shape[2])[:, chanels]
    resampled1 = clf.get_resample(w, bp)

    total_cand = 0
    total_flip = 0
    for a, b in PAIRS:
        for src, tgt in [(a, b), (b, a)]:
            lo, hi = W[tgt]
            cand = np.nonzero((num == idx[src]) & (cal >= lo) & (cal < hi))[0]
            total_cand += len(cand)
            if not len(cand):
                print(f"{src} -> {tgt}: 候选 0")
                continue
            # 完整门控:目标规则对候选像元的 fit 必须非 NaN 且 > 0
            sub = spec2d[cand]
            try:
                fit, _ = _judge_reference_entry(sub, wl, clf.rf[tgt], resampled1, chanels)
            except Exception as e:
                print(f"{src} -> {tgt}: 目标规则异常 {e}")
                continue
            ok = ~np.isnan(fit) & (fit > 0)
            nflip = int(ok.sum())
            total_flip += nflip
            print(f"{src} -> {tgt}: 候选 {len(cand)}, 过门控 {nflip} "
                  f"({nflip/num.size*100:.4f}% 全场景)")
            if nflip:
                cen = cal[cand][ok]
                print(f"    中心分布: min={cen.min():.4f} med={np.median(cen):.4f} max={cen.max():.4f}")

    print(f"\n候选合计 {total_cand},精确翻转合计 {total_flip} / {num.size} 像元 "
          f"({total_flip/num.size*100:.4f}%)")
    # 碳酸盐赢家总量(分母参考)
    n_cal = int(np.isin(num, [idx[n] for n in W]).sum())
    print(f"碳酸盐四规则赢家总量 {n_cal} ({n_cal/num.size*100:.2f}%)")


if __name__ == "__main__":
    main()
