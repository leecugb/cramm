# -*- coding: utf-8 -*-
"""核验 USGS MICA 指挥文件(.mcf)与 CRAMM rf.json 的逐字段一致性。

比较维度:
  A 条目集合(OUTPUT_NAME)与顺序
  B 每条规则:诊断特征数 / 特征权重 / 连续统端点 / 8 槽连续统约束 /
    拟合约束 / 深度约束(-99.99 -> null,别名解析为数值)
  C NOT 特征:全局库端点 + 各条目的引用(fit 约束、绝对/相对深度约束)
  D 材料级 WEIGHTED_FIT_DEPTH_CONSTRAINTS
  E 参考光谱指针:解析性 + 拓扑一致性(见下"声明豁免")
  F rf.json 相对 .mcf 的新增字段(absorption_center_range / 深度比约束 / mixture 合成)

声明豁免(Declared deviations, v1.4.0 起,经裁决):
  1. 参考谱指针字段:rf.json 的 reference.reflectance_record 与
     not_*_features.reflectance_record 为 rule-name 字符串指针(v1.4.0 起,
     77 条参考指针 + 12 个 NOT 指针),不再是 .mcf 的 SPECPR 记录号。
     本脚本核验其解析性(指针必须指向 rf 内规则)与拓扑(参考指针 = 自指,
     谱随 1nm bundle 按 rule-name 烘焙);样品身份证据链见
     docs/splib07_selection.json(splib06b 记录号 -> 规则)、
     docs/rf77_corr_06b_vs_07.csv(06b vs 07 相关)、
     docs/rfjson_splib07_verification.md(50/51 r>=0.99 裁决)。
  2. NOT 特征键改名:37 个 NOT 特征库键由旧名改为 rule-name(计数、顺序、
     端点与约束逐比特保留)。本脚本 C 节按端点集合 + 约束匹配,天然不受
     改名影响;指针解析性在 E 节核验。
  3. wavelength_map / mixtures 顶层表已按设计删除(v1.3.x/v1.4.0):
     1nm 轨道使用合成恒等波长映射,混合谱在打包时烘焙入 bundle。

用法: python docs/verify_mcf_rfjson.py [mcf_path] [rfjson_path]
"""
import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MCF_CANDIDATES = [
    Path.home() / "Downloads/mcf/mica_cmds_group2_hymap2_2014_v6a_FOR_RELEASE.mcf",
    Path("/media/lee/共享14/backup/mcf/mica_cmds_group2_hymap2_2014_v6a_FOR_RELEASE.mcf"),
]
MCF = (Path(sys.argv[1]) if len(sys.argv) > 1
       else next((p for p in _MCF_CANDIDATES if p.exists()), _MCF_CANDIDATES[0]))
RFJ = Path(sys.argv[2]) if len(sys.argv) > 2 else _REPO / "cramm/data/rf.json"
NULL = -99.99
TOL = 5e-4  # .mcf 4 位小数 vs rf.json 有效数字

CC_KEYS = ["left_min", "left_max", "mean_min", "mean_max",
           "right_min", "right_max", "ratio_min", "ratio_max"]


