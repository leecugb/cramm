#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""rf77_splib07_1nm.npz 离线完整性审计(不依赖 USGS splib07 库 / splib06b)。

验证项(2026-09-02 首次执行全部 PASS,详见 docs/rf77_bundle_audit.md):
  A. 网格完整性:2151 点,0.35-2.50 um,严格均匀 1 nm、单调
  B. 77 行规则键与当前规则库 rf.keys() 顺序完全一致
  C. label 分类:65 实物(51 直接 + 5 [AMX] + 2 [alias] GDS212/213 + 7 复用)+ 12 synth
  D. 实物行 label 与 docs/splib07_selection.json 的选定记录一致(12 条 synth 除外)
  E. NaN 结构:无内部 NaN(桥接烘焙),量程外 NaN 正常;无全 NaN 行
  F. AMX/alias label 与 selection.json AMX 映射、旧 rf.json GDS212/213 别名一致
  G. 12 条合成混合行 == 端元行按旧 rf.json mixtures 配比加权和(bit-exact,
     NaN 掩码一致);旧 rf.json 从 git 历史 11b0f53 读取
  H. docs/rf77_splib07_1nm.csv 镜像一致(数值容差 5e-7,csv 6 位小数舍入)
  J. 值域:全部有限值为正,无全行非正

用法:  python docs/_audit_rf77_bundle.py   (仓库根目录下执行)
退出码: 0 = 全部 PASS,1 = 存在 FAIL
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
NPZ = REPO / "cramm" / "data" / "rf77_splib07_1nm.npz"
RF = REPO / "cramm" / "data" / "temp_rf_notfeatures_renamed.json"
SEL = REPO / "docs" / "splib07_selection.json"
CSV = REPO / "docs" / "rf77_splib07_1nm.csv"
OLD_RF_COMMIT = "11b0f53"  # 最后一个含 cramm/data/rf.json(带 mixtures)的提交

fails = []


