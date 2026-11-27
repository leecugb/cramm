#!/usr/bin/env python
"""Classify 30 measured ASD spectra after resampling to the EMIT band contract.

This is a real laboratory-spectrum application, not a co-located EMIT pixel
validation. Derived alteration labels are retained for cross-tabulation only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import importlib.resources
import json
from collections import Counter
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

from cramm import MicaEngine
from cramm.classifier import _resample_


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resource_sha256(relative: str) -> str:
    return hashlib.sha256(importlib.resources.files("cramm").joinpath(relative).read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True, help="Traced asd30_index.csv")
    parser.add_argument("--reflectance", type=Path, required=True, help="Native ASD matrix [30, 2151]")
    parser.add_argument("--wavelength", type=Path, required=True, help="Native ASD wavelength array [µm]")
    parser.add_argument("--emit-nc", type=Path, required=True, help="EMIT granule supplying wavelengths/FWHM/good_wavelengths")
    parser.add_argument("--derived-csv", type=Path, help="Optional derived alteration-type table in the verified 30-row order")
    parser.add_argument("--output", type=Path, required=True, help="New or empty output directory")
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and not output.is_dir():
        parser.error(f"Output path is not a directory: {output}")
    if output.exists() and any(output.iterdir()):
        parser.error(f"Output directory is not empty: {output}")
    if args.top_n < 1:
        parser.error("--top-n must be at least 1")
    output.mkdir(parents=True, exist_ok=True)

    index = read_csv(args.index)
    native_wavelength = np.load(args.wavelength, allow_pickle=False)
    native_reflectance = np.load(args.reflectance, allow_pickle=False)
    if native_reflectance.shape != (len(index), len(native_wavelength)):
        raise ValueError(f"ASD matrix/index/wavelength mismatch: {native_reflectance.shape}, {len(index)}, {native_wavelength.shape}")
    if not np.isfinite(native_reflectance).all() or not np.isfinite(native_wavelength).all():
        raise ValueError("ASD inputs contain non-finite values")
    if not (np.diff(native_wavelength) > 0).all():
        raise ValueError("ASD wavelength grid must be strictly increasing")

    with Dataset(args.emit_nc) as dataset:
        group = dataset["sensor_band_parameters"]
        w = group["wavelengths"][:].data / 1000.0
        bp = group["fwhm"][:].data / 1000.0
        channels = np.flatnonzero(np.asarray(group["good_wavelengths"][:].data) == 1)
    if not (len(w) == len(bp) == 285) or not (np.diff(w) > 0).all() or not (bp > 0).all():
        raise ValueError("Invalid EMIT band metadata")
    wl = w[channels]

    # Use the same production Gaussian/FWHM window and positive-sample rule as
    # reference-spectrum resampling. No extrapolation is performed.
    resampled = np.stack([
        _resample_(native_wavelength, spectrum, w, bp)
        for spectrum in native_reflectance
    ])
    if not np.isfinite(resampled[:, channels]).all():
        raise ValueError("Valid EMIT-equivalent ASD bands contain non-finite values")

    derived = read_csv(args.derived_csv) if args.derived_csv else None
    if derived is not None and len(derived) != len(index):
        raise ValueError("Derived alteration-type table has a different row count")
    engine = MicaEngine()
    long_rows = []
    top1_rows = []
    full_results = {}
    for row, spectrum in zip(index, resampled):
        sample_id = row["sample_id"]
        result = engine.classify_spectrum(spectrum, wl, w, bp, channels, top_n=args.top_n)
        full_results[sample_id] = result
        derived_type = derived[int(row["analysis_index_0based"])]["alteration_type"] if derived else ""
        if not result:
            top1_rows.append({
                "analysis_index_0based": row["analysis_index_0based"],
                "sample_id": sample_id,
                "derived_alteration_type": derived_type,
                "top1_rule": "",
                "top1_fit": "",
                "top1_fd": "",
                "returned_candidates": 0,
            })
            continue
        for rank, item in enumerate(result, start=1):
            long_rows.append({
                "sample_id": sample_id,
                "analysis_index_0based": row["analysis_index_0based"],
                "derived_alteration_type": derived_type,
                "rank": rank,
                "rule": item["name"],
                "fit": item["fit"],
                "fd": item["fd"],
            })
        top1_rows.append({
            "analysis_index_0based": row["analysis_index_0based"],
            "sample_id": sample_id,
            "derived_alteration_type": derived_type,
            "top1_rule": result[0]["name"],
            "top1_fit": result[0]["fit"],
            "top1_fd": result[0]["fd"],
            "returned_candidates": len(result),
        })

    with (output / "asd30_topn.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(long_rows[0]) if long_rows else ["sample_id"])
        writer.writeheader()
        writer.writerows(long_rows)
    with (output / "asd30_top1.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(top1_rows[0]))
        writer.writeheader()
        writer.writerows(top1_rows)
    np.savez_compressed(
        output / "asd30_emit_resampled.npz",
        reflectance=resampled,
        wavelengths=w,
        fwhm=bp,
        channels=channels,
        sample_ids=np.array([row["sample_id"] for row in index]),
    )
    rule_counts = Counter(row["top1_rule"] or "NO_OUTPUT" for row in top1_rows)
    type_rule_counts = Counter(f"{row['derived_alteration_type'] or 'UNSPECIFIED'} | {row['top1_rule'] or 'NO_OUTPUT'}" for row in top1_rows)
    try:
        distribution = importlib.metadata.version("cramm")
    except importlib.metadata.PackageNotFoundError:
        distribution = "not-installed"
    summary = {
        "schema": "cramm.erlongnan.asd30-emit-classification.v1",
        "samples": len(index),
        "no_output": sum(not row["top1_rule"] for row in top1_rows),
        "top1_rule_counts": dict(sorted(rule_counts.items())),
        "derived_type_by_top1_rule_counts": dict(sorted(type_rule_counts.items())),
        "inputs": {
            "index_sha256": sha256(args.index),
            "reflectance_sha256": sha256(args.reflectance),
            "wavelength_sha256": sha256(args.wavelength),
            "emit_nc_sha256": sha256(args.emit_nc),
        },
        "emit_contract": {"total_bands": len(w), "valid_bands": len(channels), "resampling": "CRAMM _resample_ production function"},
        "cramm_distribution": distribution,
        "code_sha256": {
            "repo/src/cramm/classifier.py": resource_sha256("classifier.py"),
            "repo/src/cramm/mica_engine.py": resource_sha256("mica_engine.py"),
            "examples/erlongnan/classify_asd30_emit.py": sha256(Path(__file__).resolve()),
        },
        "resource_sha256": {
            "rf.json": resource_sha256("data/rf.json"),
            "rf77_splib07_1nm.npz": resource_sha256("data/rf77_splib07_1nm.npz"),
        },
        "full_topn": full_results,
        "interpretation_boundary": (
            "Measured ASD spectra are classified after EMIT-equivalent resampling. "
            "Derived alteration types are not independent microscopic truth; no co-located "
            "EMIT pixels or accuracy claims are implied."
        ),
    }
    (output / "asd30_classification.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Classified {len(index)} measured ASD spectra; no-output={summary['no_output']}")
    for rule, count in summary["top1_rule_counts"].items():
        print(f"  {count:2d}  {rule}")


if __name__ == "__main__":
    main()