def parse_mcf(path: Path):
    txt = path.read_text(encoding="utf-8", errors="replace")

    # ---- 别名 ----
    aliases = {}
    for m in re.finditer(r"ALIAS:\s*\[([^\]]+)\]\s+(\S+)", txt):
        aliases[m.group(1)] = m.group(2)

    def val(tok):
        tok = tok.strip()
        m = re.fullmatch(r"\[([^\]]+)\]", tok)
        if m:
            tok = aliases[m.group(1)]
        return float(tok)

    # ---- 全局 NOT 特征库 ----
    not_lib = {}
    for m in re.finditer(
        r'Not material title = "([^"]+)"[^\n]*\nNOT_FEATURE_ID:\s*(\d+)\s*\n'
        r"NOT_FEATURE_SPECPR_RECORD:\S+\s+(\d+)\s*\nCONTINUUM_ENDPTS:([0-9. ]+)", txt):
        not_lib[int(m.group(2))] = {
            "title": m.group(1), "record": int(m.group(3)),
            "endpoints": [float(x) for x in m.group(4).split()],
        }

    # ---- 参考条目 ----
    entries = {}
    blocks = re.split(r";\.{10,}Material SPECPR Title = ", txt)[1:]
    for b in blocks:
        title = b.split('"')[1]
        # 去掉注释行(.mcf 中以 ; 注释整行,如被禁用的 NOT_FEATURE_ID: 15 块)
        b = "\n".join(ln for ln in b.splitlines() if not ln.lstrip().startswith(";"))
        name = re.search(r"OUTPUT_NAME:\s*(\S+)", b).group(1)
        rec = int(re.search(r"REFERENCE_SPECPR_RECORD:\S+\s+(\d+)", b).group(1))
        ndiag, nnot = map(int, re.search(r"NUM_FEATURES:\s*(\d+)\s+(\d+)", b).groups())

        feats, nots = [], []
        for fm in re.finditer(
            r"FEATURE_TYPE:\s*(Diagnostic|Not)(.*?)(?=FEATURE_TYPE:|WEIGHTED_FIT_DEPTH_CONSTRAINTS:)",
            b, re.S):
            kind, body = fm.group(1), fm.group(2)
            if kind == "Diagnostic":
                cc = [None if abs(v - NULL) < 1e-9 else v
                      for v in map(val, re.search(r"CONTINUUM_CONSTRAINTS:([^\n]+)", body).group(1).split())]
                fit_toks = re.search(r"FIT_CONSTRAINTS:([^\n]+)", body).group(1).split()
                dep_toks = re.search(r"DEPTH_CONSTRAINTS:([^\n]+)", body).group(1).split()
                feats.append({
                    "weight": val(re.search(r"FEATURE_WEIGHT:\s*(\S+)", body).group(1)),
                    "endpoints": [float(x) for x in re.search(r"CONTINUUM_ENDPTS:([^\n]+)", body).group(1).split()],
                    "cc": cc,
                    "fit": None if abs(val(fit_toks[0]) - NULL) < 1e-9 else val(fit_toks[0]),
                    "depth": [None if abs(val(t) - NULL) < 1e-9 else val(t) for t in dep_toks],
                })
            else:
                d = {"id": int(re.search(r"NOT_FEATURE_ID:\s*(\d+)", body).group(1)),
                     "fit": val(re.search(r"NOT_FEATURE_FIT_CONSTRAINTS:\s*(\S+)", body).group(1))}
                mabs = re.search(r"NOT_FEATURE_ABSOLUTE_DEPTH_CONSTRAINTS:\s*(\S+)", body)
                mrel = re.search(r"NOT_FEATURE_RELATIVE_DEPTH_CONSTRAINTS:\s*(\d+)\s+(\S+)", body)
                if mabs:
                    d["abs_depth"] = val(mabs.group(1))
                if mrel:
                    d["rel_depth"] = (int(mrel.group(1)), val(mrel.group(2)))
                nots.append(d)

        wfd = [None if abs(v - NULL) < 1e-9 else v
               for v in map(val, re.search(r"WEIGHTED_FIT_DEPTH_CONSTRAINTS:([^\n]+)", b).group(1).split())]
        entries[name] = {"title": title, "record": rec, "n_diag": ndiag, "n_not": nnot,
                         "feats": feats, "nots": nots, "wfd": wfd}
    return entries, not_lib


