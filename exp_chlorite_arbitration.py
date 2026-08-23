# -*- coding: utf-8 -*-
"""绿泥石三规则波长仲裁可行性实测(不改代码,只读数据):
对 EMIT 金标准场景中 chlorite_lowFe / clinochlore / clinochlore_Fe 胜出的像元,
用生产同款 _get_quadratic_center 拟合 2250/2350 双带中心,
统计 argmax 标签 vs 中点平铺窗口归属的交叉表。
窗口锚点(chl13 实测): 2250: 2246.09/2249.09/2254.49; 2350: 2332.92/2340.55/2348.83
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cramm import MicaEngine
from cramm.classifier import _get_quadratic_center

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
RULES = ["chlorite_lowFe", "clinochlore", "clinochlore_Fe"]

# 中点平铺窗口界 (nm -> um)
B2250 = [(2246.09 + 2249.09) / 2 / 1000, (2249.09 + 2254.49) / 2 / 1000]  # 2247.59, 2251.79
B2350 = [(2332.92 + 2340.55) / 2 / 1000, (2340.55 + 2348.83) / 2 / 1000]  # 2336.74, 2344.69
# 2350 带无规则内特征,用 chl13 口径 w=(2.30,2.42) v=(2.32,2.37) 构造端点
EP2350 = [2.30, 2.32, 2.37, 2.42]


def window_id(center_nm, bounds_nm):
    """0=lowFe 1=clino 2=Fe, -1=无效"""
    out = np.full(center_nm.shape, -1, dtype=int)
    ok = np.isfinite(center_nm) & (center_nm > 0)
    out[ok & (center_nm < bounds_nm[0])] = 0
    out[ok & (center_nm >= bounds_nm[0]) & (center_nm < bounds_nm[1])] = 1
    out[ok & (center_nm >= bounds_nm[1])] = 2
    return out


def main():
    eng = MicaEngine()
    spectrum, lon, lat, w, bp, wl, chanels = eng.load_emit(NC)
    clf = eng._classifier
    res = clf.classify(spectrum, wl, w, bp, chanels, n_workers=4)

    r, c = res.r, res.c
    num = res.num
    spec = spectrum.reshape(r * c, -1)[:, chanels].astype("float64")
    gidx = [res.index_d[n] for n in RULES]
    print(f"rule indices: {dict(zip(RULES, gidx))}")

    for n, gi in zip(RULES, gidx):
        print(f"  {n:20s} argmax pixels: {int((num == gi).sum())}")

    member = np.isin(num, gidx)
    rows = np.nonzero(member)[0]
    print(f"\ntotal chlorite pixels: {len(rows)}")

    # 2250 中心:逐规则用胜方规则的 feat0 端点(生产行为)
    cen2250 = np.full(r * c, np.nan)
    for n, gi in zip(RULES, gidx):
        m = num == gi
        if not m.any():
            continue
        ep = clf.rf[n]["diagnostic_features"][0]["continuum_endpoints"]
        cen2250[m] = _get_quadratic_center(spec, wl, ep, m)[m]
    # 2350 中心:统一固定窗口
    cen2350 = _get_quadratic_center(spec, wl, EP2350, member)

    c2250_nm = cen2250[rows] * 1000
    c2350_nm = cen2350[rows] * 1000
    argmax_id = np.searchsorted(gidx, num[rows])  # gidx 升序假定;核实如下
    assert sorted(gidx) == gidx or True
    # 直接映射,避免顺序假设
    lut = {gi: i for i, gi in enumerate(gidx)}
    argmax_id = np.array([lut[v] for v in num[rows]])

    w2250 = window_id(c2250_nm, [b * 1000 for b in B2250])
    w2350 = window_id(c2350_nm, [b * 1000 for b in B2350])

    def crosstab(pred, label):
        print(f"\n== argmax (行) vs {label} 窗口归属 (列: lowFe/clino/Fe/无效) ==")
        tab = np.zeros((3, 4), dtype=int)
        for a, p in zip(argmax_id, pred):
            tab[a, p if p >= 0 else 3] += 1
        hdr = ["lowFe", "clino", "Fe", "invalid"]
        print(f"{'':14s}" + "".join(f"{h:>10s}" for h in hdr) + f"{'agree%':>10s}")
        for i, n in enumerate(RULES):
            tot = tab[i].sum()
            ag = tab[i, i] / tot * 100 if tot else 0
            print(f"{n:14s}" + "".join(f"{v:>10d}" for v in tab[i]) + f"{ag:>9.1f}%")

    crosstab(w2250, "2250")
    crosstab(w2350, "2350")

    # 双带门控:两带窗口一致且 != argmax 时才翻转
    both_valid = (w2250 >= 0) & (w2350 >= 0)
    agree_dual = (w2250 == w2350) & both_valid
    flip = agree_dual & (w2250 != argmax_id)
    print(f"\n双带均有效: {both_valid.sum()}/{len(rows)} ({both_valid.mean()*100:.1f}%)")
    print(f"双带一致: {agree_dual.sum()} ({agree_dual.mean()*100:.1f}%)")
    print(f"双带一致且与 argmax 相同: {(agree_dual & (w2250 == argmax_id)).sum()}")
    print(f"双带一致但要翻转: {flip.sum()} ({flip.mean()*100:.2f}%)")
    if flip.sum():
        for i, n in enumerate(RULES):
            for j, m in enumerate(RULES):
                k = ((argmax_id == i) & flip & (w2250 == j)).sum()
                if k:
                    print(f"  {n} -> {m}: {k}")
    # 双带冲突(argmax 无法仲裁的情形)
    conflict = both_valid & (w2250 != w2350)
    print(f"双带冲突(保持原判): {conflict.sum()} ({conflict.mean()*100:.1f}%)")

    # 中心分布概览
    for i, n in enumerate(RULES):
        m = argmax_id == i
        v = c2250_nm[m]
        v = v[np.isfinite(v) & (v > 0)]
        if len(v):
            print(f"{n:20s} 2250中心: n={len(v):6d} median={np.median(v):8.2f} "
                  f"p10={np.percentile(v,10):8.2f} p90={np.percentile(v,90):8.2f}")


if __name__ == "__main__":
    main()
