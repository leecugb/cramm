#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate reference-derived synthetic development spectra from CRAMM's bundle.

Scope: deterministic self-consistency and algorithm-development data only. The
endmembers are the same references used by CRAMM, so results on this dataset are
not independent accuracy estimates and must not be presented as such.

Outputs (written to a new, empty output directory):
  spectra.npz  -- full-band clean/noisy spectra, valid masks and sensor metadata
  truth.csv    -- one row per spectrum with endmember and perturbation truth
  manifest.json -- source hash, design, counts, audits and output hashes
  README.md    -- scope and CRAMM loading example
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "repo/src/cramm/data/rf77_splib07_1nm.npz"
DEFAULT_OUT = REPO / "output/synthetic_reference_v1"
BASE_SEED = 20261118
SNR_LEVELS_DB = (40.0, 25.0, 15.0)
CONTINUUM_SLOPES_PER_UM = (-0.10, 0.0, 0.10)
MIXTURE_FRACTIONS = (0.25, 0.50, 0.75)
BAND_CENTERS_UM = np.linspace(0.381, 2.508, 285)
FWHM_UM = np.full(285, 0.0074)
BASE_VALID_MASK = np.array(
    [not (126 <= i < 150 or 190 <= i < 210) for i in range(285)], dtype=bool
)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def resample_bundle(grid: np.ndarray, spectra: np.ndarray) -> np.ndarray:
    """Gaussian FWHM resampling with the same truncation convention as CRAMM."""
    out = np.full((spectra.shape[0], len(BAND_CENTERS_UM)), np.nan, dtype=np.float64)
    half_widths = FWHM_UM / 2.0
    sigmas = (half_widths**2 / np.log(2.0)) ** 0.5
    for j, (center, half, sigma) in enumerate(
        zip(BAND_CENTERS_UM, half_widths, sigmas)
    ):
        lo = np.searchsorted(grid, center - half, side="right")
        hi = np.searchsorted(grid, center + half, side="left")
        if hi <= lo:
            continue
        x = grid[lo:hi]
        values = spectra[:, lo:hi]
        weights = np.exp(-((x - center) ** 2) / sigma**2)
        valid = np.isfinite(values) & (values > 0)
        denominator = (valid * weights).sum(axis=1)
        numerator = (np.where(valid, values, 0.0) * weights).sum(axis=1)
        ok = denominator > 0
        out[ok, j] = numerator[ok] / denominator[ok]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=BASE_SEED)
    parser.add_argument(
        "--perturbation", choices=("white", "low-frequency"), default="white",
        help="Independent band noise or spectrally smoothed low-frequency noise",
    )
    parser.add_argument(
        "--mix-design", choices=("general", "white-mica-confuser", "white-mica-clay",
                                  "combined", "extended"),
        default="general",
        help="Add targeted white-mica/illite vs carbonate/chlorite/epidote mixtures",
    )
    parser.add_argument(
        "--emit-nc", type=Path, default=None,
        help="Read actual wavelengths, FWHM and good_wavelengths from an EMIT L2A granule",
    )
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise SystemExit(f"Output directory must be empty: {out}")

    global BAND_CENTERS_UM, FWHM_UM, BASE_VALID_MASK
    sensor_metadata = {"type": "EMIT-like offline fixture"}
    if args.emit_nc is not None:
        from netCDF4 import Dataset
        emit_path = args.emit_nc.resolve()
        with Dataset(emit_path) as ds:
            group = ds["sensor_band_parameters"]
            # Preserve the NetCDF float32 arithmetic used by EmitReader.load;
            # upcasting here would make the synthetic band contract subtly
            # different from production scene processing.
            BAND_CENTERS_UM = group["wavelengths"][:].data / 1000.0
            FWHM_UM = group["fwhm"][:].data / 1000.0
            BASE_VALID_MASK = np.asarray(
                group["good_wavelengths"][:].data) == 1
        if not (len(BAND_CENTERS_UM) == len(FWHM_UM) == len(BASE_VALID_MASK) == 285):
            raise ValueError("Expected 285 EMIT spectral bands")
        if not ((np.diff(BAND_CENTERS_UM) > 0).all() and (FWHM_UM > 0).all()):
            raise ValueError("Invalid EMIT wavelength or FWHM metadata")
        sensor_metadata = {
            "type": "actual EMIT L2A metadata",
            "granule": emit_path.name,
            "wavelength_units_in_source": "nm",
            "wavelength_dtype_after_um_conversion": str(BAND_CENTERS_UM.dtype),
            "fwhm_dtype_after_um_conversion": str(FWHM_UM.dtype),
        }

    sys.path.insert(0, str(REPO / "docs"))
    from crosslib_benchmark import RULE_FAMILY  # noqa: E402

    z = np.load(SOURCE, allow_pickle=False)
    grid = np.asarray(z["grid"], dtype=np.float64)
    rules = np.asarray(z["rule"], dtype=str)
    labels = np.asarray(z["label"], dtype=str)
    spectra = np.asarray(z["spectra"], dtype=np.float64)
    if len(rules) != 77 or spectra.shape != (77, 2151):
        raise ValueError("Unexpected reference bundle shape")
    if set(rules) != set(RULE_FAMILY):
        raise ValueError("Rule-family map and reference bundle differ")

    sensor_refs = resample_bundle(grid, spectra)
    row = {name: i for i, name in enumerate(rules)}
    native_ranges = []
    for y in spectra:
        valid = np.isfinite(y) & (y > 0)
        native_ranges.append((float(grid[valid][0]), float(grid[valid][-1])))

    # Only physical, single-family mineral references become new mixture endmembers.
    # Existing synthetic/AMX/alias mixture rows remain in the single-reference leg.
    mixture_endmembers = [
        i for i, name in enumerate(rules)
        if len(RULE_FAMILY[str(name)]) == 1
        and RULE_FAMILY[str(name)] != {"other"}
        and not str(labels[i]).lower().startswith("synth")
        and not str(labels[i]).endswith(("[AMX]", "[alias]"))
    ]
    general_pairs = {
        tuple(sorted((mixture_endmembers[k],
                      mixture_endmembers[(k + stride) % len(mixture_endmembers)])))
        for k in range(len(mixture_endmembers)) for stride in (1, 7)
    }
    high_ratio_pairs = set()
    low_ratio_pairs = set()
    if args.mix_design != "general":
        white_mica = [row[n] for n in (
            "muscovite_lowAl", "muscovite_medAl", "muscovite_medhighAl",
            "muscovite_Fe-rich", "illite_imt1", "illite_gds4",
        )]
        if args.mix_design in ("white-mica-confuser", "combined", "extended"):
            confusers = [row[n] for n in (
                "calcite", "dolomite", "chlorite_lowFe", "clinochlore",
                "clinochlore_Fe", "thuringite", "epidote",
            )]
            high_ratio_pairs = {
                tuple(sorted((a, b))) for a in white_mica for b in confusers
            }
        if args.mix_design in ("white-mica-clay", "extended"):
            clay = [row[n] for n in (
                "kaolinite_wxl", "kaolinite_pxl", "kaolinite_or_dickite",
                "montmorillonite_Na", "montmorillonite_Ca", "nontronite", "hectorite",
            )]
            low_ratio_pairs = {
                tuple(sorted((a, b))) for a in white_mica for b in clay
            }
    targeted_pairs = high_ratio_pairs | low_ratio_pairs
    if args.mix_design == "general":
        pair_set = general_pairs
    elif args.mix_design == "white-mica-confuser":
        pair_set = high_ratio_pairs
    elif args.mix_design == "white-mica-clay":
        pair_set = low_ratio_pairs
    elif args.mix_design == "combined":
        pair_set = general_pairs | high_ratio_pairs  # preserve lowfreq v1 design
    else:
        pair_set = general_pairs | high_ratio_pairs | low_ratio_pairs
    pairs = sorted(pair_set)

    records: list[dict] = []
    noisy_rows: list[np.ndarray] = []
    clean_rows: list[np.ndarray] = []
    mask_rows: list[np.ndarray] = []

    def make_noise(rng: np.random.Generator, valid: np.ndarray, sigma: float) -> np.ndarray:
        """Return noise on valid bands, normalized to the requested RMS."""
        n_valid = int(valid.sum())
        if args.perturbation == "white":
            return rng.normal(0.0, sigma, n_valid)
        # Smooth before masking so bad-band gaps do not create artificial
        # discontinuities. Normalize on the observed bands to preserve SNR.
        kernel_x = np.arange(-24, 25, dtype=np.float64)
        kernel = np.exp(-0.5 * (kernel_x / 6.0) ** 2)
        kernel /= kernel.sum()
        smooth = np.convolve(rng.normal(0.0, 1.0, len(valid)), kernel, mode="same")
        observed = smooth[valid]
        observed = observed - observed.mean()
        observed /= np.sqrt(np.mean(observed**2))
        return sigma * observed

    def add_sample(kind: str, i1: int, i2: int, fraction1: float,
                   slope: float, snr_db, replicate: int, targeted: bool = False,
                   targeted_group: str = "") -> None:
        index = len(records)
        sample_id = f"SYN{index:05d}"
        if i2 < 0:
            base = sensor_refs[i1]
            valid = BASE_VALID_MASK & np.isfinite(base) & (base > 0)
            coverage = native_ranges[i1]
            family2 = ""
            source_rule2 = source_label2 = ""
            dominant = str(rules[i1])
            fraction2 = 0.0
        else:
            base = sensor_refs[i1]
            other = sensor_refs[i2]
            valid = (BASE_VALID_MASK & np.isfinite(base) & np.isfinite(other)
                     & (base > 0) & (other > 0))
            base = fraction1 * base + (1.0 - fraction1) * other
            valid &= np.isfinite(base) & (base > 0)
            coverage = (max(native_ranges[i1][0], native_ranges[i2][0]),
                        min(native_ranges[i1][1], native_ranges[i2][1]))
            family2 = ";".join(sorted(RULE_FAMILY[str(rules[i2])]))
            source_rule2, source_label2 = str(rules[i2]), str(labels[i2])
            dominant = (str(rules[i1]) if fraction1 > 0.5 else
                        str(rules[i2]) if fraction1 < 0.5 else "")
            fraction2 = 1.0 - fraction1
        n_valid = int(valid.sum())
        if n_valid < 20:
            raise ValueError(f"Too few valid bands for {sample_id}: {n_valid}")

        continuum = 1.0 + slope * (BAND_CENTERS_UM - 1.4)
        clean = np.full(len(BAND_CENTERS_UM), np.nan, dtype=np.float64)
        clean[valid] = base[valid] * continuum[valid]
        noisy = clean.copy()
        seed = -1
        sigma = 0.0
        measured_snr = float("nan")
        n_clipped = 0
        if snr_db is not None:
            seed = int(args.seed + index)
            rng = np.random.default_rng(seed)
            sigma = float(np.sqrt(np.mean(clean[valid] ** 2)) / 10.0 ** (snr_db / 20.0))
            values = clean[valid] + make_noise(rng, valid, sigma)
            n_clipped = int((values < 1e-6).sum())
            noisy[valid] = np.maximum(values, 1e-6)
            measured_snr = float(20.0 * np.log10(
                np.sqrt(np.mean(clean[valid] ** 2)) /
                np.sqrt(np.mean((noisy[valid] - clean[valid]) ** 2))
            ))

        records.append({
            "sample_id": sample_id,
            "sample_kind": kind,
            "perturbation_model": args.perturbation,
            "targeted_mix": targeted,
            "targeted_group": targeted_group,
            "split": "reference-derived-development",
            "reference_row_1": i1,
            "reference_row_2": i2,
            "source_rule_1": str(rules[i1]),
            "source_rule_2": source_rule2,
            "source_label_1": str(labels[i1]),
            "source_label_2": source_label2,
            "family_set_1": ";".join(sorted(RULE_FAMILY[str(rules[i1])])),
            "family_set_2": family2,
            "fraction_1": fraction1,
            "fraction_2": fraction2,
            "dominant_rule": dominant,
            "continuum_slope_per_um": slope,
            "snr_db_target": "" if snr_db is None else snr_db,
            "replicate": replicate,
            "noise_seed": seed,
            "noise_sigma": sigma,
            "measured_snr_db": measured_snr,
            "n_clipped": n_clipped,
            "n_valid_bands": n_valid,
            "coverage_start_um": coverage[0],
            "coverage_end_um": coverage[1],
        })
        noisy_rows.append(noisy)
        clean_rows.append(clean)
        mask_rows.append(valid)

    # Leg A: every rule-face reference, one clean copy and two noisy replicates
    # for each continuum/SNR combination.
    for i in range(len(rules)):
        add_sample("single_reference", i, -1, 1.0, 0.0, None, 0)
        for slope in CONTINUUM_SLOPES_PER_UM:
            for snr_db in SNR_LEVELS_DB:
                for replicate in range(2):
                    add_sample("single_reference", i, -1, 1.0,
                               slope, snr_db, replicate)

    # Leg B: deterministic binary areal mixtures of physical single-family minerals.
    for i1, i2 in pairs:
        targeted = (i1, i2) in targeted_pairs
        targeted_group = ("high_ratio_confuser" if (i1, i2) in high_ratio_pairs else
                          "low_ratio_clay" if (i1, i2) in low_ratio_pairs else "")
        for fraction1 in MIXTURE_FRACTIONS:
            add_sample("binary_areal", i1, i2, fraction1, 0.0, None, 0,
                       targeted, targeted_group)
            for slope in CONTINUUM_SLOPES_PER_UM:
                for snr_db in SNR_LEVELS_DB:
                    add_sample("binary_areal", i1, i2, fraction1,
                               slope, snr_db, 0, targeted, targeted_group)

    noisy_array = np.asarray(noisy_rows, dtype=np.float64)
    clean_array = np.asarray(clean_rows, dtype=np.float64)
    valid_array = np.asarray(mask_rows, dtype=bool)
    n = len(records)
    if noisy_array.shape != (n, 285) or valid_array.shape != (n, 285):
        raise AssertionError("Output array shape mismatch")

    # Full internal audit before delivery.
    audits = {}
    audits["finite_positive_observed_values"] = bool(
        np.isfinite(noisy_array[valid_array]).all()
        and (noisy_array[valid_array] > 0).all()
        and np.isfinite(clean_array[valid_array]).all()
        and (clean_array[valid_array] > 0).all()
    )
    audits["invalid_entries_are_nan"] = bool(
        np.isnan(noisy_array[~valid_array]).all()
        and np.isnan(clean_array[~valid_array]).all()
    )
    clean_single_ok = True
    clean_mixture_ok = True
    noise_replay_ok = True
    for i, rec in enumerate(records):
        mask = valid_array[i]
        i1, i2 = rec["reference_row_1"], rec["reference_row_2"]
        if rec["snr_db_target"] == "" and rec["continuum_slope_per_um"] == 0:
            expected = sensor_refs[i1] if i2 < 0 else (
                rec["fraction_1"] * sensor_refs[i1]
                + rec["fraction_2"] * sensor_refs[i2]
            )
            same = np.array_equal(clean_array[i, mask], expected[mask])
            if i2 < 0:
                clean_single_ok &= same
            else:
                clean_mixture_ok &= same
        if rec["snr_db_target"] != "":
            rng = np.random.default_rng(rec["noise_seed"])
            expected = clean_array[i, mask] + make_noise(rng, mask, rec["noise_sigma"])
            expected = np.maximum(expected, 1e-6)
            noise_replay_ok &= np.array_equal(noisy_array[i, mask], expected)
    audits["clean_single_reference_reconstruction"] = bool(clean_single_ok)
    audits["clean_binary_mixture_reconstruction"] = bool(clean_mixture_ok)
    audits["seeded_noise_replay_bit_exact"] = bool(noise_replay_ok)
    if not all(audits.values()):
        raise AssertionError(f"Synthetic-data audit failed: {audits}")

    npz_path = out / "spectra.npz"
    csv_path = out / "truth.csv"
    np.savez_compressed(
        npz_path,
        reflectance=noisy_array,
        noise_free_reflectance=clean_array,
        valid_mask=valid_array,
        sample_id=np.asarray([r["sample_id"] for r in records], dtype="U16"),
        sample_kind=np.asarray([r["sample_kind"] for r in records], dtype="U24"),
        perturbation_model=np.asarray(
            [r["perturbation_model"] for r in records], dtype="U16"),
        targeted_mix=np.asarray([r["targeted_mix"] for r in records], dtype=bool),
        targeted_group=np.asarray([r["targeted_group"] for r in records], dtype="U24"),
        reference_row_1=np.asarray([r["reference_row_1"] for r in records], dtype=np.int16),
        reference_row_2=np.asarray([r["reference_row_2"] for r in records], dtype=np.int16),
        fraction_1=np.asarray([r["fraction_1"] for r in records], dtype=np.float64),
        fraction_2=np.asarray([r["fraction_2"] for r in records], dtype=np.float64),
        continuum_slope_per_um=np.asarray(
            [r["continuum_slope_per_um"] for r in records], dtype=np.float64),
        snr_db_target=np.asarray(
            [np.nan if r["snr_db_target"] == "" else r["snr_db_target"] for r in records],
            dtype=np.float64),
        replicate=np.asarray([r["replicate"] for r in records], dtype=np.int8),
        noise_seed=np.asarray([r["noise_seed"] for r in records], dtype=np.int64),
        noise_sigma=np.asarray([r["noise_sigma"] for r in records], dtype=np.float64),
        band_centers_um=BAND_CENTERS_UM,
        fwhm_um=FWHM_UM,
        base_valid_mask=BASE_VALID_MASK,
        reference_rules=rules,
        reference_sensor_spectra=sensor_refs,
    )
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    counts = Counter(r["sample_kind"] for r in records)
    snr_counts = Counter(str(r["snr_db_target"] or "clean") for r in records)
    valid_counts = np.asarray([r["n_valid_bands"] for r in records])
    clipped = sum(r["n_clipped"] for r in records)
    manifest = {
        "schema_version": "1.0",
        "date": str(date.today()),
        "evidence_scope": (
            "Reference-derived development/self-consistency data only; "
            "not independent validation or unbiased accuracy evidence."
        ),
        "source": {
            "path": "cramm/data/rf77_splib07_1nm.npz",
            "sha256": file_sha256(SOURCE),
            "rules": len(rules),
        },
        "sensor": {
            "metadata": sensor_metadata,
            "n_bands": len(BAND_CENTERS_UM),
            "band_centers_um": [float(BAND_CENTERS_UM[0]), float(BAND_CENTERS_UM[-1])],
            "fwhm_um_min": float(FWHM_UM.min()),
            "fwhm_um_max": float(FWHM_UM.max()),
            "base_valid_bands": int(BASE_VALID_MASK.sum()),
            "excluded_band_ranges_zero_based": (
                [[126, 150], [190, 210]] if args.emit_nc is None else "from good_wavelengths"
            ),
        },
        "design": {
            "base_seed": args.seed,
            "snr_levels_db": SNR_LEVELS_DB,
            "continuum_slopes_per_um": CONTINUUM_SLOPES_PER_UM,
            "mixture_fractions": MIXTURE_FRACTIONS,
            "single_reference_noisy_replicates": 2,
            "perturbation_model": args.perturbation,
            "mix_design": args.mix_design,
            "low_frequency_kernel_sigma_bands": 6.0 if args.perturbation == "low-frequency" else 0.0,
            "mixture_endmembers": len(mixture_endmembers),
            "unique_binary_pairs": len(pairs),
            "targeted_binary_pairs": len(targeted_pairs & pair_set),
            "high_ratio_binary_pairs": len(high_ratio_pairs & pair_set),
            "low_ratio_binary_pairs": len(low_ratio_pairs & pair_set),
        },
        "counts": {
            "spectra": n,
            "by_kind": dict(sorted(counts.items())),
            "targeted_binary_spectra": sum(r["targeted_mix"] for r in records),
            "high_ratio_targeted_spectra": sum(r["targeted_group"] == "high_ratio_confuser" for r in records),
            "low_ratio_targeted_spectra": sum(r["targeted_group"] == "low_ratio_clay" for r in records),
            "by_target_snr": dict(sorted(snr_counts.items())),
            "valid_bands_min": int(valid_counts.min()),
            "valid_bands_median": float(np.median(valid_counts)),
            "valid_bands_max": int(valid_counts.max()),
            "clipped_samples": sum(r["n_clipped"] > 0 for r in records),
            "clipped_values": clipped,
        },
        "audits": audits,
        "files": {
            "spectra.npz": {"sha256": file_sha256(npz_path), "bytes": npz_path.stat().st_size},
            "truth.csv": {"sha256": file_sha256(csv_path), "bytes": csv_path.stat().st_size},
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.md").write_text(
        "# CRAMM reference-derived synthetic development data\n\n"
        "This dataset uses CRAMM's own 77 reference rows. It is for generator "
        "checks, debugging and paired algorithm development only. It is not an "
        "independent test set and must not be used as an unbiased accuracy claim.\n\n"
        f"Sensor metadata: {sensor_metadata['type']}; "
        f"{len(BAND_CENTERS_UM)} bands, {int(BASE_VALID_MASK.sum())} base-valid.\n"
        f"Perturbation: {args.perturbation}; mixture design: {args.mix_design}.\n\n"
        f"Spectra: {n}; single-reference: {counts['single_reference']}; "
        f"binary areal mixtures: {counts['binary_areal']}.\n\n"
        "Load with `np.load('spectra.npz', allow_pickle=False)`. For spectrum `i`, "
        "use `chanels = np.flatnonzero(valid_mask[i])`, "
        "`wl = band_centers_um[chanels]`, and pass "
        "`reflectance[i, chanels].reshape(1, -1)` to `classify_spectrum` together "
        "with the full `band_centers_um`, `fwhm_um` and `chanels` arrays. "
        "Endmember fractions and all perturbations are recorded in `truth.csv`.\n",
        encoding="utf-8")
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))
    print("AUDITS", audits)
    print("WROTE", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
