# -*- coding: utf-8 -*-
"""Generate the CRAMM paper figures archived under docs/figures/.

Data sources (all in-repo or produced by archived scripts):
  - docs/benchmark.json            -> fig_performance (scaling curve)
  - D:/test EMIT_*_orth.tiff       -> fig_products (five-panel product figure)
  - docs/figures/data/num_ab.npz   -> fig_muscovite_arbitration (before/after + histogram)
                                      (produced by save_num_maps.py, two-pass protocol of
                                       arbitration_stats.py; flips verified = 63,032)
  - D:/test raw npz / num_ab.npz   -> center histograms
  - cramm bundled splib06b         -> reference spectra (fig_carbonate, fig_chlorite)
  - docs/arbitration_stats.json    -> flip-pair counts

Palette: Okabe-Ito (colorblind-safe), categorical hues in fixed order.
Output: PNG (300 dpi) + PDF for each figure.
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DOCS = "docs/figures"
RAW_NPZ = "D:/test/EMIT_L2A_RFL_001_20220819T061448_2223104_025_raw.npz"
NUM_NPZ = "docs/figures/data/num_ab.npz"
TIFF_DIR = "D:/test"
TIFF_BASE = "EMIT_L2A_RFL_001_20220819T061448_2223104_025"

# Okabe-Ito categorical palette (fixed assignment order, never cycled)
OI = {"blue": "#0072B2", "sky": "#56B4E9", "green": "#009E73",
      "orange": "#E69F00", "vermillion": "#D55E00", "purple": "#CC79A7",
      "yellow": "#F0E442", "black": "#000000"}

MUS_COLORS = {"muscovite_medhighAl": OI["blue"], "muscovite_medAl": OI["sky"],
              "muscovite_lowAl": OI["orange"], "muscovite_Fe-rich": OI["vermillion"]}
MUS_WINDOWS = {"muscovite_medhighAl": (2.195, 2.200), "muscovite_medAl": (2.200, 2.206),
               "muscovite_lowAl": (2.206, 2.210), "muscovite_Fe-rich": (2.210, 2.220)}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 8,
    "axes.linewidth": 0.6,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})


def save(fig, name):
    os.makedirs(DOCS, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(DOCS, f"{name}.{ext}"))
    plt.close(fig)
    print(f"saved {name}.png/.pdf", flush=True)


def get_splib_record(recno):
    """Return (wavelength_um, reflectance) for a splib06b record via the engine."""
    from cramm import MicaEngine
    eng = MicaEngine()
    d = eng.dic3
    row = d[d["irecno"] == recno].iloc[0]
    wv = d[d["irecno"] == row["irwav"]].iloc[0]["data"]
    return np.asarray(wv, float), np.asarray(row["data"], float), str(row["ititl"]).strip()


def continuum_remove(wav, spec, lo, hi):
    """Linear continuum removal between the two window edges (illustration)."""
    m = (wav >= lo) & (wav <= hi) & (spec > 0)
    w, s = wav[m], spec[m]
    hull = s[0] + (s[-1] - s[0]) * (w - w[0]) / (w[-1] - w[0])
    return w, s / hull


# ---------------------------------------------------------------- fig 6: performance
def fig_performance():
    b = json.load(open("docs/benchmark.json", encoding="utf-8"))
    nw, secs, thr = [], [], []
    for label, rate, _ in b["full_scene"]:
        n = int(label.split("n_workers=")[1].split(":")[0])
        s = float(label.split(":")[1].split("s")[0].strip())
        nw.append(n)
        secs.append(s)
        thr.append(float(rate.replace(",", "").split()[0]))
    nw, secs, thr = map(np.array, (nw, secs, thr))

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    ax = axes[0]
    ax.plot(nw, secs[0] / nw, "--", color="#999999", lw=1, label="ideal scaling")
    ax.plot(nw, secs, "o-", color=OI["blue"], lw=1.2, ms=5, label="measured")
    for i, (x, y) in enumerate(zip(nw, secs)):
        ax.annotate(f"{y:.1f} s", (x, y), textcoords="offset points",
                    xytext=(6, -14) if i == 0 else (6, 6), fontsize=7)
    ax.set_xlabel("worker processes")
    ax.set_ylabel("wall time (s)")
    ax.set_xticks(nw)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("a  full-scene wall time", loc="left", fontsize=8)

    ax = axes[1]
    ax.plot(nw, nw.astype(float), "--", color="#999999", lw=1, label="ideal (linear)")
    ax.plot(nw, secs[0] / secs, "o-", color=OI["orange"], lw=1.2, ms=5,
            label="measured speedup")
    for x, y, t in zip(nw, secs[0] / secs, thr):
        ax.annotate(f"{y:.2f}×  ({t:,.0f} px/s)", (x, y),
                    textcoords="offset points", xytext=(6, -12), fontsize=7)
    ax.set_xlabel("worker processes")
    ax.set_ylabel("speedup vs serial")
    ax.set_xticks(nw)
    ax.set_ylim(0, 4.5)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("b  speedup and throughput", loc="left", fontsize=8)

    fig.suptitle("EMIT scene 1280×1242 px (1,589,760 px), 24 logical CPUs, "
                 "serial = 131.73 s", fontsize=7, y=1.04)
    fig.tight_layout()
    save(fig, "fig_performance_scaling")


# ---------------------------------------------------------------- fig 2: products
def fig_products():
    from osgeo import gdal
    panels = [("mapping", "a  mineral map (winner rule)"),
              ("color_enhanced", "b  color-enhanced mineral map"),
              ("mus", "c  muscovite Al-absorption center"),
              ("chl", "d  chlorite Fe/Mg-absorption center"),
              ("cal", "e  carbonate C–O absorption center")]
    imgs = []
    for key, _ in panels:
        ds = gdal.Open(os.path.join(TIFF_DIR, f"{TIFF_BASE}_{key}_orth.tiff"))
        imgs.append(np.dstack([ds.GetRasterBand(i + 1).ReadAsArray()
                               for i in range(3)]))
    h0, w0 = imgs[0].shape[:2]
    imgs = [im if im.shape[:2] == (h0, w0) else im[:h0, :w0] for im in imgs]

    fig, axes = plt.subplots(2, 3, figsize=(7.2, 5.4))
    for ax, (im, (_, title)) in zip(axes.flat, zip(imgs, panels)):
        ax.imshow(im, interpolation="nearest")
        ax.set_title(title, loc="left", fontsize=8)
        ax.set_xticks([]); ax.set_yticks([])
    ax = axes.flat[5]
    ax.axis("off")
    ax.text(0.0, 0.85, "Scene: EMIT_L2A_RFL_001\n_20220819T061448_2223104_025\n"
            "(NASA/JPL L2A reflectance)", fontsize=7, va="top")
    ax.text(0.0, 0.45, "orthorectified products,\n5 thematic maps from one pass\n"
            "(~62 s at 4 workers)", fontsize=7, va="top")
    fig.tight_layout()
    save(fig, "fig_product_panels")


# ------------------------------------------------------ fig 3: muscovite arbitration
def fig_muscovite_arbitration():
    z = np.load(NUM_NPZ, allow_pickle=True)
    num_a, num_b = z["num_a"], z["num_b"]
    mus_c = z["mus_center_a"]
    index = list(z["index"])
    gi = {n: index.index(n) for n in MUS_COLORS}
    stats = json.load(open("docs/arbitration_stats.json", encoding="utf-8"))

    # densest muscovite 300x300 tile for the before/after panels
    win_idx = list(gi.values())
    musmask = np.isin(num_a, win_idx)
    from scipy.ndimage import uniform_filter
    dens = uniform_filter(musmask.astype(float), size=300, mode="constant")
    r0, c0 = np.unravel_index(np.argmax(dens), dens.shape)
    r0 = int(np.clip(r0 - 150, 0, num_a.shape[0] - 300))
    c0 = int(np.clip(c0 - 150, 0, num_a.shape[1] - 300))
    sl = np.s_[r0:r0 + 300, c0:c0 + 300]

    from matplotlib.colors import ListedColormap
    cats = list(MUS_COLORS)          # fixed order
    cmap = ListedColormap(["#111111"] + [MUS_COLORS[n] for n in cats])

    def subtype_img(num):
        img = np.zeros(num.shape, dtype=int)
        for k, n in enumerate(cats):
            img[num == gi[n]] = k + 1
        return img

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.4))

    for ax, num, tag in ((axes[0, 0], num_b, "a  before (pure argmax)"),
                         (axes[0, 1], num_a, "b  after (window arbitration)")):
        ax.imshow(subtype_img(num)[sl], cmap=cmap, vmin=0, vmax=4,
                  interpolation="nearest")
        ax.set_title(tag, loc="left", fontsize=8)
        ax.set_xticks([]); ax.set_yticks([])
    handles = [Rectangle((0, 0), 1, 1, fc=MUS_COLORS[n]) for n in cats]
    labels = [n.replace("muscovite_", "") for n in cats]
    leg = axes[0, 0].legend(handles, labels, frameon=True, fontsize=6.5,
                            loc="lower left", markerscale=0.8, handlelength=1.0)
    leg.get_frame().set_facecolor("white")
    leg.get_frame().set_edgecolor("none")
    leg.get_frame().set_alpha(0.85)
    axes[0, 0].set_title(f"a  before (pure argmax)   [rows {r0}–{r0+300}, "
                         f"cols {c0}–{c0+300}]", loc="left", fontsize=8)

    # (c) center histogram stacked by final subtype, window boundaries overlaid
    ax = axes[1, 0]
    bins = np.arange(2.190, 2.226, 0.0005)
    vals = [mus_c[(num_a == gi[n]) & (mus_c > 0)] for n in cats]
    ax.hist(vals, bins=bins, stacked=True,
            color=[MUS_COLORS[n] for n in cats],
            label=[n.replace("muscovite_", "") for n in cats], lw=0)
    for x in (2.195, 2.200, 2.206, 2.210, 2.220):
        ax.axvline(x, color="k", lw=0.7, ls="--", alpha=0.7)
    ax.set_xlabel("muscovite absorption center (µm)")
    ax.set_ylabel("pixels")
    ax.set_xlim(2.190, 2.226)
    ax.legend(frameon=False, fontsize=6.5, loc="upper left")
    ax.set_title("c  arbitrated center distribution vs windows", loc="left",
                 fontsize=8)

    # (d) flip-pair counts
    ax = axes[1, 1]
    pairs = stats["families"]["muscovite"]["flip_pairs"]
    pairs = sorted(pairs.items(), key=lambda kv: kv[1])
    names = [f"{a.replace('muscovite_', '')} → {b.replace('muscovite_', '')}"
             for a, b in (k.split(" -> ") for k, _ in pairs)]
    counts = [v for _, v in pairs]
    ax.barh(np.arange(len(pairs)), counts, color=OI["blue"], height=0.6)
    ax.set_yticks(np.arange(len(pairs)))
    ax.set_yticklabels(names, fontsize=6.5)
    for i, v in enumerate(counts):
        ax.text(v + max(counts) * 0.01, i, f"{v:,}", va="center", fontsize=6.5)
    ax.set_xlabel("pixels re-attributed (argmax → arbitrated)")
    ax.set_xlim(0, max(counts) * 1.15)
    ax.set_title("d  arbitration flips (46,823 px total)", loc="left", fontsize=8)

    fig.tight_layout()
    save(fig, "fig_muscovite_arbitration")


# ---------------------------------------------------------- fig 5: carbonate
def fig_carbonate():
    z = np.load(RAW_NPZ)
    cal_c = z["cal_center"]

    # documented C-O anchor sequence (lab protocol: ASDNG/NIC4 records, nm)
    anchors = [("magnesite", 2311.3), ("aragonite", 2315.2),
               ("Fe-dolomite", 2319.2), ("dolomite", 2321.2),
               ("siderite (pure)", 2327.0), ("calcite", 2339.4),
               ("rhodochrosite", 2369.0)]
    # the three rule references bundled with CRAMM (splib06b Beckman grid)
    refs = [("calcite WS272 (rec 1751)", 1751, OI["blue"]),
            ("dolomite HS102.3B (rec 2986)", 2986, OI["green"]),
            ("siderite HS271.3B (rec 8623,\nMn-bearing)", 8623, OI["vermillion"])]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2),
                             gridspec_kw={"width_ratios": [1.2, 1]})
    ax = axes[0]
    ax.axvspan(2308, 2328, color=OI["green"], alpha=0.10, zorder=0)
    ax.axvspan(2334, 2350, color=OI["orange"], alpha=0.10, zorder=0)
    for name, x in anchors:
        ax.axvline(x, color="#999999", lw=0.5, ls=":", zorder=0)
        # stagger the two 2-nm-apart labels to avoid collision
        ytop = 2.80 if name == "dolomite" else 3.02
        ax.text(x, ytop, name, rotation=90, fontsize=5.5, ha="center",
                va="top", color="#555555")
    offset = 0.0
    for label, rec, col in refs:
        wav, spec, _ = get_splib_record(rec)
        w, cr = continuum_remove(wav, spec, 2.27, 2.42)
        ax.plot(w * 1000, cr + offset, lw=0.9, color=col)
        m = (w * 1000 >= 2300) & (w * 1000 <= 2385)
        imin = np.flatnonzero(m)[np.argmin(cr[m])]
        cmin = w[imin] * 1000
        ax.plot(cmin, cr[imin] + offset, "v", color=col, ms=4)
        ax.text(2388, offset + 0.42, f"Beckman min {cmin:.1f} nm", fontsize=6,
                ha="right", va="bottom", color=col)
        ax.text(2292, offset + 0.42, label, fontsize=6.5, va="bottom",
                color="#333333")
        offset += 0.7
    ax.text(2318, 2.42, "dolomite\nwindow", ha="center", va="bottom",
            fontsize=6, color=OI["green"])
    ax.text(2342, 2.42, "calcite\nwindow", ha="center", va="bottom",
            fontsize=6, color=OI["orange"])
    ax.set_ylim(0.15, 3.05)
    ax.set_xlim(2290, 2390)
    ax.set_yticks([])
    ax.set_xlabel("wavelength (nm)")
    ax.set_ylabel("continuum-removed reflectance (offset)")
    ax.set_title("a  rule reference spectra vs documented C–O anchor sequence",
                 loc="left", fontsize=8)

    ax = axes[1]
    v = cal_c[cal_c > 0] * 1000.0
    bins = np.arange(2270, 2385, 5)
    ax.hist(v, bins=bins, color=OI["blue"], lw=0)
    ax.axvspan(2308, 2328, color=OI["green"], alpha=0.18)
    ax.axvspan(2334, 2350, color=OI["orange"], alpha=0.18)
    ax.text(2318, ax.get_ylim()[1] * 0.92, "dolomite\nwindow", ha="center",
            fontsize=6.5, color=OI["green"])
    ax.text(2342, ax.get_ylim()[1] * 0.72, "calcite\nwindow", ha="center",
            fontsize=6.5, color=OI["orange"])
    ax.set_xlabel("cal_center (nm), 5 nm bins")
    ax.set_ylabel("pixels")
    ax.set_xlim(2270, 2385)
    ax.set_title("b  scene cal_center distribution", loc="left", fontsize=8)

    fig.tight_layout()
    save(fig, "fig_carbonate_anchors")


# ----------------------------------------------------------- fig 4: chlorite
def fig_chlorite():
    refs = [("chlorite_lowFe  SMR-13.a (rec 2047)", 2047, OI["green"]),
            ("clinochlore  GDS158 (rec 2253)", 2253, OI["blue"]),
            ("clinochlore_Fe  SC-CCa-1.a (rec 2371)", 2371, OI["vermillion"]),
            ("thuringite  SMR-15.c (rec 9262)", 9262, OI["purple"])]
    windows = [("chlorite_lowFe", 2.245, 2.248, OI["green"]),
               ("clinochlore", 2.248, 2.252, OI["blue"]),
               ("clinochlore_Fe", 2.252, 2.256, OI["vermillion"]),
               ("thuringite", 2.256, 2.266, OI["purple"])]

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.8),
                             gridspec_kw={"width_ratios": [1.25, 1, 0.95]})
    ax = axes[0]
    offset = 0.0
    short = {2047: "SMR-13.a (low-Fe)", 2253: "GDS158",
             2371: "SC-CCa-1.a (Fe-rich)", 9262: "SMR-15.c (thuringite)"}
    for label, rec, col in refs:
        wav, spec, _ = get_splib_record(rec)
        w, cr = continuum_remove(wav, spec, 2.20, 2.40)
        ax.plot(w * 1000, cr + offset, lw=0.9, color=col)
        # mark the 2250 nm Fe/Mg band minimum (the arbitrated feature)
        m = (w * 1000 >= 2235) & (w * 1000 <= 2270)
        imin = np.flatnonzero(m)[np.argmin(cr[m])]
        ax.plot(w[imin] * 1000, cr[imin] + offset, "v", color=col, ms=4)
        ax.text(2396, (cr + offset)[-1] + 0.05, short[rec], ha="right",
                va="bottom", fontsize=6.5, color=col)
        offset += 0.6
    for _, lo, hi, col in windows:
        ax.axvspan(lo * 1000, hi * 1000, color=col, alpha=0.12)
    ax.set_xlabel("wavelength (nm)")
    ax.set_ylabel("continuum-removed reflectance (offset)")
    ax.set_xlim(2200, 2400)
    ax.set_ylim(0.45, 3.2)
    ax.set_title("a  rule reference spectra\n(markers: 2250 nm band min)",
                 loc="left", fontsize=8)

    # (b) window topology schematic: seamless tiling, deterministic arbitration
    ax = axes[1]
    y = 0.0
    for name, lo, hi, col in windows:
        ax.barh(y, (hi - lo) * 1000, left=lo * 1000, height=0.55,
                color=col, alpha=0.75, edgecolor="none")
        ax.text(lo * 1000 - 0.6, y, name.replace("chlorite_", "chl_"),
                ha="right", va="center", fontsize=6.5)
        y += 1.0
    for seam in (2.248, 2.252, 2.256):
        ax.axvline(seam * 1000, color="#555555", lw=0.6, ls=":")
    ax.annotate("seamless tiling:\nevery in-range center hits\nexactly one window",
                xy=(2252.0, 1.5), xytext=(2257.5, 1.5), fontsize=6.5,
                arrowprops=dict(arrowstyle="->", lw=0.6))
    ax.set_xlim(2240, 2268)
    ax.set_ylim(-1.0, 3.8)
    ax.set_yticks([])
    ax.set_xlabel("Fe/Mg absorption center (nm)")
    ax.set_title("b  tiling arbitration windows", loc="left", fontsize=8)

    # (c) chl13 calibration: measured vs closed-form model pos2250
    import pandas as pd
    ax = axes[2]
    df = pd.read_csv("docs/figures/data/chl13_features.csv")
    pred = 2218.8 * df.xAl + 2279.6 * df.xFe + 2249.7 * df.xMg
    rmse = float(np.sqrt(((df.pos2250 - pred) ** 2).mean()))
    lim = (2242, 2262)
    ax.plot(lim, lim, "--", color="#999999", lw=0.8)
    ax.plot(pred, df.pos2250, "o", color=OI["blue"], ms=4, mew=0)
    for s, x, y in zip(df.sid, pred, df.pos2250):
        if s in ("SMR-13", "GDS158", "CCa-1", "SMR-15"):
            off = (-38, -2) if s == "SMR-15" else (4, 4)  # SMR-15: top-right corner, keep inside axes
            ax.annotate(s, (x, y), textcoords="offset points", xytext=off,
                        fontsize=6, color="#555555")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("model pos2250 (nm)")
    ax.set_ylabel("measured pos2250 (nm)")
    ax.text(0.04, 0.96, "pos2250 = 2218.8·xAl\n+ 2279.6·xFe + 2249.7·xMg\n"
            f"chl13 RMSE {rmse:.2f} nm (LOO 1.0 nm)",
            transform=ax.transAxes, fontsize=6.5, va="top")
    ax.set_title("c  chl13 calibration (13 samples)", loc="left", fontsize=8)

    fig.tight_layout()
    save(fig, "fig_chlorite_windows")


# ------------------------------------------------------- fig 1: scene location
def fig_location():
    """Footprint from the granule's own geolocation arrays (no external data).

    NOTE: a full basemap (coastlines/borders) requires online Natural Earth
    data, which was unreachable at generation time; the footprint below is
    drawn from the L2A product's per-pixel lon/lat fields and is exact.
    """
    from cramm import MicaEngine
    eng = MicaEngine()
    _, lon, lat, *_ = eng.load_emit(
        "./EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc")
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    step = 8
    edge = (list(zip(lon[0, ::step], lat[0, ::step]))
            + list(zip(lon[::step, -1], lat[::step, -1]))
            + list(zip(lon[-1, ::-step], lat[-1, ::-step]))
            + list(zip(lon[::-step, 0], lat[::-step, 0])))
    ex, ey = zip(*edge)

    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    ax.fill(ex, ey, color=OI["orange"], alpha=0.45, zorder=3)
    ax.plot(ex, ey, color=OI["vermillion"], lw=1.2, zorder=4)
    for name, i, j, dx, dy, ha in (("W", 0, 0, 8, -4, "left"),
                                   ("N", 0, -1, -8, 8, "right"),
                                   ("E", -1, -1, -8, -6, "right"),
                                   ("S", -1, 0, 8, -14, "left")):
        ax.annotate(f"{name} {lat[i,j]:.3f}°N, {lon[i,j]:.3f}°E",
                    (lon[i, j], lat[i, j]), textcoords="offset points",
                    xytext=(dx, dy), ha=ha, fontsize=6, color="#333333")
    ax.set_xlim(98.4, 100.9)
    ax.set_ylim(40.1, 42.0)
    ax.set_xlabel("longitude (°E)")
    ax.set_ylabel("latitude (°N)")
    ax.set_aspect(1.0 / np.cos(np.deg2rad(41.0)))
    ax.grid(True, lw=0.3, color="#cccccc")
    ax.set_title("EMIT_L2A_RFL_001_20220819T061448_2223104_025\nfootprint "
                 "(from L2A geolocation arrays; Gobi Desert,\n"
                 "China–Mongolia border region, ~99.65°E 41.03°N)",
                 fontsize=7)
    fig.tight_layout()
    save(fig, "fig_scene_location")


if __name__ == "__main__":
    fig_performance()
    fig_products()
    fig_muscovite_arbitration()
    fig_carbonate()
    fig_chlorite()
    fig_location()
    print("all figures done", flush=True)