def check(name, cond, detail=""):
    print(f"  [{'OK' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        fails.append(name)


z = np.load(NPZ, allow_pickle=False)
grid, rule, label, spectra = z["grid"], z["rule"], z["label"], z["spectra"]
rf = json.load(open(RF, encoding="utf-8"))["rf"]
sel = json.load(open(SEL, encoding="utf-8"))
old = json.loads(subprocess.run(
    ["git", "-C", str(REPO), "show", f"{OLD_RF_COMMIT}:cramm/data/rf.json"],
    capture_output=True, text=True, check=True).stdout)
mixdefs, rules_old = old["mixtures"], old["rf"]

print("=== A. grid integrity ===")
check("A1 grid len", len(grid) == 2151, f"len={len(grid)}")
check("A2 grid lo/hi", abs(grid[0] - 0.35) < 1e-12 and abs(grid[-1] - 2.5) < 1e-9,
      f"{grid[0]}..{grid[-1]}")
check("A3 grid uniform 1nm", bool(np.allclose(np.diff(grid), 0.001, atol=1e-12)))
check("A4 grid monotonic", bool((np.diff(grid) > 0).all()))

print("=== B. rule keys vs rf ===")
check("B1 77 rows", len(rule) == 77, f"n={len(rule)}")
check("B2 order == rf.keys()", list(rule) == list(rf.keys()))
check("B3 spectra shape", spectra.shape == (77, 2151), f"{spectra.shape}")

print("=== C. label taxonomy ===")
n_amx = sum(1 for lb in label if lb.endswith("[AMX]"))
n_alias = sum(1 for lb in label if lb.endswith("[alias]"))
n_synth = sum(1 for lb in label if lb.lower().startswith("synth"))
check("C1 5 [AMX]", n_amx == 5, f"n={n_amx}")
check("C2 2 [alias]", n_alias == 2, f"n={n_alias}")
check("C3 12 synth", n_synth == 12, f"n={n_synth}")
check("C4 65 physical", 77 - n_synth == 65)

print("=== D. label vs selection.json ===")
exp = {}
for rec06, s in sel["references"].items():
    for r in s["rules"]:
        exp[r] = s["splib07_record"]
for a in sel["amx_mixture_aliases"]:
    exp[a["rule"]] = a["amx_record"]
mismatch = [(r, lb) for r, lb in zip(rule, label)
            if exp.get(str(r)) is not None and exp[str(r)] not in str(lb)]
noentry = [str(r) for r in rule if exp.get(str(r)) is None]
check("D1 physical labels match selection", not mismatch, f"mismatch={mismatch[:3]}")
check("D2 selection-less rules are exactly the 12 synth",
      sorted(noentry) == sorted(str(r) for r, lb in zip(rule, label)
                                if str(lb).lower().startswith("synth")),
      f"n={len(noentry)}")

print("=== E. NaN structure ===")
all_nan_rows = [str(r) for i, r in enumerate(rule) if np.isnan(spectra[i]).all()]
interior = 0
for i in range(77):
    sp = spectra[i]
    valid = ~np.isnan(sp)
    if valid.any():
        idx = np.nonzero(valid)[0]
        interior += int(np.isnan(sp[idx[0]:idx[-1] + 1]).sum())
check("E1 no all-NaN row", not all_nan_rows, f"{all_nan_rows}")
check("E2 no interior NaN (bridged bake)", interior == 0, f"interior={interior}")

print("=== F. AMX / alias labels ===")
amx_ok = all(a["amx_record"] in str(label[list(rule).index(a["rule"])])
             for a in sel["amx_mixture_aliases"])
check("F1 5 AMX labels match selection", amx_ok)
alias_expect = {"calcite.8+montmorilloniteNa.2_mix_intimate": "GDS212",
                "kaolinite.2+calcite.8_mix_intimate": "GDS213"}
alias_ok = all(alias_expect[r] in str(label[list(rule).index(r)])
               and str(label[list(rule).index(r)]).endswith("[alias]")
               for r in alias_expect)
check("F2 GDS212/213 alias labels", alias_ok)

print("=== G. synth rows == weighted endmember sum (bit-exact) ===")
row = {str(r): i for i, r in enumerate(rule)}
amx_rules = {a["rule"] for a in sel["amx_mixture_aliases"]}
n_syn_checked = 0
for rname, ru in rules_old.items():
    rec = str(ru["reference"]["reflectance_record"])
    if not rec.startswith("mix_") or rname in amx_rules:
        continue
    comp = mixdefs[rec]
    if len(comp) == 1 and list(comp.values())[0] == 1.0:
        continue  # GDS212/213 alias, not synthesized
    acc = np.zeros(2151)
    ok = True
    for cid, w in comp.items():
        users = [n for n, r2 in rules_old.items()
                 if str(r2["reference"]["reflectance_record"]) == cid]
        if not users:
            ok = False
            break
        acc = acc + w * spectra[row[users[0]]]
    if not ok:
        check(f"G synth {rname}", False, "endmember not resolvable")
        continue
    target = spectra[row[rname]]
    same_mask = bool((np.isnan(acc) == np.isnan(target)).all())
    both = ~np.isnan(acc) & ~np.isnan(target)
    maxd = float(np.abs(acc[both] - target[both]).max()) if both.any() else 0.0
    check(f"G synth {rname}", same_mask and maxd == 0.0,
          f"max|d|={maxd:.1e} mask_equal={same_mask}")
    n_syn_checked += 1
check("G0 all 12 synth verified", n_syn_checked == 12, f"n={n_syn_checked}")

print("=== H. csv mirror ===")
try:
    import pandas as pd
    df = pd.read_csv(CSV)
    wcols = [c for c in df.columns if c not in ("rule", "label")]
    check("H1 csv grid", np.allclose([float(c) for c in wcols], grid, atol=1e-9))
    check("H2 csv rule order", list(df["rule"]) == list(rule))
    check("H3 csv label", list(df["label"]) == list(label))
    M = df[wcols].to_numpy(float)
    maxd = 0.0
    for i in range(77):
        a, b = M[i], spectra[i]
        both = ~np.isnan(a) & ~np.isnan(b)
        if not bool((np.isnan(a) == np.isnan(b)).all()):
            check("H4 csv mask", False, f"row {rule[i]}")
            break
        maxd = max(maxd, float(np.abs(a[both] - b[both]).max()) if both.any() else 0.0)
    else:
        check("H4 csv values within 6-decimal rounding", maxd <= 5.1e-7, f"max|d|={maxd:.1e}")
except ImportError:
    print("  [SKIP] pandas not available")

print("=== J. value sanity ===")
finite = spectra[~np.isnan(spectra)]
check("J1 all finite values positive", bool((finite > 0).all()),
      f"min={finite.min():.3e} max={finite.max():.4f}")

print()
print("RESULT:", f"FAIL x{len(fails)} -> {fails}" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
