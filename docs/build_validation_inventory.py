# -*- coding: utf-8 -*-
"""Build the USGS splib07 sample inventory for CRAMM cross-sample validation.

For every splib07 sample in the mineral groups covered by the 77 rf.json
rules, list available sensor records and flag:
  REF      sample is a rule reference identity (splib06b record, verified
           against the official .mcf 2014 v6a) -> excluded from
           leave-sample-out validation (self-identification, suite 6)
  MIXREF   sample is a physical-mixture reference record
  CAL13    member of the chl13 chlorite calibration set (in-sample for the
           pos2250 closed-form calibration; excluded from proxy validation)
  MUS14    member of the 14-sample muscovite wv2200 calibration set
  BLACKL   skill blacklisted record (SMR-15 distorted; SMR-14 prochlorite;
           NMNH83369 CR-unusable)
  BECK14   Beckman 1.4 um region officially deleted (GDS4, HS146.3B)

Ground-truth columns: family from the archive MINERAL line (XRD-backed phase
ID); chemistry availability from parsed metadata (oxides / traces_ppm).

Output: docs/validation_sample_inventory.md + docs/validation_sample_inventory.csv
Run from repo root:  python docs/build_validation_inventory.py
"""
import csv
import json
import re
import sys
from collections import defaultdict

sys.path.insert(0, ".")
from usgs_splib import USGSLibrary  # noqa: E402

# ---------------------------------------------------------------- groups
# rule family -> (splib07 group, name-filter regex or None)
GROUPS = [
    ("muscovite",   "Mica",                 r"Muscovite|Margarite|Celadonite|Glauconite|Phengite|Paragonite"),
    ("illite",      "Illite",               None),
    ("chlorite",    "Chlorite",             None),
    ("kaolinite",   "Kaolinite-Serpentine", r"Kaolinite|Dickite|Nacrite|Halloysite"),
    ("serpentine",  "Kaolinite-Serpentine", r"Antigorite|Chrysotile|Lizardite"),
    ("smectite",    "Montmorillonite",      None),
    ("smectite",    "Smectite",             None),
    ("calcite",     "Calcite",              r"^Calcite|Calcite_"),
    ("siderite",    "Calcite",              r"Siderite"),
    ("dolomite",    "Dolomite",             None),
    ("gypsum",      "Gypsum",               None),
    ("alunite",     "Alunite",              r"^Alunite|Alunite_"),
    ("jarosite",    "Alunite",              r"Jarosite"),
    ("epidote",     "Epidote",              None),
    ("talc",        "Talc-Pyrophyllite",    r"Talc"),
    ("pyrophyllite","Talc-Pyrophyllite",    r"Pyrophyllite"),
    ("tremolite",   "Amphibole",            r"Tremolite|Actinolite"),
    ("buddingtonite","Feldspar",            r"Buddingtonite"),
    ("topaz",       "Topaz",                None),
    ("chalcedony",  "Quartz",               r"Chalcedony"),
    ("opal",        "Quartz",               r"Opal"),
]

# ------------------------------------------------------- flag token sets
def _rx(tokens):
    return re.compile("|".join(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![\d])"
                               for t in tokens), re.I)

# rule reference samples (splib06b identities, verified vs .mcf 2014 v6a)
REF = _rx([
    "GDS96", "RES-3", "NMNH96917", "GDS85", "WS272", "CU91-6A", "SMR-13",
    "HS323.1B", "GDS158", "CCa-1", "NMNH106242", "HS102.3B", "GDS26",
    "HS333.3B", "NMNH106237", "SHCa-1", "GDS4", "IMt-1", "GDS24", "GDS99",
    "CM9", "KGa-2", "SAz-1", "SWy-1", "CU93-1", "GDS113", "GDS116", "NG-1",
    "TM8896", "PYS1A", "HS271.3B", "GDS23", "SMR-15", "HS184.3B", "HS18.3B",
    "CU91-250A",
])
MIXREF = _rx(["GDS222", "CU93-260B", "CU93-65A", "CU93-5C", "H89-FR-2",
              "CU93-314", "GDS212", "GDS213"])

