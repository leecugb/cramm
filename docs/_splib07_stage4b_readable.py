# Post-process stage 4: regenerate the five-layer census from the two golden
# npz files with RGB->rule-name decoding (no re-classification needed), and
# carry over the center-layer section computed during the dual run.
import os

import numpy as np

G06 = np.load(r"d:\CRAMM\tests\golden_arrays.npz")
G07 = np.load(r"d:\CRAMM\tests\golden_arrays_v07.npz")
LAYERS = ["orth_rgb", "color_enhanced", "mus_image", "chl_image", "cal_image"]

# mus/chl/cal images are 10-level binned absorption-center thematic maps
# (DEFAULT_MUS_TABLE gradient), not per-rule colors: decode RGB -> bin range.
TABLE = [(255, 30, 0), (255, 115, 0), (255, 191, 0), (251, 255, 25), (207, 255, 110),
         (143, 255, 186), (15, 251, 255), (59, 167, 255), (54, 94, 255), (8, 8, 255)]
BINS = {  # layer -> (bin_lo function): mus 1nm bins 2.195-2.226, chl 1.5nm, cal 5nm
    "mus_image": [(2.195 + k * 0.001, 2.195 + (k + 1) * 0.001) for k in range(10)],
    "chl_image": [(2.244 + k * 0.0015, 2.244 + (k + 1) * 0.0015) for k in range(10)],
    "cal_image": [(2.308 + k * 0.005, 2.308 + (k + 1) * 0.005) for k in range(10)],
}
BINS["mus_image"][0] = (2.195, 2.199)   # table[0] covers [2.195,2.199)
BINS["mus_image"][9] = (2.207, 2.226)   # table[9] covers [2.207,2.226)
for k in range(1, 9):                   # table[1..8] are 1 nm bins from 2.199
    BINS["mus_image"][k] = (2.199 + (k - 1) * 0.001, 2.199 + k * 0.001)


def label(rgb, layer):
    rgb = tuple(int(v) for v in rgb)
    if rgb == (0, 0, 0):
        return "未检出"
    if rgb in TABLE:
        lo, hi = BINS[layer][TABLE.index(rgb)]
        return f"Lv{TABLE.index(rgb)} [{lo:.4f}–{hi:.4f})µm"
    return str(rgb)


L = []
L.append("# splib07 迁移 · 阶段4 全场景双跑差异普查")
L.append("")
L.append("> 日期：2026-08-30（AMX 别名后重建 v07 黄金）｜ 脚本：`docs/_splib07_stage4_dualrun.py`（双跑）+ `docs/_splib07_stage4b_readable.py`（类别解码）")
L.append("> 场景：EMIT_L2A_RFL_001_20220819T061448_2223104_025（1280×1242，1,589,760 像元）")
L.append("> 双轨：legacy=rf.json+splib06b（与 golden_arrays.npz 逐位一致，已验证）；v07=rf_splib07.json+rf07_spectra.npz。")
L.append("> 图层语义：orth_rgb = 硬分类胜出类彩色图（非真彩色场景合成）；color_enhanced = HSI 增强（受 fit/depth 连续量调制，对微小拟合分差异敏感）；"
         "mus/chl/cal_image = 吸收中心 10 级分级专题图（Lv0→Lv9 = 短波→长波）。")
L.append("")
L.append("## 五图层差异普查")
L.append("")
L.append("| 图层 | 相同像元 | 差异像元 | 差异占比 |")
L.append("|---|---|---|---|")
for name in LAYERS:
    a, b = G06[name], G07[name]
    same = np.all(a == b, axis=-1)
    L.append(f"| {name} | {same.sum()} | {(~same).sum()} | {(~same).mean()*100:.3f}% |")
L.append("")
L.append("mus/chl/cal 差异均为亚 1.5% 量级；color_enhanced 差异占比高是连续量调制的预期表现"
         "（fd Δ 中位数仅 0.0001，见文末），不代表分类翻转。")
L.append("")

for name in ["mus_image", "chl_image", "cal_image"]:
    a = G06[name].reshape(-1, 3)
    b = G07[name].reshape(-1, 3)
    changed = (a != b).any(axis=1)
    L.append(f"### {name} 类别迁移（差异 {changed.sum()} 像元）")
    L.append("")
    if changed.any():
        pairs, counts = np.unique(
            np.concatenate([a[changed], b[changed]], axis=1), axis=0, return_counts=True)
        order = np.argsort(-counts)
        L.append("| legacy → v07 | 像元数 |")
        L.append("|---|---|")
        for i in order[:15]:
            L.append(f"| {label(pairs[i, :3], name)} → {label(pairs[i, 3:], name)} | {counts[i]} |")
    L.append("")

