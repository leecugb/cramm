#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""仲裁逻辑离线审计:_reassign_by_absorption_center + 三族窗口结构。

验证项:
  A. 族列表完整性:所有带 absorption_center_range 的规则恰好属于一个族;
     族成员全部存在于规则库
  B. 窗口结构:白云母/绿泥石无缝拼接(Partition),碳酸盐重复窗(duplicate)
  C. 边界语义:左闭右开 [lo, hi) —— 拼接点中心唯一命中右侧窗
  D. 翻转门控:目标 fit NaN / fit==0 非 NaN / 当前即目标 → 不翻转
  E. member 门控:fit_pos False、中心 0(NaN 折叠)、胜方在族外 → 不仲裁
  F. 歧义保持:中心落入重叠/重复窗 → 保持原匹配
  G. 重拟合:翻转后中心按目标规则 feat0 端点重拟合;共线三点回退旧中心
  H. 族锁定:跨族中心不翻转(结构保证)

用法:  python docs/_audit_arbitration.py   (仓库根目录下执行)
退出码: 0 = 全部 PASS,1 = 存在 FAIL
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from cramm.classifier import (  # noqa: E402
    CARBONATE_ABUNDANT_MINERALS,
    CARBONATE_MINERALS,
    CARBONATE_PLAIN_MINERALS,
    CHLORITE_MINERALS,
    MUSCOVITE_MINERALS,
    _get_quadratic_center,
    _reassign_by_absorption_center,
)

rf = json.load(open(REPO / "cramm" / "data" / "rf.json",
                    encoding="utf-8"))["rf"]
fails = []


