#!/usr/bin/env python
"""Run the current CRAMM engine on the Erlongnan EMIT scene with provenance.

No source imagery is bundled. The output directory must be new or empty so a
current-version run cannot silently overwrite historical paper products.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.resources
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

from cramm import MicaEngine


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resource_sha256(relative: str) -> str:
    resource = importlib.resources.files("cramm").joinpath(relative)
    return hashlib.sha256(resource.read_bytes()).hexdigest()


def package_version() -> str:
    try:
        return importlib.metadata.version("cramm")
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", "-i", type=Path, required=True, help="EMIT L2A NetCDF scene")
    parser.add_argument("--output", "-o", type=Path, required=True, help="New or empty output directory")
    parser.add_argument("--name", "-n", default="erlongnan_current", help="Output filename prefix")
    parser.add_argument("--workers", "-w", type=int, default=4, help="Rule-level worker processes")
    args = parser.parse_args()
    source = args.input.resolve()
    output = args.output.resolve()
    if not source.is_file():
        parser.error(f"Input does not exist: {source}")
    if Path(args.name).name != args.name or not args.name:
        parser.error("--name must be a non-empty filename prefix without directory components")
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    if output.exists() and not output.is_dir():
        parser.error(f"Output path is not a directory: {output}")
    if output.exists() and any(output.iterdir()):
        parser.error(f"Output directory is not empty: {output}; choose a new directory")
    output.mkdir(parents=True, exist_ok=True)

    started = time.time()
    print(f"[case] Hashing input: {source}", flush=True)
    input_hash = sha256(source)
    engine = MicaEngine()
    print("[case] Loading EMIT reflectance and band configuration", flush=True)
    spectrum, lon, lat, w, bp, wl, chanels = engine.load_emit(str(source))
    print(f"[case] Shape={spectrum.shape}; valid bands={len(chanels)}/{len(w)}", flush=True)
    result = engine.spectrum_analysis(
        spectrum,
        wl,
        w,
        bp,
        chanels,
        n_workers=args.workers,
        raw=True,
        progress_callback=lambda value: print(f"[case] {value}%", flush=True),
    )
    orth, color, mus, chl, cal, mus_center, chl_center, cal_center, fd = result
    prefix = output / args.name
    raw_path = output / f"{args.name}_raw.npz"
    np.savez_compressed(
        raw_path,
        mus_center=mus_center,
        chl_center=chl_center,
        cal_center=cal_center,
        fd=fd,
    )
    engine.write_tiff(str(prefix), lon, lat, orth, color, mus, chl, cal)
    suffixes = [
        "_mapping_orth.tiff",
        "_color_enhanced_orth.tiff",
        "_mus_orth.tiff",
        "_chl_orth.tiff",
        "_cal_orth.tiff",
        "_raw.npz",
    ]
    outputs = []
    for suffix in suffixes:
        path = output / f"{args.name}{suffix}"
        if not path.is_file():
            raise FileNotFoundError(f"Expected output was not written: {path}")
        outputs.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})

    manifest = {
        "schema": "cramm.erlongnan.real-scene-run.v2",
        "case": "Erlongnan, Beishan: current-engine EMIT application",
        "input": {
            "path": str(source),
            "name": source.name,
            "bytes": source.stat().st_size,
            "sha256": input_hash,
        },
        "versions": {
            "cramm_distribution": package_version(),
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "code_sha256": {
            **{
                f"cramm/{name}": resource_sha256(name)
                for name in ("__init__.py", "classifier.py", "emit_reader.py", "mica_engine.py", "renderer.py")
            },
            "examples/erlongnan/run_emit_case.py": sha256(Path(__file__).resolve()),
        },
        "source_state_note": (
            "The distribution version alone does not identify an uncommitted working tree; "
            "use the code and resource hashes as the executable provenance record."
        ),
        "resources": {
            "rf.json_sha256": resource_sha256("data/rf.json"),
            "rf77_splib07_1nm.npz_sha256": resource_sha256("data/rf77_splib07_1nm.npz"),
            "color_table.json_sha256": resource_sha256("data/color_table.json"),
        },
        "spectral_contract": {
            "scene_shape": list(spectrum.shape),
            "reflectance_dtype": str(spectrum.dtype),
            "valid_bands": len(chanels),
            "total_bands": len(w),
            "wavelength_range_um": [float(np.min(w)), float(np.max(w))],
            "valid_wavelength_range_um": [float(np.min(wl)), float(np.max(wl))],
        },
        "workers": args.workers,
        "elapsed_seconds": time.time() - started,
        "outputs": outputs,
        "interpretation_boundary": (
            "This is a reproducible real-scene application, not an independent pixel-level "
            "accuracy assessment or a quantitative Au grade model."
        ),
    }
    manifest_path = output / "case_run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[case] Complete in {manifest['elapsed_seconds']:.1f}s: {output}", flush=True)


if __name__ == "__main__":
    main()
