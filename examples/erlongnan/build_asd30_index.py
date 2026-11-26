#!/usr/bin/env python
"""Rebuild the 30-spectrum ASD index from the original ENVI library.

The selected reflectance matrix contains no sample names. This script recovers
its row-to-sample mapping by numerical matching against the 100-spectrum
``beishan`` library, then checks that both raw ASD representations exist.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

MATCH_TOLERANCE = 1e-12
FIELDS = [
    "analysis_index_0based",
    "sample_id",
    "library_index_0based",
    "library_spectrum_name",
    "asd_binary_present",
    "asd_text_present",
    "asd_binary_sha256",
    "asd_text_sha256",
    "max_abs_difference",
    "text_wavelength_max_abs_difference_nm",
    "text_reflectance_max_abs_difference",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scalar(header: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}\s*=\s*([^\n]+)$", header)
    if not match:
        raise ValueError(f"ENVI header lacks {key!r}")
    return match.group(1).strip()


def block(header: str, key: str) -> str:
    match = re.search(rf"{re.escape(key)}\s*=\s*\{{(.*?)\}}", header, re.S)
    if not match:
        raise ValueError(f"ENVI header lacks {key!r} block")
    return match.group(1)


def load_library(asd_dir: Path) -> Tuple[np.ndarray, List[str], np.ndarray, Dict[str, object]]:
    binary = asd_dir / "beishan"
    header_path = asd_dir / "beishan.hdr"
    header = header_path.read_text(encoding="utf-8")
    bands = int(scalar(header, "samples"))
    spectra = int(scalar(header, "lines"))
    data_type = int(scalar(header, "data type"))
    byte_order = int(scalar(header, "byte order"))
    interleave = scalar(header, "interleave").lower()
    if data_type not in (4, 5):
        raise ValueError(f"Expected ENVI float32/float64 library, got data type {data_type}")
    if interleave != "bsq":
        raise ValueError(f"Expected BSQ spectral library, got {interleave!r}")
    dtype = np.dtype(("<" if byte_order == 0 else ">") + ("f4" if data_type == 4 else "f8"))
    expected_bytes = spectra * bands * dtype.itemsize
    if binary.stat().st_size != expected_bytes:
        raise ValueError(f"Library size mismatch: {binary.stat().st_size} != {expected_bytes}")
    library = np.fromfile(binary, dtype=dtype).reshape(spectra, bands)
    names = [item.strip() for item in block(header, "spectra names").replace("\n", " ").split(",")]
    if len(names) != spectra or any(not name for name in names):
        raise ValueError(f"Expected {spectra} non-empty spectrum names, got {len(names)}")
    wavelengths_nm = np.array(
        [float(item) for item in block(header, "wavelength").replace("\n", " ").split(",")],
        dtype=np.float64,
    )
    if wavelengths_nm.shape != (bands,) or not np.all(np.diff(wavelengths_nm) > 0):
        raise ValueError("Invalid ENVI wavelength grid")
    metadata = {
        "binary": str(binary.resolve()),
        "header": str(header_path.resolve()),
        "binary_sha256": sha256(binary),
        "header_sha256": sha256(header_path),
        "spectra": spectra,
        "bands": bands,
        "data_type": data_type,
        "byte_order": byte_order,
        "interleave": interleave,
    }
    return library, names, wavelengths_nm, metadata


def build_index(asd_dir: Path, reflectance_path: Path, wavelength_path: Optional[Path]) -> Tuple[List[dict], dict]:
    library, names, wavelengths_nm, metadata = load_library(asd_dir)
    selected = np.load(reflectance_path, allow_pickle=False)
    if selected.ndim != 2 or selected.shape[1] != library.shape[1]:
        raise ValueError(f"Selected matrix shape {selected.shape} does not match library {library.shape}")
    if not np.isfinite(selected).all():
        raise ValueError("Selected matrix contains non-finite reflectance")
    if wavelength_path is not None:
        wavelengths_um = np.load(wavelength_path, allow_pickle=False)
        if not np.allclose(wavelengths_um, wavelengths_nm / 1000.0, rtol=0.0, atol=1e-12):
            raise ValueError("Selected wavelength array differs from the ENVI header")
    rows = []
    for analysis_index, spectrum in enumerate(selected):
        differences = np.max(np.abs(library - spectrum), axis=1)
        matches = np.flatnonzero(differences <= MATCH_TOLERANCE)
        if len(matches) != 1:
            raise ValueError(
                f"Analysis row {analysis_index} has {len(matches)} library matches within "
                f"{MATCH_TOLERANCE:g}; minimum difference is {differences.min():.3e}"
            )
        library_index = int(matches[0])
        spectrum_name = names[library_index]
        if Path(spectrum_name).name != spectrum_name:
            raise ValueError(f"Unsafe spectrum name in ENVI header: {spectrum_name!r}")
        sample_id = spectrum_name[:-4] if spectrum_name.lower().endswith(".asd") else spectrum_name
        binary_path = asd_dir / spectrum_name
        text_path = asd_dir / (spectrum_name + ".txt")
        if not binary_path.is_file() or not text_path.is_file():
            raise FileNotFoundError(f"Missing raw ASD representation for {spectrum_name}")
        text_data = np.loadtxt(text_path, skiprows=1)
        if text_data.shape != (library.shape[1], 2):
            raise ValueError(f"Unexpected ASD text shape for {spectrum_name}: {text_data.shape}")
        if not np.isfinite(text_data).all():
            raise ValueError(f"ASD text contains non-finite values: {spectrum_name}")
        text_wavelength_difference = float(np.max(np.abs(text_data[:, 0] - wavelengths_nm)))
        text_reflectance_difference = float(np.max(np.abs(text_data[:, 1] - library[library_index])))
        if text_wavelength_difference > MATCH_TOLERANCE or text_reflectance_difference > MATCH_TOLERANCE:
            raise ValueError(
                f"ASD text differs from library for {spectrum_name}: "
                f"wavelength={text_wavelength_difference:.3e} nm, "
                f"reflectance={text_reflectance_difference:.3e}"
            )
        rows.append({
            "analysis_index_0based": analysis_index,
            "sample_id": sample_id,
            "library_index_0based": library_index,
            "library_spectrum_name": spectrum_name,
            "asd_binary_present": 1,
            "asd_text_present": 1,
            "asd_binary_sha256": sha256(binary_path),
            "asd_text_sha256": sha256(text_path),
            "max_abs_difference": f"{differences[library_index]:.3e}",
            "text_wavelength_max_abs_difference_nm": f"{text_wavelength_difference:.3e}",
            "text_reflectance_max_abs_difference": f"{text_reflectance_difference:.3e}",
        })
    if len({row["sample_id"] for row in rows}) != len(rows):
        raise ValueError("Selected spectra do not map to unique sample IDs")
    summary = {
        "schema": "cramm.erlongnan.asd30-traceability.v1",
        "selected_reflectance": str(reflectance_path.resolve()),
        "selected_reflectance_sha256": sha256(reflectance_path),
        "selected_shape": list(selected.shape),
        "selected_wavelength": str(wavelength_path.resolve()) if wavelength_path else None,
        "selected_wavelength_sha256": sha256(wavelength_path) if wavelength_path else None,
        "wavelength_range_nm": [float(wavelengths_nm[0]), float(wavelengths_nm[-1])],
        "match_tolerance": MATCH_TOLERANCE,
        "maximum_abs_difference": max(float(row["max_abs_difference"]) for row in rows),
        "all_asd_binary_present": all(row["asd_binary_present"] for row in rows),
        "all_asd_text_present": all(row["asd_text_present"] for row in rows),
        "maximum_text_wavelength_abs_difference_nm": max(
            float(row["text_wavelength_max_abs_difference_nm"]) for row in rows
        ),
        "maximum_text_reflectance_abs_difference": max(
            float(row["text_reflectance_max_abs_difference"]) for row in rows
        ),
        "library": metadata,
        "scope_note": (
            "This recovers spectral provenance only. Coordinates, Au units, assays, microscopy, "
            "and EMIT pixel correspondence require separate sample-level evidence."
        ),
    }
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asd-dir", type=Path, required=True, help="Directory containing beishan, beishan.hdr and ASD files")
    parser.add_argument("--reflectance", type=Path, required=True, help="Selected reflectance matrix, shape [30, 2151]")
    parser.add_argument("--wavelength", type=Path, help="Selected wavelength array in micrometres")
    parser.add_argument("--output", type=Path, required=True, help="Output CSV index")
    parser.add_argument("--summary", type=Path, help="Optional JSON audit summary")
    args = parser.parse_args()
    rows, summary = build_index(args.asd_dir, args.reflectance, args.wavelength)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Indexed {len(rows)} unique ASD samples; "
        f"max |difference|={summary['maximum_abs_difference']:.3e}; "
        f"binary/text complete={summary['all_asd_binary_present']}/{summary['all_asd_text_present']}; "
        f"max text reflectance difference={summary['maximum_text_reflectance_abs_difference']:.3e}"
    )


if __name__ == "__main__":
    main()
