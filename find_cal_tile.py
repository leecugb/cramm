# -*- coding: utf-8 -*-
"""Temporary: find a carbonate-rich 100x100 tile for the cal_center integration test."""
import numpy as np

from cramm.emit_reader import EmitReader
from cramm.mica_engine import MicaEngine

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"


def main():
    e = MicaEngine()
    spectrum, lon, lat, w, bp, wl, chanels = EmitReader.load(NC)
    res = e._classifier.classify(spectrum, wl, w, bp, chanels, n_workers=4)
    cal_names = ["calcite_abundant", "calcite", "dolomite_abundant", "dolomite", "carbonate_Fe_bearing"]
    cal_idx = [res.index_d[n] for n in cal_names if n in res.index_d]
    r, c = res.r, res.c
    num = res.num.reshape(r, c)
    winner = np.isin(num, cal_idx) & (res.fit.reshape(r, c) > 0)
    cen = res.cal_center.reshape(r, c)
    print(f"total carbonate winners: {winner.sum()}", flush=True)
    print(f"cal_center>0 count: {(cen > 0).sum()}, "
          f"range [{cen[cen > 0].min():.4f}, {cen[cen > 0].max():.4f}]", flush=True)
    # per-name stats
    for n in cal_names:
        if n in res.index_d:
            m = (num == res.index_d[n]) & (res.fit.reshape(r, c) > 0)
            print(f"  {n:28s} winners={m.sum()}", flush=True)
    # best 100x100 blocks
    best = []
    for r0 in range(0, r - 100, 50):
        for c0 in range(0, c - 100, 50):
            best.append((int(winner[r0:r0 + 100, c0:c0 + 100].sum()), r0, c0))
    best.sort(reverse=True)
    for cnt, r0, c0 in best[:8]:
        blk = cen[r0:r0 + 100, c0:c0 + 100]
        pos = blk[blk > 0]
        print(f"tile [{r0}:{r0+100}, {c0}:{c0+100}] winners={cnt} "
          f"center_range=[{pos.min():.4f},{pos.max():.4f}]" if cnt else f"tile [{r0}:{r0+100},{c0}:{c0+100}] 0", flush=True)


if __name__ == "__main__":
    main()