# mixture sample -> rf.json mixture rule correspondence.
# kind: direct = rule references this physical spectrum (x1.0);
#       exact  = documented proportions match the rule name;
#       approx = proportions close but not equal (archive check advised)
MIXTURE_RULE_MAP = {
    "Alun366+.50PyroPYS1A_GDS222":
        ("direct", "pyrophyllite.5+alunite.5_mix_intimate"),
    "Buddingtnt+Na-Mont_CU93-260B":
        ("direct", "buddingtonite+montmorillonite_mix_intimate"),
    "Chlorite+Muscovite_CU93-65A":
        ("direct", "chlorite+muscovite_mix_intimate"),
    "Kaol+Muscov_intimate_CU93-5C":
        ("direct", "kaolinite+muscovite_mix_intimate"),
    "Kaolin_Smect_H89-FR-2_.5Kao":
        ("direct", "kaolinite+smectite_mix_intimate"),
    "Kaolin_Smect_H89-FR-2_.5Kaol":
        ("direct", "kaolinite+smectite_mix_intimate"),
    "Muscov+Jaros_CU93-314_coatng":
        ("direct", "jarosite+muscovite_mix_intimate"),
    "Calcite.80+Mont_Swy-1_GDS212":
        ("direct", "calcite.8+montmorilloniteNa.2_mix_intimate"),
    "Calcite.80wt+Kaol_CM9_GDS213":
        ("direct", "kaolinite.2+calcite.8_mix_intimate"),
    "Alunite0.5+Kaol_KGa-1_AMX3":
        ("exact", "alunite.5+kaolinite.5 (KGa-1 endmember; CRAMM "
         "synthesizes with KGa-2, declared deviation)"),
    "Kaol.5+MuscCU91-250A_AMX13":
        ("exact", "kaolinite.5+muscoviteMedAl.5 (KGa-1 endmember; "
         "CRAMM synthesizes with KGa-2, declared deviation)"),
    "Kaol_Wxl+0.5Musc_Ruby_AMX12":
        ("exact", "kaolinite.5+muscoviteMedhighAl.5"),
    "Kaolwxl.75+Alun_HS295_AMX14":
        ("exact", "alunite.25+kaolinite.75"),
    "Pyrophyl.25+wxlKaol.75_AMX17":
        ("exact", "pyrophyllite.25+kaolinite.75"),
    "Calcite.5+Dolomite.5_AMX8":
        ("exact", "calcite.5+dolomite.5"),
    "Dolomite.5+Na-Mont.5_AMX21":
        ("exact", "dolomite.5+montmorilloniteNa.5"),
    "Dolomite.5+Ca-Mont.5_AMX10":
        ("exact", "dolomite.5+montmorilloniteCa.5"),
    "Calc.25+Dolo.25+Na-Mon_AMX18":
        ("approx", "calcite.18+dolomite.22+montmorilloniteNa.6 "
         "(physical .25/.25/.5)"),
    "Calc.25+Dolo.25+Ca-Mont_AMX7":
        ("approx", "calcite.18+dolomite.22+montmorilloniteCa.6 "
         "(physical .25/.25/.5)"),
    "Calcite.33+Ca-Mont.67_AMX19":
        ("approx", "calcite.25+montmorilloniteCa.75 (physical .33/.67)"),
    "Calcite.33+Na-Mont.67_AMX44":
        ("approx", "calcite.25+montmorilloniteNa.75 (physical .33/.67)"),
    "Calcite+.33Muscov_AMX5_Ruby":
        ("approx", "calcite.5+muscoviteMedHiAl.5 (physical .33 muscovite)"),
}
# chl13 chlorite calibration set (docs/figures/data/chl13_features.csv)
CAL13 = _rx(["GDS159", "SMR-13", "SMR-15", "GDS157", "GDS158", "CCa-1",
             "ps-12a", "ps-12c", "ps-12e", "ps-12f", "CLI101", "BUR-1340",
             "WAR-1924"])
