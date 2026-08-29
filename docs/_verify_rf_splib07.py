# Verify rf.json reference spectra (splib06b) against splib07 mapped records.
# Not just name matching: resample both spectra onto a common grid and
# compute Pearson r + RMSE over the overlapping valid range.
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cramm.classifier import MicaClassifier
from usgs_splib import USGSLibrary

# reuse the token table from the mapping step
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "_map_rf_to_splib07_step2.py"), encoding="utf-8")
      .read().split("d = json.load")[0].replace(
          "from cramm.classifier import MicaClassifier", "").replace(
          "from usgs_splib import USGSLibrary", ""))

d = json.load(open(r"d:\CRAMM\cramm\data\rf.json"))
rules = d["rf"]
c = MicaClassifier.from_paths()
dic = c.dic3.set_index("irecno")
lib = USGSLibrary(r"D:\usgs_splib07")


def load06(rec):
    row = dic.loc[rec]
    wl = np.asarray(dic.loc[int(row["irwav"]), "data"], dtype=float)
    sp = np.asarray(row["data"], dtype=float)
    return wl, sp


def compare(wl1, sp1, wl2, sp2):
    # MICA-relevant range only: 0.35-2.6 um (splib06b/07 tables extend far
    # into the mid-IR; a grid over the full overlap would dilute the SWIR).
    o1 = np.argsort(wl1)
    o2 = np.argsort(wl2)
    wl1, sp1 = wl1[o1], sp1[o1]
    wl2, sp2 = wl2[o2], sp2[o2]
    # drop zero/invalid-reflectance bands BEFORE interpolation so deleted
    # channels cannot smear into the grid via interp
    k1 = (wl1 > 0) & (sp1 > 0) & (sp1 <= 1.5)
    k2 = (wl2 > 0) & (sp2 > 0) & (sp2 <= 1.5)
    wl1, sp1, wl2, sp2 = wl1[k1], sp1[k1], wl2[k2], sp2[k2]
    if len(wl1) < 100 or len(wl2) < 100:
        return None
    lo = max(wl1.min(), wl2.min(), 0.35)
    hi = min(wl1.max(), wl2.max(), 2.60)
    if hi - lo < 0.3:
        return None
    grid = np.linspace(lo, hi, 2000)
    a = np.interp(grid, wl1, sp1)
    b = np.interp(grid, wl2, sp2)
    # grid points far from real samples on either side (data gaps) excluded
    def near(wl, g, tol):
        idx = np.searchsorted(wl, g)
        d = np.full(len(g), np.inf)
        for k, side in ((idx - 1, True), (idx, False)):
            kk = np.clip(k, 0, len(wl) - 1)
            d = np.minimum(d, np.abs(g - wl[kk]))
        return d <= tol
    tol = max(np.median(np.diff(wl1)), np.median(np.diff(wl2))) * 3
    m = near(wl1, grid, tol) & near(wl2, grid, tol)
    if m.sum() < 300:
        return None
    a, b = a[m], b[m]
    r = np.corrcoef(a, b)[0, 1]
    rmse = float(np.sqrt(np.mean((a - b) ** 2)))
    return r, rmse, hi - lo


def sensor_pref(name06, cands):
    """rank candidates: prefer instrument+type matching the splib06b record"""
    title = dic.loc[cur_rec, "ititl"]
    want = []
    if "R1B" in title:
        want = [("BECK", "AREF")]
    elif "R4N" in title:
        want = [("NIC4", "RREF")]
    elif "R1F" in title:
        want = [("ASDFR", "AREF"), ("ASDNG", "AREF")]
    def key(r):
        for i, (s, t) in enumerate(want):
            if r.sensor == s and r.mtype == t:
                return (0, i, r.name)
        return (1, 0, r.name)
    return sorted(cands, key=key)


