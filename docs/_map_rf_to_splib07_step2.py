# Map every rf.json reference spectrum (splib06b record) to splib07 records.
# Step 2: per-rule sample token -> search splib07 -> markdown mapping doc.
import json
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cramm.classifier import MicaClassifier
from usgs_splib import USGSLibrary

# rule -> sample-id token used for splib07 substring search (from splib06b titles)
TOKENS = OrderedDict([
    ("vegetation_green", "ES-Needls"),
    ("vegetation_npv_and_green", "C04-170"),
    ("snow_melting", "mSnw01a"),
    ("snow_slush", "mSnw09"),
    ("water", "SW1"),
    ("water_sediment_high", "Water+Montmor"),
    ("water_sediment_low", "Water+Montmor"),
    ("dry_veg_grass", "GDS480"),
    ("dry_veg_grass_2_3um", "GDS480"),
    ("dry_veg_nongrass", "Needles-3"),
    ("dry_veg_nongrass_2_3um", "Needles-3"),
    ("muscovite_lowAl", "CU93-1"),
    ("muscovite_medAl", "CU91-250A"),
    ("muscovite_medhighAl", "GDS113"),
    ("muscovite_Fe-rich", "GDS116"),
    ("illite_imt1", "IMt-1"),
    ("illite_gds4", "Illite_GDS4"),
    ("kaolinite_wxl", "CM9"),
    ("kaolinite_pxl", "KGa-2"),
    ("kaolinite+clay_mica_or_halloysite", "NMNH106237"),
    ("kaolinite_or_dickite", "NMNH106242"),
    ("buddingtonite", "GDS85_"),
    ("buddingtonite+montmorillonite_mix_intimate", "CU93-260B"),
    ("alunite_K_250C", "GDS96_"),
    ("alunite_Na_450C", "RES-3"),
    ("pyrophyllite", "PYS1A"),
    ("jarosite_Na", "GDS24_"),
    ("jarosite_K", "GDS99"),
    ("montmorillonite_Na", "SWy-1"),
    ("montmorillonite_Ca", "SAz-1"),
    ("nontronite", "NG-1"),
    ("hectorite", "SHCa-1"),
    ("gypsum", "HS333.3B"),
    ("chlorite_lowFe", "SMR-13"),
    ("clinochlore", "GDS158"),
    ("clinochlore_Fe", "SC-CCa-1"),
    ("thuringite", "SMR-15"),
    ("epidote", "GDS26"),
    ("pyrophyllite.5+alunite.5_mix_intimate", "GDS222"),
    ("kaolinite+muscovite_mix_intimate", "CU93-5C"),
    ("kaolinite+smectite_mix_intimate", "H89-FR-2"),
    ("jarosite+muscovite_mix_intimate", "CU93-314"),
    ("chlorite+muscovite_mix_intimate", "CU93-65A"),
    ("calcite_abundant", "WS272"),
    ("calcite", "WS272"),
    ("dolomite_abundant", "HS102.3B"),
    ("dolomite", "HS102.3B"),
    ("carbonate_Fe_bearing", "HS271.3B"),
    ("chalcedony", "CU91-6A"),
    ("hydrated_silica", "TM8896"),
    ("tremolite_or_talc", "HS18.3B"),
    ("talc_or_tremolite", "GDS23"),
    ("serpentine_antigorite_or_calcite+dolomite", "NMNH96917"),
    ("serpentine_chrysotile", "HS323.1B"),
    ("serpentine_antigorite_withironfeat", "NMNH96917"),
    ("serpentine_chrysotile_withsecondfeat", "HS323.1B"),
    ("serpentine_antigorite_withsecondfeat", "NMNH96917"),
    ("topaz", "HS184.3B"),
])

d = json.load(open(r"d:\CRAMM\cramm\data\rf.json"))
rules = d["rf"]
c = MicaClassifier.from_paths()
dic = c.dic3.set_index("irecno")
lib = USGSLibrary(r"D:\usgs_splib07")

def search(token):
    out = lib.search(name=token)
    # rank: exact sample_id first, then variants; keep (name, sensor, quality, mtype)
    out.sort(key=lambda r: (r.sample_id != token, r.sample_id, r.sensor))
    return out

lines = []
lines.append("# rf.json 参考光谱 ↔ splib07 样本映射清单")
lines.append("")
lines.append("> 生成日期：2026-08-29 ｜ 生成脚本：`docs/_map_rf_to_splib07_step2.py`")
lines.append("> 左侧为 CRAMM rf.json 规则（参考谱来自 splib06b，记录号 + 标题）；右侧为 splib07 中同样品名的全部记录。")
lines.append("> splib06b 与 splib07 是两套独立库：同名样品是同一物理样品的重测/再收录，记录并非逐条对应。")
lines.append("")
lines.append("| rf.json 规则 | splib06b 记录 | splib06b 标题 | splib07 对应记录 |")
lines.append("|---|---|---|---|")

n_ok = n_miss = 0
missing = []
for name in rules:
    rec = rules[name]["reference"]["reflectance_record"]
    if str(rec).startswith("mix_"):
        title = "合成混合（rf.json 内置，无 splib06b 记录）"
        found = None
    else:
        title = dic.loc[int(rec), "ititl"].strip() if int(rec) in dic.index else "??"
        token = TOKENS.get(name)
        found = search(token) if token else []
    if found is None:
        cell = "—（合成）"
    elif not found:
        cell = "**未找到**"
        n_miss += 1
        missing.append(name)
    else:
        n_ok += 1
        cell = "<br>".join(f"`{r.name}` {r.sensor}{r.quality} {r.mtype}" for r in found)
    rec_s = str(rec)
    lines.append(f"| {name} | {rec_s} | {title} | {cell} |")

lines.append("")
lines.append(f"统计：{n_ok} 条规则在 splib07 找到同名样品记录，{n_miss} 条未找到：{', '.join(missing)}")
lines.append("")
lines.append("## 备注")
lines.append("")
lines.append("- 样品名后缀变体（如 GDS113a、SMR-13.c）是同一样品的不同制备/粒径记录，一并列出。")
lines.append("- splib07 检索用 `name=` 子串匹配；`Clinochlore_Fe_SC-CCa-1.a` 的 sample_id 是 `Fe`，此处按全名子串 `SC-CCa-1` 检索。")
lines.append("- 19 条 `mix_*` 规则为 rf.json 内置线性合成谱，splib07 中无对应物理记录。")
lines.append("- **AMX 系列是计算混合而非实测物理混合**（2026-08-29 元数据核实）：`Kaol.5+MuscCU91-250A_AMX13`、`Alunite.5+MuscCU91-250A_AMX4` 等的 HTMLmetadata 明确标注 `MIXTURE_TYPE: Areal` + `SAMPLE_DESCRIPTION: Calculated areal (linear) mixture ...`，与 rf.json 的 `mix_*` 线性合成谱性质相同，不能作为物理混合 ground truth。注意 AMX13 的高岭石端元是 KGa-1（不是 CM9）、AMX4 的明矾石端元是 HS295.3B。")
lines.append("- 真正意义的实测混合样品是 CU93 系列天然混合岩石（如 `Chlorite+Muscovite_CU93-65A`，`MIXTURE_TYPE: Intimate`，Cuprite Harkless 组天然千枚岩）。")

out = r"d:\CRAMM\docs\rfjson_splib07_mapping.md"
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("wrote", out)
print(f"matched rules: {n_ok}, missing: {n_miss} -> {missing}")
