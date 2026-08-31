# Stage 1 of splib07 migration: reference selection table + per-rule
# diagnostic-feature coverage validation. No behavior change.
# Outputs: docs/splib07_selection.json + docs/splib07_selection.md
import json
import os
import sys
from collections import OrderedDict

import netCDF4 as nc
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from cramm.classifier import MicaClassifier, _resample_
from usgs_splib import USGSLibrary
from _splib07_tokens import TOKENS

GRID_LO, GRID_HI, GRID_STEP = 0.35, 2.50, 0.001  # master grid (um)
MASTER_GRID = np.arange(GRID_LO, GRID_HI + 1e-9, GRID_STEP)

# Coverage is judged on the real EMIT band grid through the engine's own
# resample kernel (_resample_), i.e. exactly what the classifier will see.
EMIT_NC = r"d:\CRAMM\EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
with nc.Dataset(EMIT_NC) as _ds:
    EMIT_W = _ds["sensor_band_parameters"]["wavelengths"][:].data / 1000.0
    EMIT_BP = _ds["sensor_band_parameters"]["fwhm"][:].data / 1000.0

d = json.load(open(r"d:\CRAMM\cramm\data\rf.json"))
rules = d["rf"]
mixdefs = d["mixtures"]
c = MicaClassifier.from_paths()
dic = c.dic3.set_index("irecno")
lib = USGSLibrary(r"D:\usgs_splib07")

QUALITY_RANK = {q: i for i, q in enumerate(
    ["c", "b", "bb", "bbb", "bc", "a", "aa", "aaa", "cdb", "bbu", "u"], 0)}
# higher quality letter-count first when comparing (aaa > aa > a > bbb > bb > b)
def qrank(q):
    q = q.strip("_")
    score = {"a": 3, "aa": 4, "aaa": 5, "b": 1, "bb": 2, "bbb": 2.5,
             "bc": 1.5, "c": 0.5, "u": 0}.get(q, 0)
    return score


def load06(rec):
    row = dic.loc[rec]
    wl = np.asarray(dic.loc[int(row["irwav"]), "data"], dtype=float)
    sp = np.asarray(row["data"], dtype=float)
    o = np.argsort(wl)
    wl, sp = wl[o], sp[o]
    k = (wl > 0) & (sp > 0) & (sp <= 1.5)
    return wl[k], sp[k]


def compare06(wl06, sp06, spec07):
    wl2 = np.asarray(spec07.wavelength, float)
    sp2 = np.asarray(spec07.reflectance, float)
    o = np.argsort(wl2)
    wl2, sp2 = wl2[o], sp2[o]
    k = (wl2 > 0) & (sp2 > 0) & (sp2 <= 1.5)
    wl2, sp2 = wl2[k], sp2[k]
    lo = max(wl06.min(), wl2.min(), GRID_LO)
    hi = min(wl06.max(), wl2.max(), GRID_HI)
    if hi - lo < 0.3 or len(wl2) < 100:
        return None
    g = np.linspace(lo, hi, 2000)
    a = np.interp(g, wl06, sp06)
    b = np.interp(g, wl2, sp2)
    return float(np.corrcoef(a, b)[0, 1])


def resample06(rec):
    """06b record through the engine path exactly as get_resample() does:
    raw dic3 wavelength/data arrays (padding zeros and deleted-band zeros
    kept), straight into _resample_. NaN in the output = FWHM window with no
    positive sample."""
    row = dic.loc[rec]
    wl = np.asarray(dic.loc[int(row["irwav"]), "data"], dtype="float64")
    sp = np.asarray(row["data"], dtype="float64")
    return _resample_(wl, sp, EMIT_W, EMIT_BP)


def bake07(spec07):
    """Bake a splib07 record onto the 1 nm master grid (the form the v07 track
    will actually ship in rf07_spectra.npz): piecewise-linear interpolation of
    the valid samples; NaN outside the valid sample range; interior gaps
    (deleted water bands) bridged linearly -- on the baked grid every EMIT
    FWHM window inside the range then contains valid samples, so the Beckman
    10 nm 'hole' artifact of raw-grid resampling disappears by construction."""
    wl = np.asarray(spec07.wavelength, dtype="float64")
    sp = np.asarray(spec07.reflectance, dtype="float64")
    o = np.argsort(wl)
    wl, sp = wl[o], sp[o]
    k = (wl > 0) & (sp > 0) & (sp < 1e34)
    wl, sp = wl[k], sp[k]
    out = np.full(len(MASTER_GRID), np.nan)
    m = (MASTER_GRID >= wl.min()) & (MASTER_GRID <= wl.max())
    out[m] = np.interp(MASTER_GRID[m], wl, sp)
    return out


