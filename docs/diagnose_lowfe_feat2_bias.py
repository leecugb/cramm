# Is chlorite_lowFe's feat2 (VNIR 0.51-1.74 um, w=0.3) unfair to it?
# Archive of the 2026-08-29 measurement (docs/lowfe_feat2_bias.md). Behavior
# unchanged -- feat2 is official .mcf v6a heritage. Run from the repo root.
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "repo", "src"))
from cramm import MicaEngine
from cramm.classifier import _diagnostic_feature

NC = "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc"

eng = MicaEngine()
spectrum, lon, lat, w, bp, wl, chanels = eng.load_emit(NC)
clf = eng._classifier
resampled = clf.get_resample(w, bp)

tile = spectrum[440:540, 160:260]
spec = tile.reshape(-1, tile.shape[2])[:, chanels].astype("float64")
N = len(spec)

# production classification of the tile for winner labels
res = clf.classify(tile, wl, w, bp, chanels, n_workers=1)
num = res.num
idx = res.index_d

def feats(rule):
    out = []
    ref = resampled[clf.rf[rule]["reference"]["reflectance_record"]][chanels]
    for f in clf.rf[rule]["diagnostic_features"]:
        cc = f["continuum_constraints"]
        cc_list = [cc["left_min"], cc["left_max"], cc["mean_min"], cc["mean_max"],
                   cc["right_min"], cc["right_max"], cc["ratio_min"], cc["ratio_max"]]
        r2w, dw, _, _ = _diagnostic_feature(
            spec, ref, wl, f["continuum_endpoints"], f["feature_weight"],
            cc_list, f["fit_constraint"], f["depth_constraints"])
        out.append((f["feature_weight"], r2w))
    return out

def fit_dist(rule):
    """per-feature raw r2 (unweighted) and the weighted-fit sum"""
    fs = feats(rule)
    raw = [r2w / wt if wt > 0 else np.full(N, np.nan) for wt, r2w in fs]
    wsum = np.nansum(np.vstack([r2w for wt, r2w in fs]), axis=0)
    # pixels rejected at any feature -> NaN in that feature's r2w; mimic chain:
    alive = np.ones(N, bool)
    for wt, r2w in fs:
        alive &= ~np.isnan(r2w)
    wsum = np.where(alive, wsum, np.nan)
    return raw, wsum, alive

low_raw, low_wsum, low_alive = fit_dist("chlorite_lowFe")
cli_raw, cli_wsum, cli_alive = fit_dist("clinochlore")

# --- on pixels where lowFe passes all its gates: fit1 vs fit2 --------------
m = low_alive
print(f"tile: lowFe passes all gates on {m.sum()} px")
print(f"  feat1 (2.3um, w=0.7) raw fit: median {np.nanmedian(low_raw[1][m]):.4f}")
print(f"  feat2 (VNIR,  w=0.3) raw fit: median {np.nanmedian(low_raw[2][m]):.4f}")
pen = 0.3 * (low_raw[1][m] - low_raw[2][m])   # score penalty vs renormalized 1.0*fit1
print(f"  penalty 0.3*(fit1-fit2): median {np.median(pen):+.4f}, "
      f"p90 {np.percentile(pen, 90):+.4f}, frac fit2<fit1: {(low_raw[2][m] < low_raw[1][m]).mean()*100:.1f}%")

# weighted score comparison on lowFe-alive pixels
renorm = low_raw[1][m]  # hypothetical: feat1 alone, weight 1.0
print(f"  weighted fit current(0.7f1+0.3f2): median {np.nanmedian(low_wsum[m]):.4f}")
print(f"  weighted fit if feat1-only (1.0):  median {np.nanmedian(renorm):.4f}")
print(f"  below min_weighted_fit 0.64: current {np.nansum(low_wsum[m] < 0.64)}, renorm {(renorm < 0.64).sum()}")

# --- head-to-head: lowFe vs clinochlore weighted fit on chlorite winners ---
chl_names = ["chlorite_lowFe", "clinochlore", "clinochlore_Fe", "thuringite"]
for n in chl_names:
    gi = idx.get(n)
    print(f"{n:18s} tile winners: {int((num == gi).sum()) if gi is not None else 0}")

clino_gi = idx.get("clinochlore")
mm = (num == clino_gi) & low_alive
print(f"\nclinochlore winners where lowFe also passes all gates: {mm.sum()}")
if mm.sum():
    d = low_wsum[mm] - cli_wsum[mm]
    print(f"  lowFe_wsum - clino_wsum: median {np.median(d):+.4f} "
          f"(lowFe would win {(d > 0).sum()} / {mm.sum()})")
    d2 = low_raw[1][mm] - cli_wsum[mm]   # lowFe without feat2 penalty
    print(f"  if lowFe scored 1.0*fit1:  median {np.median(d2):+.4f} "
          f"(lowFe would win {(d2 > 0).sum()} / {mm.sum()})")
