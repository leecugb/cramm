# Stage 3 of splib07 migration: generate cramm/data/rf_splib07.json.
#
# The v07 rule file is rf.json verbatim (rules bit-identical -- diagnostic
# parameters are inherited unchanged, per the plan's not-to-do list) plus:
#   reference_source : "rf07_spectra.npz"  (engine loads the baked bundle
#                                           instead of splib06b)
#   wavelength_map   : every needed record -> -1 (the npz's shared 1 nm
#                      master-grid wavelength row)
#   mixtures         : 14 recipes bit-identical to rf.json; the 5 mixes with a
#                      recipe-exact splib07 AMX calculated-mixture record are
#                      rewritten as weight-1.0 aliases of that record's
#                      synthetic rec id (90000+AMX number; GDS212/213
#                      precedent), so the engine resamples the baked AMX
#                      record instead of synthesizing from endmembers.
# Record-number keys are kept as the reference namespace, so all 77 rules and
# 19 mixtures resolve against the 58 baked records.
import json

import numpy as np

d = json.load(open(r"d:\CRAMM\cramm\data\rf.json", encoding="utf-8"))
rf, mixtures = d["rf"], d["mixtures"]
sel = json.load(open(r"d:\CRAMM\docs\splib07_selection.json", encoding="utf-8"))

# same id-collection logic as MicaClassifier.from_paths
ids = set()
for value in rf.values():
    ref = value["reference"]["reflectance_record"]
    if isinstance(ref, int):
        ids.add(ref)
    for key in ("not_absolute_features", "not_relative_features"):
        for feat in value.get(key, []):
            rec = feat["reflectance_record"]
            if isinstance(rec, int):
                ids.add(rec)
for components in mixtures.values():
    for comp_id in components.keys():
        ids.add(int(comp_id))

# AMX aliases: replace the 5 recipes by weight-1.0 references to the baked
# AMX record (endmember ids stay in `ids` -- other rules/mixes still use them)
for a in sel["amx_mixture_aliases"]:
    mixtures[a["mix_id"]] = {str(a["synthetic_rec"]): 1.0}
    ids.add(a["synthetic_rec"])

# every id must have a baked record in the npz
z = np.load(r"d:\CRAMM\cramm\data\rf07_spectra.npz", allow_pickle=False)
meta = json.loads(str(z["meta"][0]))
baked = {int(m["splib06b_rec"]) for m in meta}
missing = sorted(ids - baked)
if missing:
    raise SystemExit(f"ids without baked npz record: {missing}")

out = {
    "reference_source": "rf07_spectra.npz",
    "reference_provenance": "docs/splib07_selection.json",
    "rf": rf,
    "mixtures": mixtures,
    "wavelength_map": {str(i): -1 for i in sorted(ids)},
}
with open(r"d:\CRAMM\cramm\data\rf_splib07.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"wrote cramm/data/rf_splib07.json: {len(rf)} rules, {len(mixtures)} mixtures "
      f"({len(sel['amx_mixture_aliases'])} AMX-aliased), "
      f"{len(ids)} reference ids -> npz master grid row -1")