def resample07(spec07):
    """Baked splib07 record through the engine kernel (NaN entries are dropped
    by the kernel's temp > 0 filter, same as zeros)."""
    return _resample_(MASTER_GRID, bake07(spec07), EMIT_W, EMIT_BP)


# Manual record overrides: keyed by splib06b rec, forces a specific splib07
# record key regardless of the D1-A scoring (rationale in adjudications).
RECORD_OVERRIDE = {
    # 06b rec 4625 (Illite GDS4, R1Bb/BECKb): D1-A same-instrument policy picks
    # the BECKb record, but USGS deleted the 1.35-1.42 um water band from it in
    # splib07 (06b has 100 valid samples there; BECKb keeps only 5, so the npz
    # bake bridges the band linearly). The same-sample ASDNGb re-measurement
    # has real 1.4 um OH-band data (101 samples) and an integer-nm grid
    # (identity bake). 2026-08-31 adjudication: accept lower full-range r
    # (0.9973 -> 0.9708) in exchange for real 1.4 um data; the rule feature
    # windows at 2.2/2.35 um are essentially identical across both records,
    # so classification impact is confined to the reference-spectrum level.
    4625: "Illite_GDS4_Marblehead_ASDNGb_AREF",
}


def want_instrument(title06):
    if "R1B" in title06:
        return [("BECK", "AREF")]
    if "R4N" in title06:
        return [("NIC4", "RREF")]
    if "R1F" in title06:
        return [("ASDFR", "AREF"), ("ASDNG", "AREF")]
    return []


def feature_span(rule):
    """union of all diagnostic-feature windows + absorption_center_range"""
    lo, hi = np.inf, -np.inf
    for f in rule["diagnostic_features"]:
        ep = f["continuum_endpoints"]
        lo = min(lo, ep[0])
        hi = max(hi, ep[3])
        acr = f.get("absorption_center_range")
        if acr:
            lo = min(lo, acr[0])
            hi = max(hi, acr[1])
    return lo, hi


def coverage(res07, res06, span):
    """Engine-faithful criterion: after resampling both records onto the real
    EMIT (w, bp) grid with the engine's own kernel (_resample_ drops zero /
    -1.23e34 deleted samples and yields NaN where a FWHM window has no valid
    sample), the splib07 record must be non-NaN at every EMIT band inside the
    rule's feature span where the 06b record is non-NaN. Holes inherited from
    06b (Beckman 10 nm sampling, deleted water bands) are heritage and stay
    acceptable; only NEW holes introduced by the splib07 record fail."""
    lo, hi = span
    inspan = (EMIT_W >= lo) & (EMIT_W <= hi)
    ok06 = ~np.isnan(res06)
    ok07 = ~np.isnan(res07)
    missing = EMIT_W[inspan & ok06 & ~ok07]
    gained = EMIT_W[inspan & ~ok06 & ok07]
    return missing, gained, int((inspan & ok06).sum()), int(inspan.sum())


# ---------------------------------------------------------------- selection
# unique physical reference -> rules using it
rec_rules = OrderedDict()   # rec -> [rules]
synth_rules = []            # linear-computed mixes (17)
for name, rule in rules.items():
    rec = rule["reference"]["reflectance_record"]
    if str(rec).startswith("mix_"):
        comp = mixdefs[str(rec)]
        if len(comp) == 1 and list(comp.values())[0] == 1.0:
            rec = int(list(comp.keys())[0])
            rec_rules.setdefault(rec, []).append(name)
        else:
            synth_rules.append(name)
    else:
        rec_rules.setdefault(int(rec), []).append(name)

