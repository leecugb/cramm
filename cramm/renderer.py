#!/usr/bin/env python
# coding: utf-8
"""
MICA result packaging
=====================
Consumes a ClassificationResult (raw classification output) plus a color
table, produces three RGB images (orth_rgb / color_enhanced / mus_image),
and writes GeoTIFFs.

Decoupled from spectral analysis and image reading: this module performs no
mineral discrimination; it is responsible only for rendering and output.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import numpy as np

from .classifier import ClassificationResult


# =============================================================================
# Default 10-level color table for the muscovite mus_image (hardcoded; used
# when color_tif_path=None). Colored in order of mus_center from short to long
# (high-Al -> low-Al/illite): red -> yellow -> green -> cyan -> blue
# =============================================================================
DEFAULT_MUS_TABLE: List[np.ndarray] = [
    np.array([255,  30,   0], dtype=np.uint8),
    np.array([255, 115,   0], dtype=np.uint8),
    np.array([255, 191,   0], dtype=np.uint8),
    np.array([251, 255,  25], dtype=np.uint8),
    np.array([207, 255, 110], dtype=np.uint8),
    np.array([143, 255, 186], dtype=np.uint8),
    np.array([ 15, 251, 255], dtype=np.uint8),
    np.array([ 59, 167, 255], dtype=np.uint8),
    np.array([ 54,  94, 255], dtype=np.uint8),
    np.array([  8,   8, 255], dtype=np.uint8),
]


# =============================================================================
# HSI color space conversion (for the depth-enhanced image)
# =============================================================================

def _rgb2hsi(rgb: np.ndarray) -> np.ndarray:
    r = rgb[:, 0]
    g = rgb[:, 1]
    b = rgb[:, 2]
    num = 0.5 * ((r - g) + (r - b))
    den = np.sqrt((r - g) ** 2 + (r - b) * (g - b))
    theta = np.arccos(num / (den + np.finfo(float).eps))
    H = theta
    H[b > g] = 2 * np.pi - H[b > g]
    H = H / (2 * np.pi)
    num = rgb.min(1)
    den = r + g + b
    den[den == 0] = np.finfo(float).eps
    S = 1 - 3 * num / den
    H[S == 0] = 0
    I = (r + g + b) / 3
    return np.vstack([H, S, I]).T


def _hsi2rgb(hsi: np.ndarray) -> np.ndarray:
    H = hsi[:, 0] * 2 * np.pi
    S = hsi[:, 1]
    I = hsi[:, 2]
    R = np.zeros(len(hsi))
    G = np.zeros(len(hsi))
    B = np.zeros(len(hsi))
    mask = (0 <= H) & (H < 2 * np.pi / 3)
    B[mask] = I[mask] * (1 - S[mask])
    R[mask] = I[mask] * (1 + S[mask] * np.cos(H[mask]) / np.cos(np.pi / 3 - H[mask]))
    G[mask] = 3 * I[mask] - (R[mask] + B[mask])
    mask = (2 * np.pi / 3 <= H) & (H < 4 * np.pi / 3)
    R[mask] = I[mask] * (1 - S[mask])
    G[mask] = I[mask] * (1 + S[mask] * np.cos(H[mask] - 2 * np.pi / 3) / np.cos(np.pi - H[mask]))
    B[mask] = 3 * I[mask] - (R[mask] + G[mask])
    mask = (4 * np.pi / 3 <= H) & (H <= 2 * np.pi)
    G[mask] = I[mask] * (1 - S[mask])
    B[mask] = I[mask] * (1 + S[mask] * np.cos(H[mask] - 4 * np.pi / 3) / np.cos(5 * np.pi / 3 - H[mask]))
    R[mask] = 3 * I[mask] - (G[mask] + B[mask])
    rgb = np.vstack([R, G, B]).T
    rgb[rgb > 1] = 1
    rgb[rgb < 0] = 0
    return rgb


# =============================================================================
# ResultRenderer: result packaging
# =============================================================================

class ResultRenderer:
    """
    Renders raw classification results into RGB images and writes GeoTIFFs.

    Parameters
    ----------
    colors_dic : dict
        Mineral name -> (R, G, B) uint8 color.
    table : list[np.ndarray]
        Muscovite 10-level color table (for binned coloring by mus_center).
    """

    def __init__(self, colors_dic: Dict[str, Tuple[int, int, int]], table: List[np.ndarray]):
        self.colors_dic = colors_dic
        self.table = table

    @classmethod
    def from_paths(cls, color_txt_path: Optional[str] = None, color_tif_path: Optional[str] = None) -> "ResultRenderer":
        """
        Loads color tables from paths and constructs the renderer (self-contained).

        Parameters
        ----------
        color_txt_path : str, optional
            Path to the mineral RGB color table text file.
            If None, uses the built-in color_table.json packaged with the library
            (same level as rf.json, at the library root).
        color_tif_path : str, optional
            Path to the color lookup table (GeoTIFF) for the muscovite thematic map.
            If None, uses the built-in DEFAULT_MUS_TABLE (no longer depends on color.tif).
        """
        from pathlib import Path
        import json

        if color_txt_path is None:
            # Built-in packaged color_table.json (cramm/data/)
            color_txt_path = Path(__file__).parent / "data" / "color_table.json"
        txt_p = Path(color_txt_path)
        if not txt_p.exists():
            raise FileNotFoundError(f"{color_txt_path} not found.")
        data = json.loads(txt_p.read_text(encoding="utf-8"))
        colors_dic: Dict[str, Tuple[int, int, int]] = {k: tuple(v) for k, v in data.items()}

        if color_tif_path is None:
            # Built-in default color table (hardcoded, no color.tif needed)
            table = [t.copy() for t in DEFAULT_MUS_TABLE]
        else:
            from osgeo import gdal
            tif_p = Path(color_tif_path)
            if not tif_p.exists():
                raise FileNotFoundError(f"{tif_p} not found.")
            ds = gdal.Open(str(tif_p))
            if ds is None:
                raise RuntimeError(f"Failed to open {tif_p}")
            color = ds.ReadAsArray()
            # linspace(0, 282, 10) -> 10 sampling indices
            indices = np.linspace(0, 282, 10).astype(int)
            table = [color[:, 0, i] for i in indices]

        return cls(colors_dic, table)

    def render(self, result: ClassificationResult) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Renders the three RGB images.

        Returns
        -------
        orth_rgb, color_enhanced, mus_image : np.ndarray
            All are [r, c, 3] uint8
        """
        r, c = result.r, result.c
        index = result.index
        index_d = result.index_d
        # Upfront color table completeness check: if a custom rule library introduces
        # new minerals missing colors, fail here immediately — instead of hitting a
        # KeyError at the table lookup below after a full-scene classify run
        missing = [n for n in index if n not in self.colors_dic]
        if missing:
            raise KeyError(f"color table is missing {len(missing)} minerals: {missing}")
        # Prebuild the mineral->color lookup table for vectorized coloring
        # (replaces per-pixel Python loops)
        color_array = np.array([self.colors_dic[n] for n in index], dtype="uint8")

        # ---- Orth RGB (hard classification) ----
        orth_rgb = color_array[result.num]
        orth_rgb[result.fit == 0] = [0, 0, 0]

        # ---- Color Enhanced (depth modulation) ----
        mask = result.fit > 0
        color_enhanced = np.zeros([r * c, 3], dtype="uint8")
        # Locate groups by mineral in one pass (stable argsort), replacing 77 full-N
        # mask scans; within a group pixels keep ascending original row order
        # (guaranteed by stable sort), so per-group math matches the original
        # element-by-element loop -> bit-exact.
        alive = np.nonzero(mask)[0]
        num_a = result.num[alive]
        order = np.argsort(num_a, kind="stable")
        sorted_num = num_a[order]
        bounds = np.flatnonzero(np.diff(sorted_num)) + 1
        starts = np.concatenate(([0], bounds))
        ends = np.concatenate((bounds, [len(alive)]))
        for g in range(len(starts)):
            s0, e0 = starts[g], ends[g]
            if s0 == e0:
                continue  # no surviving pixels (original mask1.any() guard)
            rows_g = alive[order[s0:e0]]
            i = index[sorted_num[s0]]
            dep = result.depth[rows_g]
            dep = np.log(dep)
            denom = dep.max() - dep.min()
            if denom == 0:
                hsi = _rgb2hsi((np.array(self.colors_dic[i]) / 255).reshape([-1, 3]))[0]
                color_enhanced[rows_g] = np.tile(
                    _hsi2rgb(hsi.reshape([1, 3])) * 255, (len(rows_g), 1)
                )
                continue
            dep = (dep - dep.min()) / denom
            hsi = _rgb2hsi((np.array(self.colors_dic[i]) / 255).reshape([-1, 3]))[0]
            dep = dep * hsi[-1] / 3 + hsi[-1] * 2 / 3
            im_arr = np.zeros([len(rows_g), 3])
            im_arr[:, 0] = hsi[0]
            im_arr[:, 1] = hsi[1]
            im_arr[:, 2] = dep
            color_enhanced[rows_g] = _hsi2rgb(im_arr) * 255

        # ---- Muscovite (muscovite thematic map) ----
        # Binning thresholds are an algorithmic contract (inherited from mica_app):
        # the mus_center absorption center wavelength within [2.195, 2.226) um is
        # binned into 10 levels at ~0.001 um steps (shorter wavelength = high-Al ->
        # longer wavelength = low-Al/illite); out-of-range pixels are colored black
        # (including non-muscovite pixels with mus_center=0)
        mus_center = result.mus_center
        mus_image = np.zeros([r * c, 3], dtype="uint8")
        mus_image[mus_center < 2.199] = self.table[0]
        mus_image[(mus_center >= 2.199) & (mus_center < 2.2)] = self.table[1]
        mus_image[(mus_center >= 2.2) & (mus_center < 2.201)] = self.table[2]
        mus_image[(mus_center >= 2.201) & (mus_center < 2.202)] = self.table[3]
        mus_image[(mus_center >= 2.202) & (mus_center < 2.203)] = self.table[4]
        mus_image[(mus_center >= 2.203) & (mus_center < 2.204)] = self.table[5]
        mus_image[(mus_center >= 2.204) & (mus_center < 2.205)] = self.table[6]
        mus_image[(mus_center >= 2.205) & (mus_center < 2.206)] = self.table[7]
        mus_image[(mus_center >= 2.206) & (mus_center < 2.207)] = self.table[8]
        mus_image[mus_center >= 2.207] = self.table[9]
        mus_image[mus_center < 2.195] = [0, 0, 0]
        mus_image[mus_center >= 2.226] = [0, 0, 0]

        return (
            orth_rgb.reshape([r, c, 3]),
            color_enhanced.reshape([r, c, 3]),
            mus_image.reshape([r, c, 3]),
        )

    @staticmethod
    def write_tiff(
        pathname: str,
        lon: np.ndarray,
        lat: np.ndarray,
        orth_rgb: np.ndarray,
        color_enhanced: np.ndarray,
        mus_image: np.ndarray,
    ) -> None:
        """Handles coordinate resampling and GeoTIFF file saving."""
        from osgeo import gdal
        from pyproj import Proj
        from pyresample import geometry, kd_tree

        name = os.path.splitext(os.path.split(pathname)[1])[0]
        folder = os.path.split(pathname)[0]
        # Create the output directory upfront: osgeo does not enable UseExceptions
        # by default, so Create silently returns None when the directory does not
        # exist, and the later SetMetadataItem would raise a context-free AttributeError
        if folder:
            os.makedirs(folder, exist_ok=True)
        # Standard UTM zoning: floor((lon+180)/6)+1 (the original ceil(lon/6)+30 is
        # off by one zone when lon is an exact multiple of 6, e.g. 114 deg -> 49
        # instead of 50); southern-hemisphere scenes need +south (EMIT global coverage).
        zone = min(60, max(1, int(np.floor((lon.mean() + 180) / 6) + 1)))  # clamp: lon=+/-180 boundary
        south = " +south" if lat.mean() < 0 else ""
        proj_str = f"+proj=utm +zone={zone}{south} +datum=WGS84 +units=m +no_defs"

        p = Proj(proj_str)
        extent = [*p(lon.min(), lat.min()), *p(lon.max(), lat.max())]
        area_def = geometry.AreaDefinition(
            "areaD",
            "custom",
            "areaD",
            proj_str,
            int((extent[2] - extent[0]) / 60),
            int((extent[3] - extent[1]) / 60),
            extent,
        )
        swath_def = geometry.SwathDefinition(lons=lon, lats=lat)

        driver = gdal.GetDriverByName("GTiff")

        def _save(arr: np.ndarray, suffix: str) -> None:
            result = kd_tree.resample_nearest(swath_def, arr, area_def, radius_of_influence=90)
            r1, c1, _ = result.shape
            out_path = os.path.join(folder, name + suffix)
            raster = driver.Create(out_path, c1, r1, 3, gdal.GDT_Byte)
            if raster is None:
                raise RuntimeError(f"cannot create output file {out_path}")
            raster.SetMetadataItem("AREA_OR_POINT", "Point")
            raster.SetGeoTransform((extent[0], 60, 0, extent[-1], 0, -60))
            raster.SetProjection(proj_str)
            for i in range(3):
                raster.GetRasterBand(i + 1).WriteArray(result[:, :, i])
                raster.FlushCache()
            raster = None

        _save(orth_rgb, "_mapping_orth.tiff")
        _save(color_enhanced, "_color_enhanced_orth.tiff")
        _save(mus_image, "_mus_orth.tiff")

    # ------------------------------------------------------------------
    # Single-spectrum feature continuum-removal PDF (lazy matplotlib import)
    # ------------------------------------------------------------------

    @staticmethod
    def plot_features_pdf(
        results: list,
        rf: dict,
        spectrum1: np.ndarray,
        wl: np.ndarray,
        resampled1: dict,
        chanels: np.ndarray,
        pdf_path: str,
    ) -> None:
        """
        Generates a multi-page PDF for the top-N results of classify_spectrum.
        One mineral per page, with continuum-removal plots of all diagnostic/
        non-features plus k0/k1/r2/depth, constraint parameters, and depth ratios.

        Parameters
        ----------
        results : list[dict]
            Return value of classify_spectrum [{"name":..., "fit":..., "fd":...}, ...].
        rf : dict
            Mineral rule library (clf.rf).
        spectrum1 : np.ndarray
            Input spectrum [1, n_chanels].
        wl, chanels : np.ndarray
            Valid-band wavelengths / indices.
        resampled1 : dict
            Resampled reference spectra (return value of clf.get_resample).
        pdf_path : str
            Output PDF path.
        """
        import math
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages

        # rc_context: parameters take effect only during PDF generation and are
        # restored on exit — avoids polluting process-level global rcParams (in a
        # GUI embedding matplotlib, an unrestored rcParams.update would change the
        # style of all subsequent plots)
        _rc = {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.size": 7, "axes.titlesize": 8, "axes.labelsize": 7, "axes.linewidth": 0.6,
            "axes.spines.right": False, "axes.spines.top": False,
            "xtick.direction": "out", "ytick.direction": "out",
            "xtick.major.size": 2.5, "ytick.major.size": 2.5,
            "xtick.labelsize": 6, "ytick.labelsize": 6,
            "pdf.fonttype": 42, "svg.fonttype": "none", "figure.dpi": 100,
        }
        DIAG_COLOR = "#0173B2"; NOT_ABS_COLOR = "#C41E3A"; NOT_REL_COLOR = "#6A3D9A"; REF_COLOR = "#DE8F05"

        # Note: _compute_feature is an **independent third implementation** of the
        # continuum-removal math (single-spectrum scalar version, visualization only,
        # not subject to bit-exactness constraints). If the classifier's algorithm
        # evolves, this must be manually synchronized — otherwise the diagnostic plots
        # would no longer describe the real computation.
        def _compute_feature(spectrum1, reference, wl, endpoints):
            mask = (wl <= endpoints[3]) & (wl >= endpoints[0]) & (~np.isnan(reference))
            mle = (wl <= endpoints[1]) & (wl >= endpoints[0])
            mre = (wl <= endpoints[3]) & (wl >= endpoints[2])
            if not mask.any() or not mle.any() or not mre.any():
                return None
            x_av = np.array([wl[mle].mean(), wl[mre].mean()], dtype='float64')
            y_av = np.array([spectrum1[:, mle].mean(1), spectrum1[:, mre].mean(1)], dtype='float64').T
            rl, rr = reference[mle], reference[mre]
            yrav = np.array([rl[~np.isnan(rl)].mean(), rr[~np.isnan(rr)].mean()], dtype='float64')
            con_sp = y_av[0, 0] + (y_av[0, 1] - y_av[0, 0]) / (x_av[1] - x_av[0]) * (wl[mask] - x_av[0])
            con_ref = yrav[0] + (yrav[1] - yrav[0]) / (x_av[1] - x_av[0]) * (wl[mask] - x_av[0])
            con = spectrum1[0, mask] / con_sp
            con_ = reference[mask] / con_ref
            n = len(con_); Scc = np.dot(con_, con_); Sc = con_.sum()
            det = Scc * n - Sc * Sc
            if det == 0:
                return {'wl': wl[mask], 'con': con, 'con_': con_, 'k0': np.nan, 'k1': np.nan, 'r2': np.nan, 'depth': np.nan}
            B0 = (n * con_ - Sc) / det; B1 = (Scc - Sc * con_) / det
            k0 = float(B0.dot(con)); k1 = float(B1.dot(con))
            if k0 > 0:
                y_fit = k0 * con_ + k1
                ss_reg = ((y_fit - con.mean()) ** 2).sum(); ss_tot = ((con - con.mean()) ** 2).sum()
                r2 = ss_reg / ss_tot if ss_tot > 0 else np.nan
                depth = (1 - con_.min()) * k0 if con_.mean() < 1 else (con_.max() - 1) * k0
            else:
                r2 = np.nan; depth = np.nan
            return {'wl': wl[mask], 'con': con, 'con_': con_, 'k0': k0, 'k1': k1, 'r2': r2, 'depth': depth}

        def _plot_feature(ax, info, ftype, endpoints, constraints, weight=None):
            if info is None:
                ax.text(0.5, 0.5, 'Invalid range', transform=ax.transAxes, ha='center', va='center', color='red'); return
            color = DIAG_COLOR if ftype == 'diagnostic' else (NOT_ABS_COLOR if ftype == 'not_abs' else NOT_REL_COLOR)
            prefix = 'Diagnostic' if ftype == 'diagnostic' else ('Not-abs' if ftype == 'not_abs' else 'Not-rel')
            ax.plot(info['wl'], info['con_'], 's-', color=REF_COLOR, markersize=3, label='Reference con_', linewidth=1.0)
            ax.plot(info['wl'], info['con'], 'o-', color=color, markersize=3, label='Input con', linewidth=1.0)
            ax.axhline(1.0, color='gray', linewidth=0.5, linestyle='--', zorder=0)
            ax.axvspan(endpoints[1], endpoints[2], alpha=0.08, color='gray', zorder=0)
            ax.set_title(f"{prefix}: [{', '.join(map(str, endpoints))}] um", fontsize=7, loc='left')
            ax.set_xlabel('Wavelength (um)', fontsize=6); ax.set_ylabel('Continuum-removed', fontsize=6)
            ax.legend(fontsize=5.5, loc='best'); ax.tick_params(labelsize=5.5); ax.grid(False)
            lines = [f"k0={info['k0']:.4f}, k1={info['k1']:.4f}", f"r2={info['r2']:.4f}, depth={info['depth']:.4f}"]
            if weight is not None: lines.append(f"weight={weight:.2f}")
            if 'fit_constraint' in constraints: lines.append(f"fit>={constraints['fit_constraint']}")
            if 'depth_constraints' in constraints and constraints['depth_constraints']: lines.append(f"depth in {constraints['depth_constraints']}")
            if 'absolute_depth_constraint' in constraints: lines.append(f"abs_depth>={constraints['absolute_depth_constraint']}")
            if 'relative_depth_threshold' in constraints: lines.append(f"rel_th={constraints['relative_depth_threshold']:.4f}")
            if 'relative_depth_value' in constraints: lines.append(f"rel_depth>={constraints['relative_depth_value']:.4f}")
            ax.text(0.97, 0.97, '\n'.join(lines), transform=ax.transAxes, va='top', ha='right', fontsize=5.5,
                    bbox=dict(boxstyle='round', facecolor='white', edgecolor=color, alpha=0.8))

        with mpl.rc_context(_rc):
            with PdfPages(pdf_path) as pdf:
                for r in results:
                    name = r["name"]; rule = rf[name]
                    features = []; diag_depths = []
                    for feat in rule.get("diagnostic_features", []):
                        ref = resampled1[rule["reference"]["reflectance_record"]][chanels]
                        info = _compute_feature(spectrum1, ref, wl, feat["continuum_endpoints"])
                        diag_depths.append(info["depth"] if info else np.nan)
                        features.append({"info": info, "type": "diagnostic", "endpoints": feat["continuum_endpoints"],
                                         "constraints": {"fit_constraint": feat["fit_constraint"], "depth_constraints": feat["depth_constraints"]},
                                         "weight": feat["feature_weight"]})
                    d1 = diag_depths[0] if diag_depths else np.nan
                    for feat in rule.get("not_absolute_features", []):
                        if feat["reflectance_record"] not in resampled1: continue
                        ref = resampled1[feat["reflectance_record"]][chanels]
                        info = _compute_feature(spectrum1, ref, wl, feat["continuum_endpoints"])
                        features.append({"info": info, "type": "not_abs", "endpoints": feat["continuum_endpoints"],
                                         "constraints": {"fit_constraint": feat["fit_constraint"], "absolute_depth_constraint": feat["absolute_depth_constraint"]}})
                    for feat in rule.get("not_relative_features", []):
                        if feat["reflectance_record"] not in resampled1: continue
                        ref = resampled1[feat["reflectance_record"]][chanels]
                        info = _compute_feature(spectrum1, ref, wl, feat["continuum_endpoints"])
                        features.append({"info": info, "type": "not_rel", "endpoints": feat["continuum_endpoints"],
                                         "constraints": {"fit_constraint": feat["fit_constraint"],
                                                         "relative_depth_threshold": feat["relative_depth_threshold"],
                                                         "relative_depth_value": d1 * feat["relative_depth_threshold"] if not np.isnan(d1) else np.nan}})
                    n = len(features); cols = 3; rows = math.ceil(n / cols)
                    fig, axes = plt.subplots(rows, cols, figsize=(10, 3.2 * rows))
                    # cols is always 3 -> subplots always returns an Axes array (even when
                    # n==1); atleast_1d keeps compatibility with a future cols==1 case
                    # degenerating to a single Axes
                    axes = np.atleast_1d(axes).flatten()
                    for ax, feat in zip(axes, features):
                        _plot_feature(ax, feat["info"], feat["type"], feat["endpoints"], feat["constraints"], feat.get("weight"))
                    for ax in axes[n:]: ax.axis("off")
                    # Depth ratio constraint info
                    ratio_text = ""
                    _ratio_max = rule.get("max_depth_ratio_feat1_over_feat0")
                    if _ratio_max is not None and len(diag_depths) >= 2:
                        _d0, _d1 = diag_depths[0], diag_depths[1]
                        if not np.isnan(_d0) and _d0 > 0 and not np.isnan(_d1):
                            _ratio = _d1 / _d0
                            _status = "PASS" if _ratio < _ratio_max else "REJECT"
                            ratio_text = f"\nd1/d0={_ratio:.3f}  (threshold <{_ratio_max})  -> {_status}"
                        elif np.isnan(_d1):
                            ratio_text = f"\nd1/d0=N/A  (diag1 failed, skip ratio check)"
                    fig.suptitle(f"{name}\nMICA fit={r['fit']:.4f}, features={n}{ratio_text}", fontsize=9, fontweight="bold", y=0.98)
                    fig.tight_layout(rect=[0, 0, 1, 0.94])
                    pdf.savefig(fig, dpi=300); plt.close(fig)
            plt.close("all")
