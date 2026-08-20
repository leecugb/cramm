#!/usr/bin/env python
# coding: utf-8
"""
EMIT image reading
==================
Reads the reflectance cube, geographic coordinates, and wavelengths/FWHM from
an EMIT L2A NetCDF file, and performs invalid-band removal (-9999 set to 0 +
bad-band mean < 0.02 removal).

Decoupled from spectral analysis and result packaging: this module only
produces raw data and performs no mineral identification.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


class EmitReader:
    """EMIT L2A NetCDF reader."""

    @staticmethod
    def load(pathname: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Load an EMIT NetCDF file, reading band information and removing invalid bands.

        Returns
        -------
        spectrum : np.ndarray
            Reflectance cube [r, c, bands], with -9999 set to 0, **kept as
            float32** — the downstream numerical contract (including the golden
            regression baseline) is built on the reduction precision of float32
            input; callers must not convert to float64 at the entry point
            (ulp-level deviations would turn the regression tests red)
        lon, lat : np.ndarray
            Geographic coordinates [r, c]
        w, bp : np.ndarray
            Wavelengths (μm) and FWHM (μm)
        wl : np.ndarray
            Valid-band wavelengths
        chanels : np.ndarray
            Valid-band indices
        """
        import netCDF4 as nc

        with nc.Dataset(pathname) as dataset:  # with: handle released promptly (original implementation never closed it, leaking shared handles under fork/spawn)
            try:
                lon = dataset["location/lon"][:].data
                lat = dataset["location/lat"][:].data
                spectrum = dataset["reflectance"][:].data
                w = dataset["sensor_band_parameters"]["wavelengths"][:].data / 1000.0
                bp = dataset["sensor_band_parameters"]["fwhm"][:].data / 1000.0
            except (IndexError, KeyError) as e:
                raise ValueError(f"{pathname}: not an EMIT L2A structure (missing variable/group {e})") from e
        # Structural validation: fail here with an actionable message rather than
        # deep downstream (obscure unpack / indexing errors in the bad-band scan).
        if spectrum.ndim != 3:
            raise ValueError(
                f"{pathname}: reflectance should be 3-D [r, c, bands], got shape {spectrum.shape}")
        if lon.shape != spectrum.shape[:2] or lat.shape != spectrum.shape[:2]:
            raise ValueError(
                f"{pathname}: geometry mismatch — reflectance{spectrum.shape} "
                f"vs lon{lon.shape}/lat{lat.shape}")
        if spectrum.shape[2] != w.shape[0]:
            raise ValueError(
                f"{pathname}: band axis mismatch — reflectance has {spectrum.shape[2]} bands "
                f"but sensor_band_parameters/wavelengths has {w.shape[0]}")
        spectrum[spectrum == -9999] = 0

        _, _, s = spectrum.shape
        # Bad-band statistics: mean of positive values per band. The original
        # implementation scanned band-by-band directly on the [s, N] transposed
        # view (stride s*4=1140B > cache line, every access a miss); 285 bands ×
        # 3 full-N passes took about 6s. Optimization: block-transposed copies
        # into contiguous rows (peak memory +~200MB instead of a full +1.8GB),
        # reusing the compressed array within each block (pos.size instead of a
        # separate .any() scan).
        # Bit-exactness: np.mean's input is the compressed positive-value
        # sequence — identical in content to the original implementation (only
        # the source memory layout differs; comparison/compression do no
        # arithmetic), so the reduction sequence is unchanged → t is bit-exact.
        spec2d = spectrum.reshape(-1, s)
        t = []
        # Measured sweet spot for block size: block transposed copy ~32×N×4B≈200MB,
        # balancing cache affinity against peak memory
        BANDS_PER_BLOCK = 32
        for b0 in range(0, s, BANDS_PER_BLOCK):
            blk = np.ascontiguousarray(spec2d[:, b0 : b0 + BANDS_PER_BLOCK].T)
            for i in blk:
                pos = i[i > 0]
                if pos.size:
                    t.append(pos.mean())
                else:
                    t.append(0)
        t = np.array(t)
        # Bad-band decision threshold (algorithm contract): bands whose mean
        # reflectance over valid pixels is < 0.02 are treated as noise / strong
        # water-vapor absorption bands and removed entirely (normal EMIT bands
        # average ~0.3, bad bands ~1e-3; the threshold sits multiple orders of
        # magnitude from both ends, so float32 precision cannot flip the decision)
        mask = t < 0.02
        chanels = np.arange(s)[~mask]
        wl = w[chanels]
        return spectrum, lon, lat, w, bp, wl, chanels
