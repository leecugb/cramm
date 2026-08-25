# -*- coding: utf-8 -*-
"""参考光谱数据级核验:rf.json 参考谱 vs .mcf 配套卷积库。

与 verify_mcf_rfjson.py(规则参数字段级)互补,本脚本比较**光谱本身**:

  1. 解析 .mcf,取每条规则的 REFERENCE_SPECPR_RECORD(指向卷积库
     splib06b_cv_hymap2_2014_126ch 的记录号)与 SPECPR 标题;
  2. 用 CRAMM 自己的高斯卷积(_resample_,与生产分类同一代码路径)把
     rf.json 引用的 splib06b 原始谱(混合物按 mixtures 权重线性合成)
     重采样到 HyMap2 126 通道(波长/FWHM 取自卷积库自带的记录 5/6);
  3. 逐规则比对:相关度、RMSE、最大绝对差,并对卷积库记录标题做
     身份核对。

预期分组(设计使然):
  - 58 条纯谱一致规则:光谱应高度一致(卷积实现差异量级);
  - 6 条已声明偏差(chlorite_lowFe / illite_imt1 / pyrophyllite.5+
    alunite.5 / serpentine_antigorite x3):同一样品不同测量记录,
    允许更大差异;
  - 13 条混合物规则:.mcf 用实物混合谱,CRAMM 用端元线性合成,
    差异为设计性(verify_mcf_rfjson.py 维度 F 已声明)。

用法:
  python docs/verify_reference_spectra.py [mcf路径] [卷积库路径] [报告输出路径]
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cramm.classifier import MicaClassifier, _hyper_read_specpr  # noqa: E402
from docs.verify_mcf_rfjson import parse_mcf  # noqa: E402

MCF = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"D:\mcf\mica_cmds_group2_hymap2_2014_v6a_FOR_RELEASE.mcf")
CV = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
    r"D:\mcf\splib06b_cv_hymap2_2014_126ch")
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else None

DECLARED_DEVIATIONS = {
    "chlorite_lowFe", "illite_imt1", "pyrophyllite.5+alunite.5_mix_intimate",
    "serpentine_antigorite_or_calcite+dolomite",
    "serpentine_antigorite_withironfeat",
    "serpentine_antigorite_withsecondfeat",
}


def norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", str(t)).strip().lower()


def main() -> None:
    mcf, _ = parse_mcf(MCF)
    rfj = json.loads(Path("cramm/data/rf.json").read_text(encoding="utf-8"))
    rules, mixtures = rfj["rf"], rfj["mixtures"]

    clf = MicaClassifier.from_paths()  # bundled rf.json + splib06b
    cv = _hyper_read_specpr(str(CV))
    hymap_wl = np.asarray(cv.loc[5]["data"], float)[:126]
    hymap_fwhm = np.asarray(cv.loc[6]["data"], float)[:126]
    assert (hymap_wl > 0).all() and (hymap_fwhm > 0).all(), "HyMap band config invalid"

    # CRAMM production resample path: all references (pure + synthesized
    # mixtures) convolved to the HyMap2 126ch grid
    resampled = clf.get_resample(hymap_wl, hymap_fwhm)

    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    out(f"MCF: {MCF}")
    out(f"CV : {CV}  (HyMap2 126ch, wl {hymap_wl[0]:.4f}..{hymap_wl[-1]:.4f} um)")
    out()
    hdr = f"{'rule':<46s} {'cv_rec':>6s} {'corr':>9s} {'rmse':>8s} {'max|d|':>8s}  group"
    out(hdr)
    out("-" * len(hdr))

    rows = []
    for name in mcf:
        e = mcf[name]
        r = rules[name]
        ref = r["reference"]["reflectance_record"]
        cv_rec = int(e["record"])
        cv_row = cv.loc[cv_rec]
        cv_spec = np.asarray(cv_row["data"], float)[:126]
        cv_title = norm_title(cv_row["ititl"])
        mcf_title = norm_title(e["title"])

        # rf side resampled spectrum (mix_* synthesized by get_resample)
        key = ref if ref in resampled else (int(ref) if str(ref).isdigit() else str(ref))
        rf_spec = resampled[key]

        m = (cv_spec > 0) & np.isfinite(rf_spec)
        a, b = rf_spec[m], cv_spec[m]
        corr = float(np.corrcoef(a, b)[0, 1]) if m.sum() > 2 else float("nan")
        rmse = float(np.sqrt(np.mean((a - b) ** 2)))
        mx = float(np.max(np.abs(a - b)))

        is_mix = str(ref).startswith("mix_")
        group = ("mixture(合成)" if is_mix
                 else "declared(已声明偏差)" if name in DECLARED_DEVIATIONS
                 else "pure")
        ident = "" if is_mix else ("TITLE-DIFF" if cv_title != mcf_title else "")
        rows.append((name, cv_rec, corr, rmse, mx, group, is_mix, ref, cv_title))
        out(f"{name:<46s} {cv_rec:>6d} {corr:>9.5f} {rmse:>8.4f} {mx:>8.4f}  {group} {ident}")

    out()
    for g, label in (("pure", "纯谱一致规则"), ("declared(已声明偏差)", "已声明偏差"),
                     ("mixture(合成)", "混合物(合成 vs 实物)")):
        sub = [x for x in rows if x[5] == g]
        if not sub:
            continue
        corrs = [x[2] for x in sub]
        rmses = [x[3] for x in sub]
        worst = min(sub, key=lambda x: x[2])
        out(f"{label}: n={len(sub)}  corr min={min(corrs):.5f} median="
            f"{float(np.median(corrs)):.5f}  rmse max={max(rmses):.4f}  "
            f"最差={worst[0]} (corr={worst[2]:.5f}, rmse={worst[3]:.4f})")

    # 身份核对:卷积库记录标题 vs .mcf SPECPR 标题
    out()
    n_tdiff = sum(1 for x in rows if not x[6] and x[8] != norm_title(mcf[x[0]]["title"]))
    out(f"身份核对(cv 记录标题 vs mcf SPECPR 标题): {len(rows) - n_tdiff - sum(1 for x in rows if x[6])} 一致, "
        f"{n_tdiff} 不同(详见上表 TITLE-DIFF 标记)")

    if OUT:
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nsaved -> {OUT}")


if __name__ == "__main__":
    main()
