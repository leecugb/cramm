# Survey all muscovite records in splib07 (library: D:\usgs_splib07)
# usgs-splib skill, name= search (not keyword). No band computation here.
from usgs_splib import USGSLibrary

lib = USGSLibrary(r"D:\usgs_splib07")
print("library:", lib.path)

recs = lib.search(name="Muscovite")
print(f"\nsearch(name='Muscovite'): {len(recs)} records")

rows = []
for r in recs:
    rows.append((r.name, r.sensor, r.quality, r.mtype, r.errorbar is not None))

for name, sensor, q, mt, eb in rows:
    print(f"  {name:38s} {sensor:6s} q={q:3s} {mt:4s} eb={eb}")

# group by sample
from collections import defaultdict
g = defaultdict(list)
for r in recs:
    g[r.name].append(r)
print(f"\n{len(g)} distinct named samples")
for name, rs in g.items():
    sen = ", ".join(f"{r.sensor}{r.quality}:{r.mtype}" for r in rs)
    print(f"  {name:38s} [{len(rs)} rec] {sen}")

# chemistry availability (Al2O3) per sample
print("\nchemistry (Al2O3 wt%):")
for name, rs in g.items():
    try:
        al = lib.metadata.composition(rs[0].meta_filename, "Al2O3")
    except Exception as e:
        al = f"n/a ({type(e).__name__})"
    print(f"  {name:38s} Al2O3 = {al}")