selection = OrderedDict()
problems = []
for rec, users in rec_rules.items():
    title06 = dic.loc[rec, "ititl"].strip()
    token = TOKENS[users[0]]
    want = want_instrument(title06)
    wl06, sp06 = load06(rec)
    cands = lib.search(name=token)
    scored = []
    for r in cands:
        inst = 0 if (r.sensor, r.mtype) in want else 1
        rr = compare06(wl06, sp06, lib.load(r))
        scored.append((inst, -qrank(r.quality), -(rr or 0), r, rr))
    scored.sort(key=lambda t: (t[0], t[1], t[2], t[3].name))
    if rec in RECORD_OVERRIDE:
        okey = RECORD_OVERRIDE[rec]
        pick = [t for t in scored
                if f"{t[3].name}_{t[3].sensor}{t[3].quality}_{t[3].mtype}" == okey]
        if not pick:
            raise SystemExit(f"override target not among candidates for rec {rec}: {okey}")
        inst, _, _, best, r_val = pick[0]
    else:
        inst, _, _, best, r_val = scored[0]
    res06 = resample06(rec)
    res07 = resample07(lib.load(best))
    cov = {}
    for u in users:
        span = feature_span(rules[u])
        missing, gained, n_ok06, n_span = coverage(res07, res06, span)
        ok = len(missing) == 0
        cov[u] = {"span": [round(span[0], 4), round(span[1], 4)],
                  "covered": bool(ok),
                  "emit_bands_in_span": n_span,
                  "emit_bands_06b_valid": n_ok06,
                  "emit_bands_gained": int(len(gained))}
        if not ok:
            cov[u]["missing_bands_um"] = [round(float(m), 4) for m in missing[:20]]
            problems.append((u, best.name, span, missing))
    key = f"{best.name}_{best.sensor}{best.quality}_{best.mtype}"
    selection[str(rec)] = {
        "rules": users,
        "splib06b_title": title06,
        "splib07_record": key,
        "splib07_name": best.name,
        "sensor": best.sensor, "quality": best.quality, "mtype": best.mtype,
        "instrument_match": inst == 0,
        "record_override": rec in RECORD_OVERRIDE,
        "r_vs_06b": round(r_val, 4) if r_val else None,
        "coverage": cov,
    }

# synthetic mixes: 5 have a recipe-exact calculated areal mixture in splib07
# (AMX series) and are aliased to it; the other 12 stay engine-synthesized.
AMX_MAP = OrderedDict([  # mix_id -> (splib07 record key, synthetic rec id)
    ("mix_7821", ("Calcite.5+Dolomite.5_AMX8_ASDNGb_AREF", 90008)),
    ("mix_7715", ("Dolomite.5+Ca-Mont.5_AMX10_ASDNGb_AREF", 90010)),
    ("mix_7711", ("Dolomite.5+Na-Mont.5_AMX21_ASDNGb_AREF", 90021)),
    ("mix_7745", ("Kaol_Wxl+0.5Musc_Ruby_AMX12_ASDNGa_AREF", 90012)),
    ("mix_7737", ("Pyrophyl.25+wxlKaol.75_AMX17_ASDNGb_AREF", 90017)),
])
# instrument policy: among same-quality AMX variants prefer ASDNG -- integer-nm
# grid makes the master-grid bake an identity copy (BECK 10 nm would not be).
by_key = {f"{r.name}_{r.sensor}{r.quality}_{r.mtype}": r for r in lib.records}
amx_report = []
for mix_id, (key, synth_rec) in AMX_MAP.items():
    name = [n for n, rule in rules.items()
            if str(rule["reference"]["reflectance_record"]) == mix_id][0]
    comp = mixdefs[mix_id]
    r_amx = resample07(lib.load(by_key[key]))
    synth07 = np.zeros_like(EMIT_W)
    synth06 = np.zeros_like(EMIT_W)
    for cid, w in comp.items():
        s07 = selection[cid]["splib07_record"]
        synth07 = synth07 + resample07(lib.load(by_key[s07])) * w
        synth06 = synth06 + resample06(int(cid)) * w
    both = ~np.isnan(r_amx) & ~np.isnan(synth07)
    both6 = ~np.isnan(r_amx) & ~np.isnan(synth06)
    amx_report.append({
        "mix_id": mix_id,
        "rule": name,
        "recipe": comp,
        "amx_record": key,
        "amx_name": by_key[key].name,
        "synthetic_rec": synth_rec,
        "sensor": by_key[key].sensor,
        "quality": by_key[key].quality,
        "mtype": by_key[key].mtype,
        "r_vs_synth_v07": round(float(np.corrcoef(r_amx[both], synth07[both])[0, 1]), 4),
        "maxdiff_vs_synth_v07": round(float(np.abs(r_amx[both] - synth07[both]).max()), 4),
        "r_vs_synth_06b": round(float(np.corrcoef(r_amx[both6], synth06[both6])[0, 1]), 4),
        "new_nan_bands_vs_synth": int((~np.isnan(synth07) & np.isnan(r_amx)).sum()),
    })

synth_report = []
for name in synth_rules:
    rec = str(rules[name]["reference"]["reflectance_record"])
    if rec in AMX_MAP:
        continue  # aliased to an AMX physical record, not synthesized
    comp = mixdefs[rec]
    ems = {e: selection.get(e, {}).get("splib07_record") for e in comp}
    synth_report.append({"rule": name, "mix_id": rec,
                         "endmembers": ems,
                         "all_selected": all(v for v in ems.values())})

