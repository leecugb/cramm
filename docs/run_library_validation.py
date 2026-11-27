# -*- coding: utf-8 -*-
"""Classify the splib07 validation inventory at EMIT band space with CRAMM.

Pipeline per record in docs/validation_sample_inventory.csv:
  1. load spectrum from the local splib07a library (usgs_splib)
  2. zero specpr deletion markers (-1.23e-34) in wavelength and data
  3. Gaussian-resample onto the EMIT grid (cramm.classifier._resample_ --
     the identical kernel the engine applies to its reference library)
  4. classify with eng.classify_spectrum (77 rules, Top-77 returned)
  5. score against the expectation:
       - pure mineral families  -> winner within the family's rule set
       - rule-linked mixtures   -> winner == linked mixture rule
       - natural soils / unlinked mixtures -> recorded, not scored

Circularity control: REF/MIXREF rows are the rule-reference samples.
Rows whose sensor matches the reference record's instrument are SELF-ID
controls (circular; equivalent to test suite 6); same sample on a different
sensor is the cross-instrument variant. Rows without REF/MIXREF are the
actual leave-sample-out (LSO) validation pool. BLACKL rows are run but
excluded from LSO metrics.

BECK stratum caveat (see docs/diagnose_beck_resample.py): splib07a serves
"BECK" records at ~10 nm SWIR sampling, coarser than the EMIT ~7.5 nm FWHM,
so the strict-FWHM kernel punches holes exactly at the 2.0-2.5 um diagnostic
bands and no rule fires. This is a source-grid artifact of the validation
pipeline, NOT a classifier defect: all 72 bundled splib06b references
(including the Beckman-based ones, stored at 1 nm) resample to 0% zeros.
The report therefore separates BECK from the valid strata (NIC4/ASDFR/ASDNG).

Usage (from repo root):
  python docs/run_library_validation.py                # report from cached CSV
  python docs/run_library_validation.py --reclassify   # full re-run + report

Output: docs/library_validation_results.csv + console report.
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, "repo/src")
from cramm import MicaEngine  # noqa: E402
from cramm.classifier import _resample_  # noqa: E402
from usgs_splib import USGSLibrary  # noqa: E402

NC = "EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"
INVENTORY = "docs/validation_sample_inventory.csv"
OUT = "docs/library_validation_results.csv"

# family -> expected winner rules (pure rules only)
FAMILY_RULES = {
    "alunite": {"alunite_K_250C", "alunite_Na_450C"},
    "buddingtonite": {"buddingtonite"},
    "calcite": {"calcite", "calcite_abundant"},
    "chalcedony": {"chalcedony"},
    "chlorite": {"chlorite_lowFe", "clinochlore", "clinochlore_Fe",
                 "thuringite"},
    "dolomite": {"dolomite", "dolomite_abundant"},
    "epidote": {"epidote"},
    "gypsum": {"gypsum"},
    "illite": {"illite_gds4", "illite_imt1"},
    "jarosite": {"jarosite_K", "jarosite_Na"},
    "kaolinite": {"kaolinite_wxl", "kaolinite_pxl", "kaolinite_or_dickite",
                  "kaolinite+clay_mica_or_halloysite"},
    "muscovite": {"muscovite_medhighAl", "muscovite_medAl",
                  "muscovite_lowAl", "muscovite_Fe-rich"},
    "opal": {"hydrated_silica"},
    "pyrophyllite": {"pyrophyllite"},
    "serpentine": {"serpentine_antigorite_or_calcite+dolomite",
                   "serpentine_antigorite_withironfeat",
                   "serpentine_antigorite_withsecondfeat",
                   "serpentine_chrysotile",
                   "serpentine_chrysotile_withsecondfeat"},
    "siderite": {"carbonate_Fe_bearing"},
    "smectite": {"montmorillonite_Na", "montmorillonite_Ca", "hectorite",
                 "nontronite"},
    "talc": {"talc_or_tremolite", "tremolite_or_talc"},
    "tremolite": {"tremolite_or_talc", "talc_or_tremolite"},
    "topaz": {"topaz"},
}

# reference-sample token -> instrument of the rf.json reference record
# (from the splib06b titles: W1R1B* = Beckman, W*R4N* = Nicolet NIC4)
REF_INSTR = {
    "GDS96": "NIC4", "RES-3": "NIC4", "NMNH96917": "BECK", "GDS85": "BECK",
    "WS272": "BECK", "CU91-6A": "BECK", "SMR-13": "BECK", "HS323.1B": "BECK",
    "GDS158": "NIC4", "CCa-1": "NIC4", "NMNH106242": "NIC4",
    "HS102.3B": "BECK", "GDS26": "NIC4", "HS333.3B": "NIC4",
    "NMNH106237": "NIC4", "SHCa-1": "NIC4", "GDS4": "BECK", "IMt-1": "BECK",
    "GDS24": "NIC4", "GDS99": "NIC4", "CM9": "NIC4", "KGa-2": "NIC4",
    "SAz-1": "NIC4", "SWy-1": "NIC4", "CU93-1": "NIC4", "GDS113": "NIC4",
    "GDS116": "NIC4", "NG-1": "NIC4", "TM8896": "NIC4", "PYS1A": "NIC4",
    "HS271.3B": "BECK", "GDS23": "NIC4", "SMR-15": "NIC4",
    "HS184.3B": "BECK", "HS18.3B": "NIC4", "CU91-250A": "NIC4",
    "GDS222": "BECK", "CU93-260B": "NIC4", "CU93-65A": "BECK",
    "CU93-5C": "BECK", "H89-FR-2": "NIC4", "CU93-314": "BECK",
}

import re  # noqa: E402


def ref_instrument(name):
    for tok, instr in REF_INSTR.items():
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(tok) + r"(?![\d])",
                     name, re.I):
            return instr
    return ""


def linked_rule(rule_link):
    """'exact: alunite.5+kaolinite.5 (note)' -> ('exact', 'alunite.5+kaolinite.5')"""
    if not rule_link:
        return "", ""
    conf, _, rest = rule_link.partition(": ")
    rule = rest.split(" (")[0].strip()
    return conf, rule


def classify_inventory():
    """Run the full pipeline; return the list of result-row dicts."""
    eng = MicaEngine()
    _, _, _, w, bp, wl, chanels = eng.load_emit(NC)
    print(f"EMIT grid: {len(w)} bands {w[0]:.4f}..{w[-1]:.4f} um, "
          f"{len(chanels)} valid", flush=True)

    lib = USGSLibrary()
    index = {}
    for r in lib.records:
        index.setdefault((r.name, r.sensor), r)

    inv = list(csv.DictReader(open(INVENTORY, encoding="utf-8-sig")))
    print(f"inventory rows: {len(inv)}", flush=True)

    out = []
    misses = []
    for i, row in enumerate(inv):
        rec = index.get((row["name"], row["sensor"]))
        if rec is None:
            misses.append((row["name"], row["sensor"]))
            continue
        spec = lib.load(rec)
        bands = np.asarray(spec.wavelength, dtype="float64").copy()
        data = np.asarray(spec.reflectance, dtype="float64").copy()
        bad = (data < -1e34) | (bands <= 0) | (data <= 0)
        bands[bad] = 0.0
        data[bad] = 0.0
        res = _resample_(bands, data, w, bp)
        res[np.isnan(res)] = 0.0

        top = eng.classify_spectrum(res, wl, w, bp, chanels, top_n=77)
        names = [t["name"] for t in top]

        flags = row["flags"]
        family = row["family"]
        if family == "soils":
            conf, rule = linked_rule(row["rule_link"])
            expected = {rule} if rule else set()
        else:
            conf = ""
            expected = FAMILY_RULES[family]

        circular = ""
        if "REF" in flags or "MIXREF" in flags:
            instr = ref_instrument(row["name"])
            circular = ("self" if instr and instr == row["sensor"]
                        else "xinstr")

        rank_exp = 0
        if expected:
            for rk, nm in enumerate(names, 1):
                if nm in expected:
                    rank_exp = rk
                    break

        out.append({
            "family": family,
            "kind": row["kind"],
            "name": row["name"],
            "sensor": row["sensor"],
            "quality": row["quality"],
            "flags": flags,
            "link_conf": conf,
            "expected": ";".join(sorted(expected)),
            "circular": circular,
            "winner": names[0] if names else "",
            "winner_fit": f"{top[0]['fit']:.6f}" if top else "",
            "winner_fd": f"{top[0]['fd']:.6f}" if top else "",
            "rank_expected": rank_exp,
            "family_hit1": int(bool(expected) and rank_exp == 1),
            "family_hit3": int(bool(expected) and 0 < rank_exp <= 3),
            "top3": " | ".join(f"{t['name']}:{t['fit']:.4f}"
                               for t in top[:3]),
        })
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(inv)}", flush=True)

    print(f"classified {len(out)} rows; unmatched records: {len(misses)}",
          flush=True)
    for m in misses:
        print("  MISS", m)
    return out


def write_results(out):
    cols = ["family", "kind", "name", "sensor", "quality", "flags",
            "link_conf", "expected", "circular", "winner", "winner_fit",
            "winner_fd", "rank_expected", "family_hit1", "family_hit3",
            "top3"]
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.DictWriter(f, fieldnames=cols)
        wr.writeheader()
        wr.writerows(out)
    print(f"wrote {OUT} ({len(out)} rows)", flush=True)


def _normalize(rows):
    """Coerce CSV-string numerics to int so report() works on both sources."""
    for r in rows:
        for k in ("rank_expected", "family_hit1", "family_hit3"):
            r[k] = int(r[k]) if str(r[k]).strip() not in ("", "None") else 0
    return rows


def report(out):
    out = _normalize(out)

    def rate(rows, key):
        sel = [r for r in rows if r["expected"]]
        n = len(sel)
        h = sum(r[key] for r in sel)
        return h, n

    pure = [r for r in out if r["kind"] == "pure"]
    selfid = [r for r in pure if r["circular"] == "self"]
    xinstr = [r for r in pure if r["circular"] == "xinstr"]
    lso = [r for r in pure if not r["circular"]
           and "BLACKL" not in r["flags"]]
    blackl = [r for r in pure if "BLACKL" in r["flags"]
              and not r["circular"]]

    def by_sensor(rows):
        return sorted({r["sensor"] for r in rows})

    print("\n================ pure mineral records ================")
    print("NOTE on the BECK stratum (docs/diagnose_beck_resample.py):")
    print("  splib07a serves BECK records at ~10 nm SWIR sampling, coarser than")
    print("  the EMIT ~7.5 nm FWHM, so the strict-FWHM resample kernel leaves")
    print("  holes at the 2.0-2.5 um diagnostic bands and NO rule fires. This")
    print("  is a validation-pipeline grid artifact, not a classifier defect:")
    print("  all 72 bundled splib06b references (Beckman ones stored at 1 nm)")
    print("  resample to 0% zeros. Valid strata = NIC4 / ASDFR / ASDNG.")

    print("\n-- SELF-ID control (circular) by sensor --")
    for s in by_sensor(selfid):
        rows = [r for r in selfid if r["sensor"] == s]
        h1, n1 = rate(rows, "family_hit1")
        tag = "  <-- grid artifact" if s == "BECK" else ""
        print(f"  {s:6s} n={n1:3d}  winner-hit={h1:3d} "
              f"({h1 / max(n1, 1) * 100:5.1f}%){tag}")

    print("\n-- cross-instrument same-sample by sensor --")
    for s in by_sensor(xinstr):
        rows = [r for r in xinstr if r["sensor"] == s]
        h1, n1 = rate(rows, "family_hit1")
        tag = "  <-- grid artifact" if s == "BECK" else ""
        print(f"  {s:6s} n={n1:3d}  winner-hit={h1:3d} "
              f"({h1 / max(n1, 1) * 100:5.1f}%){tag}")

    print("\n-- LEAVE-SAMPLE-OUT --")
    h1, n1 = rate(lso, "family_hit1")
    h3, _ = rate(lso, "family_hit3")
    print(f"  all sensors            n={n1:3d}  winner-hit={h1:3d} "
          f"({h1 / max(n1, 1) * 100:5.1f}%)  top3-hit={h3:3d}  "
          f"(understated: includes BECK artifact)")
    lso_nb = [r for r in lso if r["sensor"] != "BECK"]
    h1, n1 = rate(lso_nb, "family_hit1")
    h3, _ = rate(lso_nb, "family_hit3")
    print(f"  excluding BECK (valid) n={n1:3d}  winner-hit={h1:3d} "
          f"({h1 / max(n1, 1) * 100:5.1f}%)  top3-hit={h3:3d}  "
          f"<-- headline")

    print("\n-- LSO by sensor --")
    for s in by_sensor(lso):
        rows = [r for r in lso if r["sensor"] == s]
        h1, n1 = rate(rows, "family_hit1")
        h3, _ = rate(rows, "family_hit3")
        tag = "  <-- grid artifact" if s == "BECK" else ""
        print(f"  {s:6s} n={n1:3d}  winner-hit={h1:3d} "
              f"({h1 / max(n1, 1) * 100:5.1f}%)  top3-hit={h3:3d}{tag}")

    print("\n-- LSO by family (valid strata, BECK excluded) --")
    for f_ in sorted({r["family"] for r in lso_nb}):
        rows = [r for r in lso_nb if r["family"] == f_]
        h1, n1 = rate(rows, "family_hit1")
        h3, _ = rate(rows, "family_hit3")
        print(f"  {f_:14s} n={n1:3d}  winner-hit={h1:3d} "
              f"({h1 / max(n1, 1) * 100:5.1f}%)  top3-hit={h3:3d}")

    h1, n1 = rate(blackl, "family_hit1")
    print(f"\nblacklisted (informational)  n={n1:3d}  winner-hit={h1:3d} "
          f"({h1 / max(n1, 1) * 100:5.1f}%)")

    print("\n-- genuine LSO misses (valid strata; BECK excluded as artifact) --")
    for r in lso_nb:
        if r["expected"] and not r["family_hit1"]:
            w = r["winner"] or "(no rule fired)"
            print(f"  {r['family']:13s} {r['name']:42s} {r['sensor']:6s}"
                  f" -> {w} (fit={r['winner_fit']})")

    print("\n================ rule-linked mixtures ================")
    print("(BECK rows are grid-artifact no-fires; hit rates below exclude both")
    print(" circular self-ID rows and the compromised BECK stratum.)")
    linked = [r for r in out if r["kind"] == "mixture" and r["expected"]]
    for conf in ("direct", "exact", "approx"):
        rows = [r for r in linked if r["link_conf"] == conf]
        valid = [r for r in rows
                 if r["circular"] != "self" and r["sensor"] != "BECK"]
        h1 = sum(r["family_hit1"] for r in valid)
        h3 = sum(r["family_hit3"] for r in valid)
        print(f"  {conf:7s} n={len(rows):2d}  valid(non-circ,non-BECK)="
              f"{len(valid):2d}  winner==linked rule: {h1}   top3: {h3}")
        for r in rows:
            if int(r["family_hit1"]):
                mark = ""
            elif r["sensor"] == "BECK":
                mark = "  <-- grid artifact"
            elif r["circular"] == "self":
                mark = "  <-- circular (miss)"
            else:
                mark = "  <-- miss"
            w = r["winner"] or "(no rule fired)"
            print(f"    {r['name']:44s} {r['sensor']:6s} -> {w}"
                  f" ({r['winner_fit']}){mark}")

    print("\n================ natural soils (recorded) ==========")
    print("(BECK rows returning '(no rule fired)' are the grid artifact.)")
    for r in out:
        if r["kind"] == "natural":
            print(f"  {r['name']:44s} {r['sensor']:6s} -> "
                  f"{r['winner'] or '(no rule fired)'} "
                  f"({r['winner_fit']})")


def main():
    reclassify = "--reclassify" in sys.argv
    if not reclassify and os.path.exists(OUT):
        print(f"report-only mode: reading cached {OUT} "
              f"(use --reclassify to re-run the 627 classifications)")
        out = _normalize(list(csv.DictReader(open(OUT, encoding="utf-8-sig"))))
        report(out)
    else:
        out = classify_inventory()
        write_results(out)
        report(out)


if __name__ == "__main__":
    main()
