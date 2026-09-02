# -*- coding: utf-8 -*-
"""
MICA spectral analysis core -- splib07 1nm track (cramm.classifier wrapper)
===========================================================================

This script is now a thin CLI wrapper around ``cramm.classifier.MicaClassifier``.
All numerical business logic (rule evaluation, depth-ratio secondary constraints,
wavelength-arbitrated subtypes, quantitative mus/chl/cal center maps, compiled
rule cache, multiprocessing spawn pipeline) lives inside
:mod:`cramm.classifier`, which natively runs the **1 nm rule-face track**
(77-rule-name x 2151-band bundle ``cramm/data/rf77_splib07_1nm.npz``).

The wrapper keeps the original CLI signature of the experimental
``mica_core_v07_1nm.py`` script so downstream callers / batch jobs do not
need to change.

Output fields and dtype layout are identical to the legacy script::

    fit, depth, num, mus_center, chl_center, cal_center, index, r, c

Usage::

    python mica_core_v07_1nm.py                       # default experiment
    python mica_core_v07_1nm.py --crop 500:600,300:400 --workers 2 -o out.npz
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

# Make the repo root importable when the script is invoked directly.
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from cramm.classifier import MicaClassifier  # noqa: E402
from cramm.emit_reader import EmitReader     # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stat(name: str, a: np.ndarray) -> None:
    nz = np.count_nonzero(a)
    print(
        f"  {name:<12s} shape={tuple(a.shape)} dtype={a.dtype!s:<8s} "
        f"min={np.nanmin(a): .6g}  max={np.nanmax(a): .6g}  "
        f"nonzero={nz}/{a.size}"
    )


def _parse_crop(expr: str):
    """Parse "r0:r1,c0:c1"  ->  (r0, r1, c0, c1)."""
    rng, cng = expr.split(",", 1)
    r0, r1 = (int(v) for v in rng.split(":"))
    c0, c1 = (int(v) for v in cng.split(":"))
    return r0, r1, c0, c1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="MICA core — splib07 1nm track (cramm.classifier 1nm-track wrapper)"
    )
    ap.add_argument(
        "--emit",
        default=r"D:\CRAMM\EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc",
        help="EMIT L2A Reflectance netCDF file",
    )
    ap.add_argument(
        "--npz",
        default=None,
        help="1nm rule-face reference bundle (77 rules × 2151 bands); "
             "None uses the bundled cramm/data/rf77_splib07_1nm.npz",
    )
    ap.add_argument(
        "--rules",
        default=None,
        help="Rule JSON whose not-(abs/rel)-feature reflectance_record uses rule names; "
             "None uses the bundled cramm/data/temp_rf_notfeatures_renamed.json",
    )
    ap.add_argument(
        "--crop",
        default="500:600,300:400",
        help='Spatial crop spec "r0:r1,c0:c1"',
    )
    ap.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Number of worker processes (default: 2, aligned with notebook baseline)",
    )
    ap.add_argument(
        "-o", "--out",
        default=r"D:\CRAMM\_core_check.npz",
        help="Output compressed npz path",
    )
    args = ap.parse_args()

    # --- Build classifier on 1nm track --------------------------------------
    cls = MicaClassifier.from_paths(
        rf_path=args.rules,
        splib_path=args.npz,
    )
    print(f"[load] rules={len(cls.rf)}  track={cls.track!r}")

    # --- Load EMIT cube ------------------------------------------------------
    spectrum, lon, lat, w, bp, wl, chanels = EmitReader.load(args.emit)
    print(
        f"[load] emit: spectrum={tuple(spectrum.shape)}  "
        f"valid bands={len(chanels)}/{len(w)}"
    )
    del lon, lat

    # --- Crop ---------------------------------------------------------------
    if args.crop:
        r0, r1, c0, c1 = _parse_crop(args.crop)
        spectrum = spectrum[r0:r1, c0:c1, :]
        print(f"[crop] r=[{r0}:{r1}] c=[{c0}:{c1}] -> {tuple(spectrum.shape)}")

    # --- Classify -----------------------------------------------------------
    z = cls.classify(
        spectrum, wl, w, bp, chanels,
        n_workers=args.workers,
    )
    print("[done] ClassificationResult")

    # --- Report statistics --------------------------------------------------
    print("\n===== statistics =====")
    _stat("fit", z.fit)
    _stat("depth", z.depth)
    _stat("mus_center", z.mus_center)
    _stat("chl_center", z.chl_center)
    _stat("cal_center", z.cal_center)

    counts = np.bincount(z.num, minlength=len(z.index))
    print(f"\nmineral counts ({int(counts.sum())} px):")
    order = np.argsort(-counts)
    for i in order:
        if counts[i] == 0:
            continue
        print(f"  {counts[i]:>6d}  {z.index[i]}")

    # --- Save ---------------------------------------------------------------
    np.savez_compressed(
        args.out,
        fit=z.fit,
        depth=z.depth,
        num=z.num,
        mus_center=z.mus_center,
        chl_center=z.chl_center,
        cal_center=z.cal_center,
        index=np.array(z.index, dtype=object),
        r=z.r,
        c=z.c,
    )
    print(f"\nsaved: {args.out}")


if __name__ == "__main__":
    main()