out = {
    "master_grid": {"lo_um": GRID_LO, "hi_um": GRID_HI, "step_um": GRID_STEP},
    "strategy": ("D1-A same instrument+type; best quality then best r within group; "
                 "coverage = engine _resample_ on real EMIT grid, no new NaN bands "
                 "vs 06b inside feature span"),
    "references": selection,
    "amx_mixture_aliases": amx_report,
    "synthetic_mixes": synth_report,
    "adjudications": [
        {"rule": "illite_gds4",
         "issue": "D1-A 同仪器策略选中的 Illite_GDS4_Marblehead_BECKb_AREF 在 splib07 "
                  "中被 USGS 删除了 1.35–1.42 µm 水汽吸收带（06b 该区间有 100 个有效采样，"
                  "BECKb 仅剩 5 个，npz 烘焙只能线性桥接）；同样品的 "
                  "Illite_GDS4_Marblehead_ASDNGb_AREF 重测记录在该区间有 101 个真实采样，"
                  "且为整数 nm 网格（主网格烘焙恒等）。代价：全段 r 0.9973→0.9708，"
                  "整体反射率水平略偏高；规则实际使用的 2.2/2.35 µm 特征窗内两记录"
                  "与 06b 几乎重合，分类行为影响可忽略（1.4 µm 不在任何规则特征窗内）",
         "decision": "覆盖裁决（RECORD_OVERRIDE）：选用 ASDNGb 全覆盖记录，"
                     "接受同仪器策略偏离，换取 1.4 µm OH 带真实数据"},
        {"rule": "dry_veg_nongrass(+_2_3um)",
         "issue": "USGS 在 splib07 重排了 LP-Needles 系列编号：与 06b 'LP-Needles-3'"
                  "（rec 12794，干针叶）谱形一致的是 splib07 LP-Needles-2（r=0.999995）；"
                  "splib07 自有的 LP-Needles-3 是新测的健康绿叶谱（r=0.884，"
                  "红边+液态水吸收），并非对应记录——v1.2.0/v1.2.1 曾按名称精确匹配"
                  "误选后者并裁决'仅存重测记录'，该裁决依据错误",
         "decision": "映射更正为 LP-Needles-2_ASDFRa_AREF（同样品族、同仪器 ASDFRa AREF）"},
        {"rule": "5 条 AMX 直接映射混合规则",
         "issue": "AMX 计算混合谱与按 .mcf 配方从新端元合成的谱存在有界差异"
                  "（AMX 由 USGS 用其自择端元记录预先计算，r=0.918–0.994），"
                  "但样品与配比和 .mcf 配方一致",
         "decision": "采纳 AMX 实物记录，以权重 1.0 别名接入（合成 rec id 90008+）"},
        {"rule": "mix_7703 / mix_7741 / mix_7707",
         "issue": "AMX3/AMX13 的高岭石端元为 KGa-1（.mcf 用 KGa-2=rec 5167）、"
                  "AMX14 的矾石端元为 HS295（.mcf 用 GDS96=rec 596）——端元样品不一致",
         "decision": "拒绝映射，维持按 .mcf 配方端元合成"},
    ],
}
with open(r"d:\CRAMM\docs\splib07_selection.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- markdown
L = []
L.append("# splib07 迁移 · 阶段1 选谱表与特征覆盖校验")
L.append("")
L.append("> 日期：2026-08-31（dry_veg_nongrass 映射更正：LP-Needles-3→LP-Needles-2；"
         "illite_gds4 覆盖裁决：BECKb→ASDNGb，恢复 1.4 µm 真实数据）｜ 脚本：`docs/_splib07_stage1_selection.py` ｜ 数据：`docs/splib07_selection.json`")
L.append("> 策略 D1-A：同仪器+同测量类型优先，组内质量最高、r 最高者胜出。")
L.append("> 覆盖判据（引擎口径）：splib07 记录先按 D2 增补烘焙到 1 nm 主网格"
         "（分段线性插值、量程外 NaN、内部删除带线性桥接——烘焙后 Beckman 10 nm 采样的"
         "FWHM 窗空洞按构造消失），再与 06b 原始谱一同经引擎 `_resample_` 重采样到真实 "
         "EMIT 波段网格；规则特征区间内，splib07 在 06b 非 NaN 的每个 EMIT 波段必须同样"
         "非 NaN——继承自 06b 的空洞（删水带等）视为遗产，仅新增空洞判失败。")
L.append("")
L.append("| splib06b rec | 使用规则 | splib06b 标题 | 选定 splib07 记录 | r | 覆盖 |")
L.append("|---|---|---|---|---|---|")
n_ok = 0
for rec, s in selection.items():
    cov_all = all(v["covered"] for v in s["coverage"].values())
    if cov_all and (s["instrument_match"] or s["record_override"]):
        n_ok += 1
    flag = "✓" if cov_all else "**✗**"
    L.append(f"| {rec} | {', '.join(s['rules'])} | {s['splib06b_title']} | "
             f"`{s['splib07_record']}` | {s['r_vs_06b']} | {flag} |")
L.append("")
L.append(f"唯一实物参考谱 {len(selection)} 条（51 条规则直接引用 + 2 条仅经权重 1.0 混合别名的 GDS212/213）；"
         f"仪器匹配（或裁决覆盖）且特征全覆盖 {n_ok} 条。规则面口径：77 条规则消费 70 条唯一重采样参考"
         f"（51 直接 + 19 混合，7 条为复用——6 组共享）。另有 5 条 AMX 计算混合记录见下节，"
         f"npz 实物记录合计 58 条。")
L.append("")
L.append("## AMX 直接映射混合谱（5 条）")
L.append("")
L.append("splib07 AMX 系列为 USGS 预先计算的面积（线性）混合谱。以下 5 条与 .mcf 配方的"
         "**样品和配比一致**，按 D2 同口径烘焙进 npz（合成 rec id 90000+AMX 编号），"
         "规则文件中以权重 1.0 别名引用（同 GDS212/213 先例），不再由引擎端元合成。")
L.append("仪器策略：同质量优先 ASDNG——整数 nm 网格使主网格烘焙为恒等拷贝。")
L.append("")
L.append("| mix_id | 规则 | 配方 | AMX 记录 | r(v07 合成) | max\\|Δ\\| | r(06b 合成) | 新增 NaN |")
L.append("|---|---|---|---|---|---|---|---|")
for a in amx_report:
    comp = ", ".join(f"{k}:{v}" for k, v in a["recipe"].items())
    L.append(f"| {a['mix_id']} | {a['rule']} | {comp} | `{a['amx_record']}` | "
             f"{a['r_vs_synth_v07']} | {a['maxdiff_vs_synth_v07']} | "
             f"{a['r_vs_synth_06b']} | {a['new_nan_bands_vs_synth']} |")
L.append("")
L.append("r<1 的原因：AMX 由 USGS 用其自择端元记录预先计算，并非本选谱表端元的数值加权和"
         "（对 06b 端元合成同样 r≈0.92–0.99，差异不来自 06b→07 重测）。差异有界且记录在此。")
L.append("")
L.append("**拒绝的 3 条 AMX 映射**（端元样品与 .mcf 配方不一致，维持端元合成）："
         "AMX3/AMX13 用 KGa-1 ≠ 5167(KGa-2)（mix_7703/mix_7741）；"
         "AMX14 用 HS295 ≠ 596(GDS96)（mix_7707）。")
L.append("")
L.append("## 覆盖失败明细" if problems else "## 覆盖失败：无")
for u, nm, span, missing in problems:
    L.append(f"- {u}: `{nm}` 特征区间 {span[0]:.3f}–{span[1]:.3f} µm 内 splib07 新增 "
             f"{len(missing)} 个 NaN 波段（06b 有值）："
             + ", ".join(f"{m:.4f}" for m in missing[:12]) + (" …" if len(missing) > 12 else ""))
L.append("")
L.append("## 合成混合端元检查（12 条线性合成规则；另 5 条已别名至 AMX 实物记录）")
L.append("")
n_syn = sum(1 for s in synth_report if s["all_selected"])
L.append(f"全部端元均已选定 splib07 记录的规则：{n_syn}/{len(synth_report)}")
for s in synth_report:
    if not s["all_selected"]:
        L.append(f"- ⚠ {s['rule']}: {s['endmembers']}")
L.append("")
L.append("## 逐条裁决")
L.append("")
for a in out["adjudications"]:
    L.append(f"- **{a['rule']}**：{a['issue']} → {a['decision']}")

with open(r"d:\CRAMM\docs\splib07_selection.md", "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print(f"unique refs: {len(selection)}, coverage-instrument OK: {n_ok}")
print(f"coverage problems: {len(problems)}")
for u, nm, span, missing in problems:
    print(f"   {u}: {nm} span={span[0]:.3f}-{span[1]:.3f} new-NaN={len(missing)}")
print(f"synthetic mixes fully covered: {n_syn}/{len(synth_report)}")
print(f"AMX aliases: {len(amx_report)} "
      f"(min r vs synth07 = {min(a['r_vs_synth_v07'] for a in amx_report)})")
