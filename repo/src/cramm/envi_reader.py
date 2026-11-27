#!/usr/bin/env python
"""Generic ENVI Standard HDR + binary reflectance reader.

The reader returns the same seven-tuple spectral contract as ``EmitReader``.
ENVI map metadata are not expanded into synthetic lon/lat grids, so ``lon`` and
``lat`` are ``None``; classification does not require geolocation.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import numpy as np

# ENVI data types supported for real-valued reflectance cubes.
_DTYPES = {
    1: "u1",
    2: "i2",
    3: "i4",
    4: "f4",
    5: "f8",
    12: "u2",
    13: "u4",
    14: "i8",
    15: "u8",
}


def _parse_header(text: str) -> Dict[str, str]:
    entries: Dict[str, str] = {}
    matches = list(re.finditer(r"(?m)^\s*([A-Za-z][A-Za-z0-9_ ]*?)\s*=\s*", text))
    for index, match in enumerate(matches):
        key = match.group(1).strip().lower()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        if chunk.startswith("{"):
            closing = chunk.rfind("}")
            if closing < 0:
                raise ValueError(f"ENVI header has an unterminated value for {key!r}")
            value = chunk[1:closing]
        else:
            value = chunk.splitlines()[0] if chunk else ""
        entries[key] = value.strip()
    if not entries:
        raise ValueError("No key=value fields found in ENVI header")
    return entries


def _floats(value: str) -> np.ndarray:
    return np.array([float(item) for item in value.replace("\n", " ").split(",") if item.strip()], dtype=np.float64)


def _required_int(header: Dict[str, str], key: str) -> int:
    if key not in header:
        raise ValueError(f"ENVI header lacks required field {key!r}")
    return int(header[key])


def _to_um(values: np.ndarray, units: Optional[str]) -> np.ndarray:
    if units is None:
        # ENVI files frequently omit this field. The two reflectance conventions
        # are unambiguous in the supported VNIR-SWIR range: hundreds/thousands
        # are nm, while values near 0.35-2.5 are micrometres.
        units = "nm" if np.nanmax(np.abs(values)) > 10.0 else "um"
    normalized = units.strip().lower().replace("µ", "u")
    if normalized in {"nm", "nanometer", "nanometers", "nanometre", "nanometres"}:
        return values / 1000.0
    if normalized in {"um", "micrometer", "micrometers", "micrometre", "micrometres", "micron", "microns"}:
        return values
    raise ValueError(f"Unsupported ENVI wavelength units: {units!r}")


class EnviReader:
    """Read an ENVI Standard reflectance cube and its spectral configuration."""

    @staticmethod
    def read_header(pathname: str) -> Dict[str, str]:
        path = Path(pathname)
        if path.suffix.lower() != ".hdr":
            raise ValueError(f"Expected an ENVI .hdr file: {path}")
        return _parse_header(path.read_text(encoding="utf-8-sig"))

    @staticmethod
    def _binary_path(header_path: Path, explicit: Optional[str]) -> Path:
        if explicit:
            path = Path(explicit)
            if not path.is_file():
                raise FileNotFoundError(f"ENVI binary data not found: {path}")
            return path
        candidates = [header_path.with_suffix("")]
        candidates += [header_path.with_suffix(suffix) for suffix in (".dat", ".img", ".bil", ".bsq", ".bip", ".raw", ".bin")]
        for path in candidates:
            if path.is_file():
                return path
        raise FileNotFoundError(
            f"Cannot locate binary data for {header_path}; tried " + ", ".join(str(path) for path in candidates)
        )

    @staticmethod
    def load(
        pathname: str,
        *,
        data_path: Optional[str] = None,
        fwhm: Optional[Sequence[float]] = None,
        valid_bands: Optional[Sequence[int]] = None,
        wavelength_units: Optional[str] = None,
    ) -> Tuple[np.ndarray, None, None, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Load ENVI reflectance as ``[rows, cols, bands]`` float32.

        Parameters
        ----------
        pathname : str
            ENVI ``.hdr`` file. The binary is inferred beside it or supplied by
            ``data_path``.
        fwhm : sequence of float, optional
            Fallback FWHM in **micrometres** when the header lacks ``fwhm``.
        valid_bands : sequence of int, optional
            Explicit zero-based band indices. Otherwise ``good_wavelengths``
            from the header is used when present, else all bands.
        wavelength_units : str, optional
            Override for missing/incorrect header units. Explicit FWHM values
            are always interpreted as micrometres.
        """
        header_path = Path(pathname)
        header = EnviReader.read_header(str(header_path))
        rows = _required_int(header, "lines")
        cols = _required_int(header, "samples")
        bands = _required_int(header, "bands")
        offset = int(header.get("header offset", 0))
        data_type = _required_int(header, "data type")
        byte_order = int(header.get("byte order", 0))
        interleave = header.get("interleave", "").lower()
        if min(rows, cols, bands) <= 0:
            raise ValueError(f"Invalid ENVI dimensions: lines={rows}, samples={cols}, bands={bands}")
        if offset < 0 or byte_order not in (0, 1):
            raise ValueError("ENVI header offset must be >=0 and byte order must be 0 or 1")
        if data_type not in _DTYPES:
            raise ValueError(f"Unsupported ENVI reflectance data type: {data_type}")
        if interleave not in ("bsq", "bil", "bip"):
            raise ValueError(f"Unsupported ENVI interleave: {interleave!r}")

        if "wavelength" not in header:
            raise ValueError("ENVI header lacks required wavelength values")
        w = _floats(header["wavelength"])
        if w.shape != (bands,):
            raise ValueError(f"ENVI wavelength count {len(w)} does not match bands={bands}")
        units = wavelength_units or header.get("wavelength units")
        resolved_units = units or ("nm" if np.nanmax(np.abs(w)) > 10.0 else "um")
        w = _to_um(w, resolved_units)
        if fwhm is None and "fwhm" not in header:
            raise ValueError("ENVI header lacks FWHM; pass fwhm=... in micrometres")
        bp = _floats(header["fwhm"]) if fwhm is None else np.asarray(fwhm, dtype=np.float64)
        if bp.ndim == 0:
            bp = np.full(bands, float(bp), dtype=np.float64)
        if bp.shape != (bands,):
            raise ValueError(f"ENVI FWHM count {bp.size} does not match bands={bands}")
        if fwhm is None:
            bp = _to_um(bp, resolved_units)
        if not np.isfinite(w).all() or not np.isfinite(bp).all() or not (w > 0).all() or not (bp > 0).all():
            raise ValueError("ENVI wavelengths and FWHM must be finite and positive")

        if valid_bands is not None:
            channels = np.asarray(valid_bands, dtype=np.int64)
            if channels.ndim != 1 or len(channels) == 0 or (channels < 0).any() or (channels >= bands).any():
                raise ValueError("valid_bands must be a non-empty 1-D sequence of valid zero-based indices")
            if len(np.unique(channels)) != len(channels):
                raise ValueError("valid_bands contains duplicate indices")
        elif "good_wavelengths" in header or "good wavelengths" in header:
            good = _floats(header.get("good_wavelengths", header.get("good wavelengths")))
            if good.shape != (bands,):
                raise ValueError("ENVI good_wavelengths count does not match bands")
            channels = np.flatnonzero(good == 1)
        else:
            channels = np.arange(bands, dtype=np.int64)
        if len(channels) == 0:
            raise ValueError("ENVI valid-band mask is empty")
        wl = w[channels]

        binary = EnviReader._binary_path(header_path, data_path)
        dtype = np.dtype(("<" if byte_order == 0 else ">") + _DTYPES[data_type])
        shape = {
            "bsq": (bands, rows, cols),
            "bil": (rows, bands, cols),
            "bip": (rows, cols, bands),
        }[interleave]
        expected = offset + rows * cols * bands * dtype.itemsize
        if binary.stat().st_size != expected:
            raise ValueError(
                f"ENVI binary size mismatch: {binary.stat().st_size} != {expected} "
                f"(offset={offset}, shape={shape}, dtype={dtype})"
            )
        raw = np.memmap(binary, dtype=dtype, mode="r", offset=offset, shape=shape, order="C")
        if interleave == "bsq":
            raw = raw.transpose(1, 2, 0)
        elif interleave == "bil":
            raw = raw.transpose(0, 2, 1)
        spectrum = np.array(raw, dtype=np.float32, copy=True, order="C")
        del raw

        if "data ignore value" in header:
            ignore = float(header["data ignore value"])
            spectrum[spectrum == ignore] = 0
        if "reflectance scale factor" in header:
            scale = float(header["reflectance scale factor"])
            if not np.isfinite(scale) or scale <= 0:
                raise ValueError("ENVI reflectance scale factor must be finite and positive")
            spectrum /= np.float32(scale)
        spectrum[~np.isfinite(spectrum)] = 0
        return spectrum, None, None, w, bp, wl, channels