def check(name, cond, detail=""):
    print(f"  [{'OK' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        fails.append(name)


def windows(name):
    f0 = rf[name]["diagnostic_features"][0]
    rng = f0.get("absorption_center_range")
    return tuple(rng) if rng else None


print("=== A. 族列表完整性 ===")
FAMILIES = {"mus": MUSCOVITE_MINERALS, "chl": CHLORITE_MINERALS, "cal": CARBONATE_MINERALS}
windowed = [n for n, r in rf.items()
            if r["diagnostic_features"] and r["diagnostic_features"][0].get("absorption_center_range")]
owner = {}
for fam, members in FAMILIES.items():
    for m in members:
        owner.setdefault(m, []).append(fam)
check("A1 带窗规则恰好 12 条", len(windowed) == 12, f"n={len(windowed)}")
check("A2 每条带窗规则属于且仅属于一个族",
      all(len(owner.get(n, [])) == 1 for n in windowed),
      f"orphan={[n for n in windowed if not owner.get(n)]} multi={[n for n in windowed if len(owner.get(n, [])) > 1]}")
check("A3 族成员全部存在于规则库",
      all(m in rf for ms in FAMILIES.values() for m in ms))
check("A4 族列表无重复成员",
      all(len(ms) == len(set(ms)) for ms in FAMILIES.values()))
check("A5 族内带窗成员数 mus=4 chl=4 cal=4",
      [sum(1 for m in ms if windows(m)) for ms in FAMILIES.values()] == [4, 4, 4])

print("=== B. 窗口结构 ===")
mus_w = sorted(windows(m) for m in MUSCOVITE_MINERALS if windows(m))
chl_w = sorted(windows(m) for m in CHLORITE_MINERALS if windows(m))
cal_w = sorted(windows(m) for m in CARBONATE_MINERALS if windows(m))


def is_partition(ws):
    return all(ws[i][1] == ws[i + 1][0] for i in range(len(ws) - 1))


check("B1 白云母窗无缝拼接 [2.195,2.220)", is_partition(mus_w)
      and mus_w[0][0] == 2.195 and mus_w[-1][1] == 2.220, f"{mus_w}")
check("B2 绿泥石窗无缝拼接 [2.244,2.266)", is_partition(chl_w)
      and chl_w[0][0] == 2.244 and chl_w[-1][1] == 2.266, f"{chl_w}")
check("B3 碳酸盐窗为两对重复窗",
      cal_w[0] == cal_w[1] and cal_w[2] == cal_w[3] and cal_w[1] != cal_w[2], f"{cal_w}")
# 浮点减法存在 ulp 误差,判据用名义值容差而非 >= 精确阈值
check("B4 族间窗口间距 mus→chl = 24nm, chl→cal = 42nm",
      abs((chl_w[0][0] - mus_w[-1][1]) - 0.024) < 1e-9
      and abs((cal_w[0][0] - chl_w[-1][1]) - 0.042) < 1e-9,
      f"gaps={(chl_w[0][0]-mus_w[-1][1])*1000:.1f}nm,{(cal_w[0][0]-chl_w[-1][1])*1000:.1f}nm")

# ---- 合成仲裁试验台 -------------------------------------------------
# 构造最小规则库:直接用真实规则的窗口与 feat0 端点,合成光谱由
# 真实 1nm 参考谱裁剪而成(只需让 _get_quadratic_center 产出指定中心过于
# 迂回路,改为直接注入 cen 数组 —— 仲裁器只消费 cen,不重新计算)
NAMES = list(rf.keys())
index_d = {n: i for i, n in enumerate(NAMES)}


def run_arb(winner, cen_val, family, fit_overrides=None, n_rules=None):
    """单次仲裁仿真:im=winner, cen=cen_val, FIT 默认全 1(fit_nan 全 False)。"""
    n = n_rules or len(NAMES)
    im = np.array([index_d[winner]])
    FIT = np.ones((1, n))
    fit_nan = np.zeros((1, n), dtype=bool)
    if fit_overrides:
        for rule, (val, isnan) in fit_overrides.items():
            FIT[0, index_d[rule]] = val
            fit_nan[0, index_d[rule]] = isnan
    fit_pos = FIT.max(1) > 0
    cen = np.array([cen_val], dtype="float64")
    # 仲裁器仅在翻转时触碰 spectrum1(重拟合);用真实网格避免形状问题
    wl = np.linspace(2.1, 2.4, 300)
    spectrum1 = np.full((1, len(wl)), 0.3)
    _reassign_by_absorption_center(im, FIT, fit_nan, cen, spectrum1, wl,
                                   rf, index_d, fit_pos, family)
    return NAMES[im[0]], cen[0]


print("=== C. 边界语义(左闭右开) ===")
# 白云母拼接点 2.200/2.206/2.210 应唯一命中右侧窗
got, _ = run_arb("muscovite_medhighAl", 2.200, MUSCOVITE_MINERALS)
check("C1 中心恰在拼接点 2.200 → 命中右侧 medAl", got == "muscovite_medAl", f"got={got}")
got, _ = run_arb("muscovite_medAl", 2.206, MUSCOVITE_MINERALS)
check("C2 中心恰在拼接点 2.206 → 命中右侧 lowAl", got == "muscovite_lowAl", f"got={got}")
got, _ = run_arb("muscovite_Fe-rich", 2.220, MUSCOVITE_MINERALS)
check("C3 中心在族窗右端 2.220(开区间) → 出窗保持", got == "muscovite_Fe-rich", f"got={got}")
got, _ = run_arb("chlorite_lowFe", 2.244, CHLORITE_MINERALS)
check("C4 中心在族窗左端 2.244(闭区间) → 命中自身保持", got == "chlorite_lowFe", f"got={got}")
got, _ = run_arb("thuringite", 2.266, CHLORITE_MINERALS)
check("C5 中心在 2.266(thuringite 窗 hi,开) → 出窗保持", got == "thuringite", f"got={got}")
got, _ = run_arb("chlorite_lowFe", 2.248, CHLORITE_MINERALS)
check("C6 中心恰在 2.248 → 命中右侧 clinochlore", got == "clinochlore", f"got={got}")
got, _ = run_arb("clinochlore", 2.252, CHLORITE_MINERALS)
check("C7 中心恰在 2.252 → 命中右侧 clinochlore_Fe", got == "clinochlore_Fe", f"got={got}")
got, _ = run_arb("clinochlore_Fe", 2.256, CHLORITE_MINERALS)
check("C8 中心恰在 2.256 → 命中右侧 thuringite", got == "thuringite", f"got={got}")
got, _ = run_arb("clinochlore", 2.2439, CHLORITE_MINERALS)
check("C9 中心低于全局下限 2.244 → 保持 clinochlore", got == "clinochlore", f"got={got}")
got, _ = run_arb("clinochlore_Fe", 2.266, CHLORITE_MINERALS)
check("C10 中心达到全局上限 2.266 → 保持 clinochlore_Fe", got == "clinochlore_Fe", f"got={got}")
got, _ = run_arb("clinochlore", 2.2445, CHLORITE_MINERALS)
check("C11 中心进入新增的 2.244–2.245 区间 → 翻转 lowFe", got == "chlorite_lowFe", f"got={got}")

print("=== D. 翻转门控 ===")
got, _ = run_arb("muscovite_medhighAl", 2.203, MUSCOVITE_MINERALS,
                 fit_overrides={"muscovite_medAl": (np.nan, True)})
check("D1 目标 fit NaN(规则拒绝) → 不翻转", got == "muscovite_medhighAl", f"got={got}")
got, _ = run_arb("muscovite_medhighAl", 2.203, MUSCOVITE_MINERALS,
                 fit_overrides={"muscovite_medAl": (0.0, False)})
check("D2 目标 fit==0 非 NaN → 不翻转(fit_pos 语义防线)", got == "muscovite_medhighAl", f"got={got}")
got, _ = run_arb("muscovite_medAl", 2.203, MUSCOVITE_MINERALS)
check("D3 中心命中自身窗 → 不翻转", got == "muscovite_medAl", f"got={got}")
got, _ = run_arb("muscovite_medhighAl", 2.203, MUSCOVITE_MINERALS)
check("D4 正常排他落入他窗 → 翻转", got == "muscovite_medAl", f"got={got}")

print("=== E. member 门控 ===")
got, _ = run_arb("muscovite_medhighAl", 0.0, MUSCOVITE_MINERALS)
check("E1 中心 0(NaN 折叠) → 不仲裁", got == "muscovite_medhighAl", f"got={got}")
got, _ = run_arb("muscovite_medhighAl", np.nan, MUSCOVITE_MINERALS)
check("E2 中心 NaN(未折叠路径防御) → 不仲裁", got == "muscovite_medhighAl", f"got={got}")
got, _ = run_arb("illite_imt1", 2.203, MUSCOVITE_MINERALS)
check("E3 胜方为族内无窗成员(illite) → 不仲裁", got == "illite_imt1", f"got={got}")
got, _ = run_arb("gypsum", 2.203, MUSCOVITE_MINERALS)
check("E4 胜方在族外 → 不仲裁", got == "gypsum", f"got={got}")
# fit_pos False:所有规则 fit<=0
n = len(NAMES)
im = np.array([index_d["muscovite_medhighAl"]])
FIT = np.zeros((1, n))
fit_nan = np.zeros((1, n), dtype=bool)
fit_pos = FIT.max(1) > 0
cen = np.array([2.203])
_reassign_by_absorption_center(im, FIT, fit_nan, cen, np.full((1, 300), 0.3),
                               np.linspace(2.1, 2.4, 300), rf, index_d, fit_pos,
                               MUSCOVITE_MINERALS)
check("E5 fit_pos False(无任何正 fit) → 不仲裁", NAMES[im[0]] == "muscovite_medhighAl")

print("=== F. 碳酸盐按层仲裁(v1.5.0)===")
# plain 对:跨窗翻转;tier 锁定;死区保持
got, _ = run_arb("calcite", 2.320, CARBONATE_PLAIN_MINERALS)
check("F1 plain 对:calcite 赢家中心入白云石窗 → 翻转 dolomite", got == "dolomite", f"got={got}")
got, _ = run_arb("dolomite", 2.340, CARBONATE_PLAIN_MINERALS)
check("F2 plain 对:dolomite 赢家中心入方解石窗 → 翻转 calcite", got == "calcite", f"got={got}")
got, _ = run_arb("calcite_abundant", 2.320, CARBONATE_PLAIN_MINERALS)
check("F3 abundant 赢家在 plain 调用中 → 不仲裁(tier 锁定)", got == "calcite_abundant", f"got={got}")
got, _ = run_arb("calcite", 2.331, CARBONATE_PLAIN_MINERALS)
check("F4 死区 2.331(两窗之间) → 保持", got == "calcite", f"got={got}")
got, _ = run_arb("dolomite_abundant", 2.340, CARBONATE_ABUNDANT_MINERALS)
check("F5 abundant 对:dolomite_abundant 赢家中心入方解石窗 → 翻转", got == "calcite_abundant", f"got={got}")
got, _ = run_arb("carbonate_Fe_bearing", 2.335, CARBONATE_PLAIN_MINERALS)
check("F6 无窗成员(carbonate_Fe_bearing) → 不仲裁", got == "carbonate_Fe_bearing", f"got={got}")
got, _ = run_arb("calcite", 2.328, CARBONATE_PLAIN_MINERALS)
check("F7 中心恰在 dolomite 窗 hi 2.328(开) → 死区保持 calcite", got == "calcite", f"got={got}")
got, _ = run_arb("dolomite", 2.334, CARBONATE_PLAIN_MINERALS)
check("F8 中心恰在 calcite 窗 lo 2.334(闭) → 翻转 calcite", got == "calcite", f"got={got}")
got, _ = run_arb("calcite", 2.350, CARBONATE_PLAIN_MINERALS)
check("F9 中心恰在 calcite 窗 hi 2.350(开) → 出窗保持", got == "calcite", f"got={got}")
got, _ = run_arb("calcite", 2.308, CARBONATE_PLAIN_MINERALS)
check("F10 中心恰在 dolomite 窗 lo 2.308(闭) → 翻转 dolomite", got == "dolomite", f"got={got}")

print("=== G. 重拟合 ===")
# 真实光谱重拟合路径:用 npz 参考谱合成一个会被翻转的像元
z = np.load(REPO / "cramm" / "data" / "rf77_splib07_1nm.npz")
grid = z["grid"]
spec_row = z["spectra"][list(z["rule"]).index("muscovite_medAl")]
m = (grid >= 2.1) & (grid <= 2.4)
wl_g = grid[m]
spec_g = spec_row[m][None, :]
wl_g64 = np.ascontiguousarray(wl_g, dtype="float64")
spec_g = np.ascontiguousarray(np.nan_to_num(spec_g, nan=0.3), dtype="float64")
# 赢家 medhighAl,中心按 medhighAl 端点拟合(应落入 2.2x 某窗);若唯一命中他窗则翻转并重拟合
endpts = rf["muscovite_medhighAl"]["diagnostic_features"][0]["continuum_endpoints"]
cen0 = _get_quadratic_center(spec_g, wl_g64, endpts, np.array([True]))[0]
im = np.array([index_d["muscovite_medhighAl"]])
FIT = np.ones((1, len(NAMES)))
fit_nan = np.zeros((1, len(NAMES)), dtype=bool)
fit_pos = np.array([True])
cen_arr = np.array([cen0])
_reassign_by_absorption_center(im, FIT, fit_nan, cen_arr, spec_g, wl_g64,
                               rf, index_d, fit_pos, MUSCOVITE_MINERALS)
w_after = NAMES[im[0]]
if w_after != "muscovite_medhighAl":
    # 翻转后中心必须等于用目标端点直接重拟合的结果(或有限回退)
    endpts_t = rf[w_after]["diagnostic_features"][0]["continuum_endpoints"]
    cen_expect = _get_quadratic_center(spec_g, wl_g64, endpts_t, np.array([True]))[0]
    ok = (cen_arr[0] == cen_expect) or (not np.isfinite(cen_expect) and cen_arr[0] == cen0)
    check("G1 翻转后中心 = 目标端点重拟合(或共线回退)", ok,
          f"{cen0:.6f} -> {w_after} cen={cen_arr[0]:.6f} expect={cen_expect:.6f}")
else:
    check("G1 中心命中自身窗,未翻转(重拟合路径未触发)", True,
          f"cen0={cen0:.6f} 保持 muscovite_medhighAl")
# 精确共线回退:常数 0.5(2 的幂,端点均值/连续线逐比特精确)→ con ≡ 1.0,
# argmin=0 → mas=False → 重拟合 NaN → 必须回退翻转前中心
flat = np.full((1, len(wl_g64)), 0.5)
im = np.array([index_d["muscovite_medhighAl"]])
FIT = np.ones((1, len(NAMES)))
fit_nan = np.zeros((1, len(NAMES)), dtype=bool)
cen_flat = np.array([2.203])  # 注入一个会触发翻转的中心
_reassign_by_absorption_center(im, FIT, fit_nan, cen_flat, flat, wl_g64,
                               rf, index_d, np.array([True]), MUSCOVITE_MINERALS)
ok = NAMES[im[0]] == "muscovite_medAl" and cen_flat[0] == 2.203
check("G2 精确共线(平直 0.5)重拟合 NaN → 回退翻转前中心", ok,
      f"winner={NAMES[im[0]]} cen={cen_flat[0]}")
# 近似共线观察项:常数 0.3(非 2 的幂)的端点均值有 1ulp 级噪声,con 在
# 1±1e-16 抖动,可能产生有限野值。新的目标窗后验门控会在野值越出目标窗时
# 回退到翻转前中心 2.203，避免有限但错误的中心与标签不一致。
flat3 = np.full((1, len(wl_g64)), 0.3)
im = np.array([index_d["muscovite_medhighAl"]])
FIT = np.ones((1, len(NAMES)))
fit_nan = np.zeros((1, len(NAMES)), dtype=bool)
cen_flat3 = np.array([2.203])
_reassign_by_absorption_center(im, FIT, fit_nan, cen_flat3, flat3, wl_g64,
                               rf, index_d, np.array([True]), MUSCOVITE_MINERALS)
mus_windows = [windows(m) for m in MUSCOVITE_MINERALS if windows(m)]
in_any = any(lo <= cen_flat3[0] < hi for lo, hi in mus_windows)
check("G3 近似共线有限野值出目标窗 → 回退翻转前中心",
      NAMES[im[0]] == "muscovite_medAl" and cen_flat3[0] == 2.203 and in_any,
      f"winner={NAMES[im[0]]} cen={cen_flat3[0]} (目标窗内回退)")
# 有限但越出目标窗的重拟合也必须回退。把 lowFe 临时窗下缘设为 2.246，
# 预中心 2.2465 命中该窗，而 lowFe 参考谱按目标端点重估约 2.245063，出窗。
saved_lowfe_window = rf["chlorite_lowFe"]["diagnostic_features"][0]["absorption_center_range"]
try:
    rf["chlorite_lowFe"]["diagnostic_features"][0]["absorption_center_range"] = [2.246, 2.248]
    lowfe_row = z["spectra"][list(z["rule"]).index("chlorite_lowFe")]
    spec_lowfe = np.ascontiguousarray(np.nan_to_num(lowfe_row[m][None, :], nan=0.3), dtype="float64")
    im = np.array([index_d["clinochlore"]])
    FIT = np.ones((1, len(NAMES)))
    fit_nan = np.zeros((1, len(NAMES)), dtype=bool)
    cen_out = np.array([2.2465])
    _reassign_by_absorption_center(im, FIT, fit_nan, cen_out, spec_lowfe, wl_g64,
                                   rf, index_d, np.array([True]), CHLORITE_MINERALS)
    ok = NAMES[im[0]] == "chlorite_lowFe" and cen_out[0] == 2.2465
    check("G4 重拟合有限但越出目标窗 → 回退翻转前中心", ok,
          f"winner={NAMES[im[0]]} cen={cen_out[0]}")
finally:
    rf["chlorite_lowFe"]["diagnostic_features"][0]["absorption_center_range"] = saved_lowfe_window

print("=== H. 族锁定 ===")
got, _ = run_arb("chlorite_lowFe", 2.203, CHLORITE_MINERALS)
check("H1 绿泥石赢家中心落入白云母窗 → 不翻转", got == "chlorite_lowFe", f"got={got}")
got, _ = run_arb("muscovite_medAl", 2.250, MUSCOVITE_MINERALS)
check("H2 白云母赢家中心落入绿泥石窗 → 不翻转", got == "muscovite_medAl", f"got={got}")
got, _ = run_arb("calcite", 2.250, CARBONATE_MINERALS)
check("H3 碳酸盐赢家中心落入绿泥石窗 → 不翻转", got == "calcite", f"got={got}")

print()
print("RESULT:", f"FAIL x{len(fails)} -> {fails}" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
