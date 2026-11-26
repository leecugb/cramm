#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export and plot one representative CRAMM mixture-attribution error."""
import csv
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = "SYN02031"
OUT = Path(os.environ.get("CRAMM_SPECTRUM_OUT", ROOT / f"output/misclassified_{SAMPLE}"))
SKILL = Path.home() / ".claude/skills/nature-figure/scripts"
import sys
sys.path.insert(0, str(SKILL))
from audit_panel_alignment import require_matplotlib_panel_alignment  # noqa: E402


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if any(OUT.iterdir()):
        raise SystemExit(f"Output directory must be empty: {OUT}")
    data = np.load(ROOT / "output/synthetic_emit_lowfreq_extended_v1/spectra.npz", allow_pickle=False)
    i = list(data["sample_id"]).index(SAMPLE)
    w = data["band_centers_um"]
    bp = data["fwhm_um"]
    valid = data["valid_mask"][i]
    observed = data["reflectance"][i]
    clean = data["noise_free_reflectance"][i]
    refs = data["reference_sensor_spectra"]
    rules = list(data["reference_rules"])
    mus = refs[rules.index("muscovite_medAl")]
    kao = refs[rules.index("kaolinite_wxl")]

    with (OUT / "spectrum.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["band_index", "wavelength_um", "fwhm_um", "valid",
                         "observed_reflectance", "noise_free_reflectance",
                         "muscovite_medAl_reference", "kaolinite_wxl_reference"])
        for j in range(len(w)):
            writer.writerow([j, w[j], bp[j], int(valid[j]), observed[j], clean[j], mus[j], kao[j]])

    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
        "font.size": 8, "axes.linewidth": 0.8, "pdf.fonttype": 42,
        "svg.fonttype": "none",
    })
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.8))
    fig.patch.set_facecolor("white")
    colors = {"observed": "#2a78d6", "clean": "#202020",
              "mus": "#e68632", "kao": "#508c49"}
    for ax, title, xlim in zip(
        axes, ["Reflectance: full spectrum", "Reflectance: diagnostic SWIR region"],
        [(0.35, 2.50), (2.05, 2.45)]
    ):
        ax.plot(w[valid], observed[valid], ".", ms=3.2, color=colors["observed"],
                label="Observed (25 dB, low-frequency)", zorder=3)
        ax.plot(w[valid], clean[valid], "-", lw=1.4, color=colors["clean"],
                label="Noise-free same condition", zorder=4)
        ax.plot(w, mus, "--", lw=1.0, color=colors["mus"], label="Muscovite medAl reference")
        ax.plot(w, kao, "-.", lw=1.0, color=colors["kao"], label="Kaolinite WXL reference")
        ax.set_xlim(*xlim)
        ax.set_xlabel("Wavelength (µm)")
        ax.set_title(title, loc="left", fontsize=9)
        ax.tick_params(labelsize=7, length=3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].text(-0.14, 1.04, "a", transform=axes[0].transAxes,
                 fontsize=10, fontweight="bold")
    axes[1].text(-0.14, 1.04, "b", transform=axes[1].transAxes,
                 fontsize=10, fontweight="bold")
    axes[1].legend(loc="upper right", fontsize=6.5, frameon=False)
    fig.suptitle(
        "SYN02031: 75% muscovite medAl + 25% kaolinite WXL\n"
        "M00 correct mixture components → M10 pure muscovite medAl; "
        "ratios 0.4784 ≥ 0.4 and 0.4950 < 0.6",
        fontsize=9.5, y=0.995,
    )
    fig.subplots_adjust(left=0.07, right=0.985, top=0.76, bottom=0.15, wspace=0.24)
    require_matplotlib_panel_alignment(
        fig, axes=list(axes), row_groups=[["a", "b"]],
        json_out=str(OUT / "panel_alignment.json"),
        overlay_svg=str(OUT / "panel_alignment.svg"),
        tolerance_pt=1.5, gutter_tolerance_pt=1.5,
        require_panel_labels=True, strict=True,
    )
    fig.savefig(OUT / "spectrum.png", dpi=300)
    fig.savefig(OUT / "spectrum.pdf")
    plt.close(fig)

    readme = """# Misclassified spectrum SYN02031

Truth: 75% `muscovite_medAl` + 25% `kaolinite_wxl`, low-frequency 25 dB,
continuum slope +0.1 per µm.

- M00 (depth ratio off): `kaolinite.5+muscoviteMedAl.5`, correct family component set.
- M10 (depth ratio on): `muscovite_medAl`, incorrect pure-white-mica attribution.
- Kaolinite–muscovite mixture-rule ratio: 0.4783627888 >= 0.4, so that mixture rule is rejected.
- Remaining pure-medAl ratio: 0.4949975783 < 0.6, so pure medAl remains accepted and wins.

This is a reference-derived synthetic development example, not an independent
geological validation spectrum. `spectrum.csv` preserves all 285 bands, valid
mask, observed/noise-free spectra and both source references.

Threshold-version note (2026-11-20): this example documents the former 0.4
kaolinite–muscovite threshold. At the current 0.55 threshold, the mixture rule
is retained and SYN02031 returns to `kaolinite.5+muscoviteMedAl.5`.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
