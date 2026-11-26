#!/usr/bin/env python
"""Numerically verify the equations in docs/cramm_mathematical_model.md."""
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cramm.classifier import _fit_r2_depth, _get_quadratic_center, _precompute_feature, _resample_


def main() -> None:
    rng = np.random.default_rng(20261125)

    # 1. Gaussian FWHM resampling: open window, half-width weight = 0.5,
    # positive finite samples only, normalized weighted mean.
    grid = np.arange(0.95, 1.051, 0.001)
    values = 1.0 + 0.1 * grid
    target = np.array([1.0])
    fwhm = np.array([0.01])
    actual = _resample_(grid, values, target, fwhm)[0]
    half = fwhm[0] / 2
    sigma = half / np.sqrt(np.log(2))
    mask = (grid > target[0] - half) & (grid < target[0] + half)
    x = grid[mask]
    weights = np.exp(-((x - target[0]) ** 2) / sigma**2)
    expected = np.sum(weights * values[mask]) / np.sum(weights)
    assert np.isclose(actual, expected, rtol=0, atol=1e-15)
    assert np.isclose(np.exp(-(half**2) / sigma**2), 0.5, rtol=0, atol=1e-15)
    print("PASS Gaussian FWHM equation and normalization")

    # 2. Closed-form simple linear regression, r2 and raw fitted depth.
    wl = np.arange(2.18, 2.231, 0.001)
    reference = 0.85 + 0.12 * (wl - 2.205) ** 2 + rng.normal(0, 0.002, len(wl))
    endpoints = [2.18, 2.19, 2.22, 2.23]
    pre = _precompute_feature(reference, wl, endpoints)
    x = pre["con_"]
    n = len(x)
    det = n * np.dot(x, x) - x.sum() ** 2
    y = 1.7 * x + 0.04 + rng.normal(0, 0.003, n)
    k0 = (n * np.dot(x, y) - x.sum() * y.sum()) / det
    k1 = (np.dot(x, x) * y.sum() - x.sum() * np.dot(x, y)) / det
    r2, depth = _fit_r2_depth(y.reshape(1, -1), x, pre["B"], pre["depth_factor"])
    y_fit = k0 * x + k1
    expected_r2 = np.sum((y_fit - y.mean()) ** 2) / np.sum((y - y.mean()) ** 2)
    # Algebraic forms are equivalent, but the production reduction order can
    # differ by floating-point roundoff (about 2.3e-11 in this fixture).
    assert np.isclose(r2[0], expected_r2, rtol=0, atol=1e-9)
    assert np.isclose(depth[0], pre["depth_factor"] * k0, rtol=0, atol=1e-12)
    print("PASS closed-form k0/k1, r2 and raw-depth equations")

    # 3. Three-point parabolic vertex on an exact parabola.
    # Use constant endpoint reflectance so continuum removal is exactly
    # neutral, and place a known parabola only inside the feature window.
    reflectance = np.ones_like(wl)
    feature = (wl > 2.19) & (wl < 2.22)
    reflectance[feature] = 0.05 * (wl[feature] - 2.20525) ** 2 + 0.8
    center = _get_quadratic_center(reflectance.reshape(1, -1), wl, endpoints, np.array([True]))[0]
    m = int(np.argmin(reflectance))
    x1, x2, x3 = wl[m - 1 : m + 2]
    y1, y2, y3 = reflectance[m - 1 : m + 2]
    expected_center = -0.5 * (
        (y2 - y1) * (x3**2 - x2**2) - (y3 - y2) * (x2**2 - x1**2)
    ) / ((y3 - y2) * (x2 - x1) - (y2 - y1) * (x3 - x2))
    assert np.isclose(center, 2.20525, rtol=0, atol=1e-9)
    assert np.isclose(center, expected_center, rtol=0, atol=1e-9)
    print("PASS three-point parabolic vertex equation")

    # 4. Aggregation identities used by the model.
    weights = np.array([0.5, 0.3, 0.2])
    fits = np.array([0.9, 0.8, 0.7])
    depths = np.array([0.1, 0.2, 0.3])
    weighted_fit = np.sum(weights * fits)
    weighted_depth = np.sum(weights * depths)
    fit_depth = np.sum(weights * fits * depths)
    assert not np.isclose(fit_depth, weighted_fit * weighted_depth)
    print("PASS Q = sum(w*r2*d) is distinct from F*D")

    print("ALL MATHEMATICAL MODEL CHECKS PASSED")


if __name__ == "__main__":
    main()