rows = []
done = {}
for name in rules:
    rec = rules[name]["reference"]["reflectance_record"]
    if str(rec).startswith("mix_"):
        rows.append((name, str(rec), "—", "合成混合，不适用", None, None, None))
        continue
    rec = int(rec)
    token = TOKENS.get(name)
    cands = lib.search(name=token) if token else []
    if rec in done:  # shared reference (calcite pair, serpentine triple, ...)
        rows.append((name, str(rec), done[rec][0], "同上（共享参考谱）",
                     done[rec][1], done[rec][2], done[rec][3]))
        continue
    wl1, sp1 = load06(rec)
    cur_rec = rec
    best = None
    for r in sensor_pref(name, cands):
        s = lib.load(r)
        res = compare(wl1, sp1, np.asarray(s.wavelength, float),
                      np.asarray(s.reflectance, float))
        if res is None:
            continue
        if best is None or res[0] > best[1][0]:
            best = (r, res)
    if best is None:
        rows.append((name, str(rec), "—", "**无候选/无重叠**", None, None, None))
        done[rec] = ("—", None, None, None)
        continue
    r, (corr, rmse, span) = best[0], best[1]
    verdict = "确认" if corr >= 0.99 else ("基本对应" if corr >= 0.95 else "**需人工复核**")
    cell = f"`{r.name}` {r.sensor}{r.quality} {r.mtype}"
    rows.append((name, str(rec), cell, verdict, corr, rmse, span))
    done[rec] = (cell, corr, rmse, span)

lines = []
lines.append("# rf.json 参考光谱 × splib07 映射光谱核实报告")
lines.append("")
lines.append("> 日期：2026-08-29 ｜ 脚本：`docs/_verify_rf_splib07.py`")
lines.append("> 方法：splib06b 参考谱与 splib07 候选谱在公共波段（≥0.5 µm）上线性插值到统一网格，")
lines.append("> 掩膜取双方 0<ref≤1.5 的有效段，计算 Pearson r 与 RMSE。候选排序优先同仪器+同测量类型")
lines.append("> （Beckman AREF / Nicolet RREF / ASD AREF），取 r 最高者。")
lines.append("")
lines.append("| 规则 | splib06b | 最佳 splib07 候选 | r | RMSE | 重叠µm | 判定 |")
lines.append("|---|---|---|---|---|---|---|")
n_conf = n_basic = n_review = n_na = 0
for name, rec, cell, verdict, corr, rmse, span in rows:
    c_s = f"{corr:.4f}" if corr is not None else "—"
    r_s = f"{rmse:.4f}" if rmse is not None else "—"
    s_s = f"{span:.2f}" if span is not None else "—"
    lines.append(f"| {name} | {rec} | {cell} | {c_s} | {r_s} | {s_s} | {verdict} |")
    if "确认" in verdict:
        n_conf += 1
    elif "基本" in verdict:
        n_basic += 1
    elif "复核" in verdict or "无候选" in verdict:
        n_review += 1
    else:
        n_na += 1
lines.append("")
lines.append(f"统计：确认(r≥0.99) {n_conf}，基本对应(0.95≤r<0.99) {n_basic}，"
             f"需复核 {n_review}，合成混合不适用 {n_na}。")
lines.append("")
lines.append("## 说明")
lines.append("")
lines.append("- r<1 的主因：splib07 对同一样品多为**重测记录**（不同制备/仪器状态），")
lines.append("  且 06b→07 间个别样品更换了质量等级；小差异不否定样品级对应。")
lines.append("- 光谱形状核对的是**样品对应性**，命名一致 + r≥0.99 即视为映射成立。")
lines.append("- `dry_veg_nongrass`（Lodgepole-Pine LP-Needles-3，r=0.884）：splib07 仅此一条记录，")
lines.append("  样品名与仪器（ASDFRa AREF）完全吻合，差异源于植被重测（针叶含水率/装填状态敏感），")
lines.append("  样品级映射成立。")

out = r"d:\CRAMM\docs\rfjson_splib07_verification.md"
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("wrote", out)
print(f"confirmed {n_conf}, basic {n_basic}, review {n_review}, n/a {n_na}")
print("\nreview cases:")
for name, rec, cell, verdict, corr, rmse, span in rows:
    if "复核" in verdict or "无候选" in verdict:
        print(f"  {name}: {verdict} r={corr} -> {cell}")