def close(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= TOL


def main():
    if not MCF.exists():
        sys.exit(f"找不到 .mcf 指挥文件: {MCF}\n"
                 f"用法: python docs/verify_mcf_rfjson.py <mcf_path> [rfjson_path]")
    mcf, not_lib = parse_mcf(MCF)
    rf = json.loads(RFJ.read_text(encoding="utf-8"))
    rules = rf["rf"]  # v1.4.0 起顶层仅 'rf' 一个键

    problems, notes = [], []
    n_feat_cmp = n_cc_cmp = n_not_cmp = 0

    # A. 条目集合
    only_mcf = sorted(set(mcf) - set(rules))
    only_rf = sorted(set(rules) - set(mcf))
    if only_mcf or only_rf:
        problems.append(f"条目集合不一致: only_mcf={only_mcf} only_rf={only_rf}")

    for name in sorted(set(mcf) & set(rules)):
        e, r = mcf[name], rules[name]
        tag = f"[{name}]"

        # B. 诊断特征
        if e["n_diag"] != len(r["diagnostic_features"]) or len(e["feats"]) != len(r["diagnostic_features"]):
            problems.append(f"{tag} 诊断特征数: mcf={e['n_diag']} rf={len(r['diagnostic_features'])}")
            continue
        wsum = 0.0
        for i, (mf, rf_) in enumerate(zip(e["feats"], r["diagnostic_features"])):
            n_feat_cmp += 1
            wsum += mf["weight"]
            if not close(mf["weight"], rf_["feature_weight"]):
                problems.append(f"{tag} feat{i+1} 权重: mcf={mf['weight']} rf={rf_['feature_weight']}")
            if [round(x, 4) for x in mf["endpoints"]] != [round(x, 4) for x in rf_["continuum_endpoints"]]:
                problems.append(f"{tag} feat{i+1} 端点: mcf={mf['endpoints']} rf={rf_['continuum_endpoints']}")
            for k, v in zip(CC_KEYS, mf["cc"]):
                n_cc_cmp += 1
                if not close(v, rf_["continuum_constraints"][k]):
                    problems.append(f"{tag} feat{i+1} 连续统约束 {k}: mcf={v} rf={rf_['continuum_constraints'][k]}")
            if not close(mf["fit"], rf_["fit_constraint"]):
                problems.append(f"{tag} feat{i+1} fit 约束: mcf={mf['fit']} rf={rf_['fit_constraint']}")
            if len(mf["depth"]) != 2 or not all(close(a, b) for a, b in zip(mf["depth"], rf_["depth_constraints"])):
                problems.append(f"{tag} feat{i+1} depth 约束: mcf={mf['depth']} rf={rf_['depth_constraints']}")
        if abs(wsum - 1.0) > 1e-3:
            notes.append(f"{tag} 特征权重和={wsum:.4f}(!=1)")

        # C. NOT 特征(按端点集合匹配:rf.json 将 relative 类存入独立列表,顺序与 .mcf 不同)
        rf_nots = r["not_absolute_features"] + r["not_relative_features"]
        if len(e["nots"]) != len(rf_nots):
            problems.append(f"{tag} NOT 特征数: mcf={len(e['nots'])} rf={len(rf_nots)}")
        for j, mn in enumerate(e["nots"]):
            n_not_cmp += 1
            lib = not_lib[mn["id"]]
            ep4 = [round(x, 4) for x in lib["endpoints"]]
            cand = [rn for rn in rf_nots
                    if [round(x, 4) for x in rn["continuum_endpoints"]] == ep4]
            if len(cand) == 0:
                problems.append(f"{tag} not#{j+1}: mcf id={mn['id']} 端点 {ep4} 在 rf.json 中无对应")
                continue
            # 端点相同可能有多条(如干草/松针共用区间),取约束也匹配的一条
            def not_match(rn):
                if not close(mn["fit"], rn["fit_constraint"]):
                    return False
                if "abs_depth" in mn and not close(mn["abs_depth"], rn.get("absolute_depth_constraint")):
                    return False
                if "rel_depth" in mn:
                    fid, v = mn["rel_depth"]
                    if not close(v, rn.get("relative_depth_threshold")):
                        return False
                return True
            if not any(not_match(rn) for rn in cand):
                got = [(rn["fit_constraint"], rn.get("absolute_depth_constraint"),
                        rn.get("relative_depth_threshold")) for rn in cand]
                problems.append(f"{tag} not#{j+1} (id={mn['id']}) 约束不符: mcf fit={mn['fit']} "
                                f"abs={mn.get('abs_depth')} rel={mn.get('rel_depth')} rf={got}")

        # D. 材料级约束
        wc = r["weighted_constraints"]
        for k, v in zip(["min_weighted_fit", "min_weighted_depth", "max_weighted_depth",
                         "min_fit_depth_product"], e["wfd"]):
            if not close(v, wc[k]):
                problems.append(f"{tag} weighted {k}: mcf={v} rf={wc[k]}")

        # E. 参考谱指针(声明豁免 1/2:rule-name 指针取代 .mcf 记录号)
        # 核验解析性与拓扑,样品身份证据链见文件头豁免说明。
        ref_rec = r["reference"]["reflectance_record"]
        if not isinstance(ref_rec, str) or ref_rec not in rules:
            problems.append(f"{tag} reference 指针无法解析: {ref_rec!r}")
        elif ref_rec != name:
            problems.append(f"{tag} reference 指针非自指: {ref_rec!r} "
                            f"(v1.4.0 口径下每条规则的谱以自身 rule-name 烘焙入 bundle)")
        for nf in rf_nots:
            nrec = nf.get("reflectance_record")
            if not isinstance(nrec, str) or nrec not in rules:
                problems.append(f"{tag} NOT 指针无法解析: {nrec!r}")

        # F. CRAMM 新增字段
        acr = [f.get("absorption_center_range") for f in r["diagnostic_features"] if f.get("absorption_center_range")]
        if acr or r.get("max_depth_ratio_feat1_over_feat0") is not None:
            notes.append(f"{tag} CRAMM 新增: acr={acr} depth_ratio={r.get('max_depth_ratio_feat1_over_feat0')}")

    print(f"MCF: {MCF}")
    print(f"RFJ: {RFJ}")
    print(f"MCF 条目: {len(mcf)}  rf.json 规则: {len(rules)}")
    print(f"比对: 诊断特征 {n_feat_cmp} 个, 连续统约束槽 {n_cc_cmp} 个, NOT 引用 {n_not_cmp} 处")
    print(f"全局 NOT 库: {len(not_lib)} 个")
    print()
    print(f"== 不一致项: {len(problems)} ==")
    for p in problems:
        print(" *", p)
    print()
    print(f"== 备注(设计性差异/新增): {len(notes)} ==")
    for n_ in notes:
        print(" -", n_)
    print()
    print("RESULT:", "PASS" if not problems else "FAIL")
    sys.exit(0 if not problems else 1)


if __name__ == "__main__":
    main()