# center section computed during the dual run (legacy centers not persisted)
old = open(r"d:\CRAMM\docs\splib07_dualrun_diff.md", encoding="utf-8").read()
sec = old[old.index("## center 连续图层差异"):]
L.append(sec)
L.append("## 归属分析")
L.append("")
L.append("### mus_image（净增 ~15.7k 像元；与 AMX 接入前基本一致）")
L.append("")
L.append("经 orth_rgb 胜出类交叉制表（`_inspect_amxgain.py`）：")
L.append("")
L.append("- **新增 18,787 像元中 18,658 个（99.3%）在 legacy 下的胜出类是方解石（+蒙脱石/白云石混合）规则**")
L.append("  （`calcite.8+montmorilloniteNa.2_mix_intimate` 13,204；`calcite.18+dolomite.22+montmorilloniteNa.6` 4,772；")
L.append("  `calcite` 524 等），v07 下胜出类转为**方解石+白云母混合规则**（`calcite.5+muscoviteMedHiAl.5` 等同色族 16,178）")
L.append("  或纯白云母（2,249）。两族规则在 2.3 µm 区高度相关，这些像元本就位于族间仲裁边缘——")
L.append("  正是方案阶段 4 预言的“仲裁窗口边缘像元归属漂移”，且漂移后仍属含碳酸盐指派。")
L.append("- 流失 3,068 像元的 94.7%（2,907）来自 `clinochlore_Fe.3+muscovite.7` 的边缘像元。")
L.append("- AMX 别名对 mus 图影响极小（增/减与接入前 18,779/3,038 相比仅 +8/+30）：被别名的 ")
L.append("  `kaolinite.5+muscoviteMedhighAl.5`（AMX12）在本场景不是主要胜出类。")
L.append("")
L.append("### cal_image（差异 0.078%→0.297%，AMX 碳酸盐混合接入的直接效应）")
L.append("")
L.append("- 最大单一迁移是 **bin 级平移 1,637 像元（Lv2 [2.318–2.323) → Lv3 [2.323–2.328) µm），")
L.append("  其中 1,630 个 v07 胜出类为 `calcite.5+dolomite.5`**——AMX8 记录的吸收中心比端元合成谱")
L.append("  偏长波约 5 nm，同族同级内平移，不涉及类别翻转。")
L.append("- 类别翻转同样集中于 AMX 碳酸盐混合族：新增 1,086 像元中 688 为 ")
L.append("  `dolomite.5+montmorilloniteNa.5`→`calcite.5+dolomite.5`（AMX21 让位于 AMX8）；")
L.append("  流失 1,591 像元中 436 为 `calcite.5+dolomite.5`→`calcite.18+dolomite.22+montmorilloniteNa.6`、")
L.append("  278 为 `calcite.5+dolomite.5`→`epidote`——均为 AMX8 与端元合成谱的有界差异（r=0.994）")
L.append("  在族间仲裁边缘的重排，全部停留在碳酸盐/绿泥石族内。")
L.append("")
L.append("### 参考谱层面排除异常")
L.append("")
L.append("白云母族四条 NIC4 参考在 2.14–2.24 µm 特征区偏差 ≤±0.0004、新增 NaN 仅 2.508 µm 网格边缘 1 波段；")
L.append("AMX 记录逐条 r 值与 max|Δ| 见 `docs/MCF_vs_rf07_diff.md` 混合谱处理节——漂移由混合族间")
L.append("拟合分微小重排驱动，非参考谱异常。")
L.append("")
L.append("**结论：双轨差异有界、可归因、集中于族间仲裁边缘；mus 1.433%（AMX 接入前后基本持平）、")
L.append("chl 近乎零漂移（94 像元）、cal 0.297%（AMX8/10/21 接入的预期效应，以同族 bin 平移为主）。")
L.append("v07 轨道可接受，遗留轨道继续作为 .mcf 保真基线。**")
L.append("")

with open(r"d:\CRAMM\docs\splib07_dualrun_diff.md", "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print("wrote docs/splib07_dualrun_diff.md")
