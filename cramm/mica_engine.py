#!/usr/bin/env python
# coding: utf-8
"""
MICA core engine — zero GUI dependencies (facade)
=================================================
Composes three decoupled components while preserving the original public API:
    - EmitReader      (image reading, cramm/emit_reader.py)
    - MicaClassifier  (spectral analysis core, cramm/classifier.py)
    - ResultRenderer  (result packaging, cramm/renderer.py)

This module is only responsible for resource loading and component composition;
it contains no algorithm/rendering implementation. The desktop GUI,
verify_optimize.py, test_engine.py, and __main__ all access the package
through this facade.

Algorithm documentation:
    - algorithm_walkthrough.md   — concise overview of the current state
    - algorithm_deep_analysis.md — in-depth analysis of the math / three-tier
                                   filtering / constraint statistics / numerical stability

How to verify:
    python test_parallel.py 4|1    # full-scene golden regression (parallel/serial, bit-exact)
    python check_rows_logic.py     # 14 checks of rows surviving-pixel semantics
    python check_compiled_path.py  # compiled/direct path 302x77 bit-exact diff
    python -m cramm.mica_engine -i <nc> [-o dir] [--raw]  # end-to-end CLI
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from .classifier import MicaClassifier
from .emit_reader import EmitReader
from .renderer import ResultRenderer


# =============================================================================
# Data model (kept for cramm/__init__.py export compatibility)
# =============================================================================

@dataclass
class ProcessResult:
    """Spectral analysis result data package."""
    orth_rgb: np.ndarray          # [H, W, 3] uint8
    color_enhanced: np.ndarray    # [H, W, 3] uint8
    mus_image: np.ndarray         # [H, W, 3] uint8
    lon: np.ndarray               # [H, W]
    lat: np.ndarray               # [H, W]


# =============================================================================
# MicaEngine facade
# =============================================================================

class MicaEngine:
    """
    MICA mineral identification engine (facade).

    Composes EmitReader / MicaClassifier / ResultRenderer while preserving the
    original public API. Resource loading happens in this class; analysis and
    rendering are delegated to the respective components.

    Parameters
    ----------
    rf_path : str
        Path to the rf.json rule library.
    splib_path : str
        Path to the USGS splib06b binary library.
    color_txt_path : str
        Path to the mineral RGB color table text file.
    color_tif_path : str
        Path to the muscovite thematic map color lookup table (GeoTIFF).
    """

    def __init__(
        self,
        rf_path: Optional[str] = None,
        splib_path: Optional[str] = None,
        color_txt_path: Optional[str] = None,
        color_tif_path: Optional[str] = None,
    ):
        self.rf_path = Path(rf_path) if rf_path else None  # None → built-in cramm/data/rf.json
        self.splib_path = Path(splib_path) if splib_path else None  # None → built-in cramm/data/splib06b
        self.color_txt_path = Path(color_txt_path) if color_txt_path else None  # None → built-in cramm/data/color_table.json
        self.color_tif_path = Path(color_tif_path) if color_tif_path else None  # None → built-in DEFAULT_MUS_TABLE

        # Components load their own resources (from_paths of the core library)
        self._classifier = MicaClassifier.from_paths(rf_path, splib_path)
        self._renderer = ResultRenderer.from_paths(color_txt_path, color_tif_path)

        # Backward-compatible attribute aliases (for external code accessing resources directly)
        self.rf = self._classifier.rf
        self.mixtures = self._classifier.mixtures
        self.wavelength_map = self._classifier.wavelength_map
        self.dic3 = self._classifier.dic3
        self.ids = self._classifier.ids
        self.colors_dic = self._renderer.colors_dic
        self.table = self._renderer.table

    # ------------------------------------------------------------------
    # Public interface: data loading (delegated to EmitReader)
    # ------------------------------------------------------------------

    @staticmethod
    def load_emit(pathname: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Load an EMIT NetCDF file (delegated to EmitReader)."""
        return EmitReader.load(pathname)

    def get_resample(self, w: np.ndarray, bp: np.ndarray) -> Dict[int, np.ndarray]:
        """Resample all reference spectra to the EMIT wavelengths/FWHM (delegated to MicaClassifier)."""
        return self._classifier.get_resample(w, bp)

    def invalidate_caches(self) -> None:
        """Clear the resampling and compiled-rule caches (delegated to MicaClassifier).

        Must be called after in-place modification of the rule library via
        compatibility aliases such as engine.rf (or create a new engine);
        otherwise the caches keep the old reference-side constants and the
        results are silently wrong.
        """
        self._classifier.invalidate_caches()

    # ------------------------------------------------------------------
    # Public interface: single-spectrum classification (delegated to MicaClassifier)
    # ------------------------------------------------------------------

    def classify_spectrum(
        self,
        spectrum: np.ndarray,
        wl: np.ndarray,
        w: np.ndarray,
        bp: np.ndarray,
        chanels: np.ndarray,
        top_n: int = 10,
        pdf_path: Optional[str] = None,
    ) -> List[Dict]:
        """
        Run all mineral rules on a single spectrum and return the Top-N results sorted by fit.

        Parameters
        ----------
        pdf_path : str, optional
            If provided, generate a multi-page PDF of top-N features with
            continuum removal. One mineral per page, including con_ vs con
            comparisons for all diagnostic/non-feature bands plus
            k0/k1/r2/depth + constraint parameters + depth-ratio constraint
            annotations.
        """
        # Automatically handles 1D → 2D; full-band input (len(w) columns) is
        # automatically reduced to valid bands via chanels — otherwise the
        # column indices derived from wl would mismatch the full-band columns,
        # and the old behavior silently computed wrong results.
        # Input already reduced to selected bands (len(chanels) columns) passes through unchanged.
        spectrum_2d = spectrum.reshape(1, -1).astype("float64") if spectrum.ndim == 1 else spectrum
        if spectrum_2d.shape[1] == len(w) and len(chanels) != len(w):
            spectrum_2d = np.ascontiguousarray(spectrum_2d[:, chanels])
        results = self._classifier.classify_spectrum(spectrum_2d, wl, w, bp, chanels, top_n)
        if pdf_path is not None:
            resampled1 = self._classifier.get_resample(w, bp)
            ResultRenderer.plot_features_pdf(
                results, self._classifier.rf,
                spectrum_2d, wl, resampled1, chanels, pdf_path,
            )
        return results

    # ------------------------------------------------------------------
    # Public interface: spectral analysis (delegated to MicaClassifier + ResultRenderer)
    # ------------------------------------------------------------------

    def spectrum_analysis(
        self,
        spectrum: np.ndarray,
        wl: np.ndarray,
        w: np.ndarray,
        bp: np.ndarray,
        chanels: np.ndarray,
        progress_callback: Optional[Callable[[int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        cancel_flag: Optional[Callable[[], bool]] = None,
        n_workers: Optional[int] = None,
        raw: bool = False,
    ) -> Tuple[np.ndarray, ...]:
        """
        Spectral analysis core (facade): classify → render.

        Parameters
        ----------
        progress_callback : callable(int), optional
            Emitted once per 1/3 progress segment as 33/66/100.
        log_callback : callable(str), optional
            Log callback replacing print.
        cancel_flag : callable() -> bool, optional
            Returning False cancels the remaining computation.
        n_workers : int, optional
            Number of mineral-level parallel worker processes. <=1 takes the
            serial path (bit-exact with the parallel path, guarded by the
            dual-path golden regression in test_parallel.py); None defaults to
            min(os.cpu_count() or 1, 8).
        raw : bool, optional
            False (default) returns the three uint8 images
            (orth_rgb, color_enhanced, mus_image).
            True additionally returns two float arrays:
              mus_center — muscovite 2.2μm absorption center wavelength (μm);
                           non-muscovite pixels are 0.
              fd — per-pixel best (argmax) fit×depth joint confidence.

        Returns
        -------
        orth_rgb, color_enhanced, mus_image : np.ndarray
            All [r, c, 3] uint8.
        mus_center : np.ndarray, optional (when raw=True)
            [r, c] float, muscovite 2200nm absorption wavelength (μm).
        fd : np.ndarray, optional (when raw=True)
            [r, c] float, best fit×depth.
        """
        result = self._classifier.classify(
            spectrum, wl, w, bp, chanels,
            progress_callback=progress_callback,
            log_callback=log_callback,
            cancel_flag=cancel_flag,
            n_workers=n_workers,
        )
        orth_rgb, color_enhanced, mus_image = self._renderer.render(result)
        if raw:
            return (
                orth_rgb, color_enhanced, mus_image,
                result.mus_center.reshape(result.r, result.c),
                result.depth.reshape(result.r, result.c),
            )
        return orth_rgb, color_enhanced, mus_image

    # ------------------------------------------------------------------
    # Public interface: GeoTIFF output (delegated to ResultRenderer)
    # ------------------------------------------------------------------

    @staticmethod
    def write_tiff(
        pathname: str,
        lon: np.ndarray,
        lat: np.ndarray,
        orth_rgb: np.ndarray,
        color_enhanced: np.ndarray,
        mus_image: np.ndarray,
    ) -> None:
        """Handle coordinate resampling and GeoTIFF file saving (delegated to ResultRenderer)."""
        ResultRenderer.write_tiff(
            pathname, lon, lat, orth_rgb, color_enhanced, mus_image
        )


# =============================================================================
# CLI entry point (cramm command after pip install / python -m cramm.mica_engine)
# =============================================================================

def main():
    """Command-line entry point: process EMIT NetCDF → 3 GeoTIFFs + float variables."""
    import argparse
    import time

    parser = argparse.ArgumentParser(
        description="CRAMM — EMIT hyperspectral mineral identification (USGS MICA, extended)"
    )
    parser.add_argument("--input", "-i", required=True, help="path to EMIT L2A NetCDF file")
    parser.add_argument("--output", "-o", default=".", help="output directory (default: current directory)")
    parser.add_argument("--name", "-n", default=None, help="output filename prefix (default: input filename)")
    parser.add_argument("--workers", "-w", type=int, default=None, help="number of parallel worker processes (default: min(cpu, 8))")
    parser.add_argument("--raw", action="store_true", help="also save mus_center + fd float arrays as npz")
    args = parser.parse_args()

    nc_path = args.input
    out_dir = args.output
    out_name = args.name or os.path.splitext(os.path.basename(nc_path))[0]
    out_path = os.path.join(out_dir, out_name)
    # Create the output directory up front: --raw's npz is saved before write_tiff (which contains makedirs)
    os.makedirs(out_dir, exist_ok=True)

    engine = MicaEngine()
    print(f"[CRAMM] Loading: {nc_path}", flush=True)
    spectrum, lon, lat, w, bp, wl, chanels = engine.load_emit(nc_path)
    print(f"[CRAMM] Shape: {spectrum.shape}  Valid bands: {len(chanels)}/{len(w)}", flush=True)

    t0 = time.time()
    if args.raw:
        orth, color, mus, mus_center, fd = engine.spectrum_analysis(
            spectrum, wl, w, bp, chanels, n_workers=args.workers, raw=True,
            progress_callback=lambda p: print(f"[CRAMM] {p}%", flush=True),
        )
        np.savez_compressed(
            os.path.join(out_dir, out_name + "_raw.npz"),
            mus_center=mus_center, fd=fd,
        )
        print(f"[CRAMM] Raw data saved: {out_name}_raw.npz", flush=True)
    else:
        orth, color, mus = engine.spectrum_analysis(
            spectrum, wl, w, bp, chanels, n_workers=args.workers,
            progress_callback=lambda p: print(f"[CRAMM] {p}%", flush=True),
        )
    print(f"[CRAMM] Analysis: {time.time()-t0:.1f}s", flush=True)

    engine.write_tiff(out_path, lon, lat, orth, color, mus)
    print(f"[CRAMM] GeoTIFF written to: {out_dir}", flush=True)
    for suffix in ["_mapping_orth.tiff", "_color_enhanced_orth.tiff", "_mus_orth.tiff"]:
        p = out_path + suffix
        if os.path.exists(p):
            print(f"  {os.path.basename(p)}", flush=True)
    print(f"[CRAMM] Done. Total: {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