# 14-sample muscovite wv2200 calibration set (USGS members;
# D:/my/mica14_formula_pos2200.csv)
MUS14 = _rx(["GDS108", "GDS111", "GDS113", "GDS114", "GDS116", "GDS117",
             "GDS118", "GDS119", "GDS120", "GDS4", "IMt-1"])
BLACKL = _rx(["SMR-15", "SMR-14", "NMNH83369"])
BECK14 = _rx(["GDS4", "HS146.3B"])


def flags_for(name):
    f = []
    if REF.search(name):
        f.append("REF")
    if MIXREF.search(name):
        f.append("MIXREF")
    if CAL13.search(name):
        f.append("CAL13")
    if MUS14.search(name):
        f.append("MUS14")
    if BLACKL.search(name):
        f.append("BLACKL")
    if BECK14.search(name):
        f.append("BECK14")
    return ",".join(f)


def main():
    lib = USGSLibrary()
    rows = []          # one row per (sample name, sensor record)
    seen = set()
    for family, group, name_rx in GROUPS:
        recs = lib.search(group=group)
        rx = re.compile(name_rx, re.I) if name_rx else None
        for r in recs:
            if rx and not rx.search(r.name):
                continue
            key = (r.name, r.sensor, r.quality)
            if key in seen:
                continue
            seen.add(key)
            try:
                ent = lib.metadata.entry(r.meta_filename)
            except Exception:
                ent = {}
            ox = ent.get("oxides") or {}
            tr = ent.get("traces_ppm") or {}
            rows.append({
                "family": family,
                "group": r.group,
                "name": r.name,
                "mineral_line": (ent.get("MINERAL") or "").strip(),
                "sensor": r.sensor,
                "quality": r.quality or "",
                "mtype": r.mtype or "",
                "chem_oxides": "Y" if ox else "",
                "chem_traces": "Y" if tr else "",
                "locality": (ent.get("COLLECTION_LOCALITY") or "").strip(),
                "flags": flags_for(r.name),
                "kind": "pure",
                "rule_link": "",
            })

    # ------------------------------------- SoilsAndMixtures chapter (group='')
    # artificial mixtures (documented proportions) + natural soils/rocks
    for r in lib.records:
        if r.category != "SoilsAndMixtures":
            continue
        key = (r.name, r.sensor, r.quality)
        if key in seen:
            continue
        seen.add(key)
        try:
            ent = lib.metadata.entry(r.meta_filename)
        except Exception:
            ent = {}
        ox = ent.get("oxides") or {}
        tr = ent.get("traces_ppm") or {}
        kind = ("mixture" if ("+" in r.name or "AMX" in r.name
                              or "Kaolin_Smect" in r.name
                              or "Kaolin-Smect" in r.name
                              or "_Mix_" in r.name) else "natural")
        link = MIXTURE_RULE_MAP.get(r.name)
        rule_link = f"{link[0]}: {link[1]}" if link else ""
        rows.append({
            "family": "soils",
            "group": r.group or "",
            "name": r.name,
            "mineral_line": (ent.get("MINERAL") or "").strip(),
            "sensor": r.sensor,
            "quality": r.quality or "",
            "mtype": r.mtype or "",
            "chem_oxides": "Y" if ox else "",
            "chem_traces": "Y" if tr else "",
            "locality": (ent.get("COLLECTION_LOCALITY") or "").strip(),
            "flags": flags_for(r.name),
            "kind": kind,
            "rule_link": rule_link,
        })

    rows.sort(key=lambda x: (x["family"], x["name"], x["sensor"]))

    # ------------------------------------------------------------- CSV
    cols = ["family", "group", "name", "mineral_line", "sensor", "quality",
            "mtype", "chem_oxides", "chem_traces", "locality", "flags",
            "kind", "rule_link"]
    with open("docs/validation_sample_inventory.csv", "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # ------------------------------------------------- per-sample rollup
    samples = {}
    for r in rows:
        s = samples.setdefault((r["family"], r["name"]), {
            "group": r["group"], "mineral_line": r["mineral_line"],
            "sensors": [], "quality": [], "chem": "", "traces": "",
            "locality": r["locality"], "flags": r["flags"],
            "kind": r["kind"], "rule_link": r["rule_link"]})
        s["sensors"].append(r["sensor"])
        s["quality"].append(r["quality"])
        s["chem"] = s["chem"] or r["chem_oxides"]
        s["traces"] = s["traces"] or r["chem_traces"]

    # ------------------------------------------------------------- MD
    L = []
    L.append("# USGS splib07 validation sample inventory for CRAMM\n")
    L.append("> Generated by `docs/build_validation_inventory.py` "
             "(re-run to refresh). Library: splib07a at `D:\\usgs_splib07`.\n")
    L.append("Scope: mineral groups covered by the 77 rf.json rules, plus "
             "the full SoilsAndMixtures chapter (artificial mixtures with "
             "documented proportions + natural soils/rocks). "
             "Vegetation/water/snow rules are out of scope (no mineral "
             "ground truth in the library).\n")
    L.append("**Flags**: REF = rule reference identity (excluded from "
             "leave-sample-out validation; self-identification is already "
             "covered by test suite 6) | MIXREF = physical-mixture reference "
             "| CAL13 = chl13 calibration member (in-sample for pos2250 "
             "calibration) | MUS14 = muscovite wv2200 calibration member | "
             "BLACKL = quality blacklist (SMR-15 distorted, SMR-14 "
             "prochlorite, NMNH83369 CR-unusable) | BECK14 = Beckman 1.4 µm "
             "officially deleted.\n")
    L.append("**Ground truth**: family = archive MINERAL line (XRD-backed); "
             "chem = parsed oxides table available (enables subtype-level "
             "expectation via structural formula).\n")

    fam_groups = defaultdict(list)
    for (fam, name), s in sorted(samples.items()):
        fam_groups[fam].append((name, s))

    total_s = total_r = usable_s = 0
    L.append("## Summary\n")
    L.append("| rule family | samples | records | excluded (REF/MIXREF) "
             "| calibration (CAL13/MUS14) | with chemistry | usable "
             "leave-sample-out |")
    L.append("|---|---|---|---|---|---|---|")
    summary = []
    for fam in sorted(f for f in fam_groups if f != "soils"):
        items = fam_groups[fam]
        n_s = len(items)
        n_r = sum(len(s["sensors"]) for _, s in items)
        n_ref = sum(1 for _, s in items if "REF" in s["flags"]
                    or "MIXREF" in s["flags"])
        n_cal = sum(1 for _, s in items
                    if ("CAL13" in s["flags"] or "MUS14" in s["flags"])
                    and "REF" not in s["flags"])
        n_chem = sum(1 for _, s in items if s["chem"])
        n_use = sum(1 for _, s in items
                    if "REF" not in s["flags"] and "MIXREF" not in s["flags"]
                    and "BLACKL" not in s["flags"])
        summary.append((fam, n_s, n_r, n_ref, n_cal, n_chem, n_use))
        total_s += n_s
        total_r += n_r
        usable_s += n_use
        L.append(f"| {fam} | {n_s} | {n_r} | {n_ref} | {n_cal} | {n_chem} "
                 f"| {n_use} |")
    L.append(f"| **total** | **{total_s}** | **{total_r}** |  |  |  "
             f"| **{usable_s}** |\n")

    # soils chapter has different ground-truth semantics: report separately
    soil_items = fam_groups.get("soils", [])
    soil_mix = [(n, s) for n, s in soil_items if s["kind"] == "mixture"]
    soil_nat = [(n, s) for n, s in soil_items if s["kind"] == "natural"]
    n_linked = sum(1 for _, s in soil_mix if s["rule_link"])
    n_soil_ref = sum(1 for _, s in soil_items
                     if "REF" in s["flags"] or "MIXREF" in s["flags"])
    L.append("## SoilsAndMixtures chapter\n")
    L.append(f"- artificial mixtures: **{len(soil_mix)}** samples "
             f"({sum(len(s['sensors']) for _, s in soil_mix)} records), "
             f"of which **{n_linked}** map to rf.json mixture rules "
             f"(direct/exact/approx, see tables)\n"
             f"- natural soils/rocks/assemblages: **{len(soil_nat)}** samples "
             f"({sum(len(s['sensors']) for _, s in soil_nat)} records)\n"
             f"- flagged as rule/mixture references: {n_soil_ref}\n"
             f"- ground-truth semantics: mixtures have documented endmember "
             f"proportions (name-encoded); natural samples have qualitative "
             f"archive mineralogy — use as \"expected winner within the "
             f"documented assemblage\" tests, not as pure-phase truth.\n")

    L.append("## Per-sample inventory\n")
    for fam in sorted(f for f in fam_groups if f != "soils"):
        L.append(f"### {fam}\n")
        L.append("| sample | archive MINERAL line | sensors (quality) "
                 "| chem | locality | flags |")
        L.append("|---|---|---|---|---|---|")
        for name, s in fam_groups[fam]:
            sq = ", ".join(f"{a}{b}" for a, b in
                           zip(s["sensors"], s["quality"]))
            chem = ("ox" if s["chem"] else "") + ("+tr" if s["traces"]
                                                  else "")
            loc = s["locality"][:40]
            L.append(f"| {name} | {s['mineral_line'][:40]} | {sq} "
                     f"| {chem} | {loc} | {s['flags']} |")
        L.append("")

    # --------------------------------------- soils chapter: two subsections
    L.append("### soils — artificial mixtures\n")
    L.append("| sample | mixture-rule correspondence | sensors (quality) "
             "| chem | locality | flags |")
    L.append("|---|---|---|---|---|---|")
    for name, s in soil_mix:
        sq = ", ".join(f"{a}{b}" for a, b in zip(s["sensors"], s["quality"]))
        chem = ("ox" if s["chem"] else "") + ("+tr" if s["traces"] else "")
        L.append(f"| {name} | {s['rule_link']} | {sq} | {chem} "
                 f"| {s['locality'][:40]} | {s['flags']} |")
    L.append("")
    L.append("### soils — natural soils / rocks / assemblages\n")
    L.append("| sample | sensors (quality) | chem | locality | flags |")
    L.append("|---|---|---|---|---|")
    for name, s in soil_nat:
        sq = ", ".join(f"{a}{b}" for a, b in zip(s["sensors"], s["quality"]))
        chem = ("ox" if s["chem"] else "") + ("+tr" if s["traces"] else "")
        L.append(f"| {name} | {sq} | {chem} | {s['locality'][:40]} "
                 f"| {s['flags']} |")
    L.append("")

    with open("docs/validation_sample_inventory.md", "w",
              encoding="utf-8") as f:
        f.write("\n".join(L))

    print(f"samples={total_s} records={total_r} usable_leave_sample_out="
          f"{usable_s}")
    for fam, n_s, n_r, n_ref, n_cal, n_chem, n_use in summary:
        print(f"  {fam:14s} samples={n_s:3d} records={n_r:3d} ref={n_ref:2d} "
              f"cal={n_cal:2d} chem={n_chem:2d} usable={n_use:3d}")
    print(f"  soils: mixtures={len(soil_mix)} ({n_linked} rule-linked) "
          f"natural={len(soil_nat)} ref-flagged={n_soil_ref}")


if __name__ == "__main__":
    main()
