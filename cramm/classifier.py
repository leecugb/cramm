#!/usr/bin/env python
# coding: utf-8
"""
MICA spectral analysis core
===========================
Pure core for per-pixel mineral discrimination: given a spectral cube +
wavelengths + rule library, produce raw classification results
(FIT / DEPTH / NUM / mus_center / chl_center / cal_center), **without** any coloring or image packaging.

Dependencies: numpy only (top level). Heavy dependencies (pandas) are lazily
imported at the point of use, so multiprocessing workers that merely import
this module load only numpy, keeping spawn overhead low.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import sys
import tempfile
import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np


# =============================================================================
# Exception types
# =============================================================================

class InvalidRangeError(Exception):
    """The feature's continuum window covers no valid channels."""

    def __str__(self):
        return "the spectrum range of this feature contains no channels"


class InvalidLeftEndPointError(Exception):
    """The left-endpoint window covers no channels."""

    def __str__(self):
        return "this left end point range covers no channels"


class InvalidRightEndPointError(Exception):
    """The right-endpoint window covers no channels."""

    def __str__(self):
        return "this right end point range covers no channels"


# =============================================================================
# Classification result data contract (no color/image, consumed by ResultRenderer)
# =============================================================================

@dataclass
class ClassificationResult:
    """Raw per-pixel classification results."""
    fit: np.ndarray          # [r*c] best (argmax) weighted fit per pixel
    depth: np.ndarray        # [r*c] best fit*depth (fd) per pixel
    num: np.ndarray          # [r*c] uint8 argmax mineral index
    mus_center: np.ndarray   # [r*c] muscovite absorption center (0 if absent)
    chl_center: np.ndarray   # [r*c] chlorite 2250nm absorption center (0 if absent)
    cal_center: np.ndarray   # [r*c] carbonate 2330nm absorption center (0 if absent)
    r: int
    c: int
    index: List[str]         # mineral names (order matches num indices)
    index_d: Dict[str, int]


# Muscovite-group minerals (used for mus_center quadratic fitting)
MUSCOVITE_MINERALS = [
    "muscovite_lowAl",
    "muscovite_medAl",
    "muscovite_medhighAl",
    "muscovite_Fe-rich",
    "illite_imt1",
    "illite_gds4",
    "kaolinite.5+muscoviteMedAl.5",
    "kaolinite.5+muscoviteMedhighAl.5",
    "kaolinite+muscovite_mix_intimate",
    "clinochlore_Fe.3+muscovite.7",
    "calcite.5+muscoviteMedHiAl.5",
    "calcite.5+muscoviteMedAl.5",
    "calcite.3+muscoviteLowAl.7",
]

# Pure-chlorite minerals (used for chl_center quadratic fitting of the 2250 nm
# Fe-OH band). Only the four pure references are included: the chlorite-bearing
# mixture rules are excluded on purpose — their band position reflects the
# mixture, not the chlorite composition (chl13 application boundary: band-
# position inversion is quantitative only for chlorite >= ~50%). thuringite
# carries the Fe-richest window ([2.256, 2.266), 1nm rule library), extending the
# arbitration sequence beyond clinochlore_Fe's [2.252, 2.256).
CHLORITE_MINERALS = [
    "chlorite_lowFe",
    "clinochlore",
    "clinochlore_Fe",
    "thuringite",
]

# Carbonate minerals (used for cal_center quadratic fitting of the 2330 nm
# C-O band). The family carries the full member list for the center layer;
# ARBITRATION runs per abundance tier (v1.5.0): the abundant pair competes
# among themselves and the plain pair among themselves — within each pair the
# windows are disjoint ([2.308, 2.328) vs [2.334, 2.350)), so band position
# arbitrates dolomite<->calcite flips while the abundant/plain axis stays
# decided by fit alone (a pixel can never flip across tiers: the two
# sub-family lists are disjoint arbitration groups). The 6 nm dead zone
# [2.328, 2.334) between the windows keeps siderite-ish centers (~2327 nm
# anchor) with their argmax winner; carbonate_Fe_bearing and
# calcite.5+dolomite.5 stay windowless (position cannot discriminate the
# former from calcite; the latter's blend center lands in the dead zone by
# design). The continuous cal_center layer remains the product line's
# primary value (7-anchor carbonate band-position sequence;
# aragonite/magnesite silently classified as dolomite become detectable via
# their <2320 nm centers).
# serpentine_antigorite_or_calcite+dolomite is excluded on purpose: its
# reference is antigorite, not a carbonate.
CARBONATE_MINERALS = [
    "calcite_abundant",
    "calcite",
    "dolomite_abundant",
    "dolomite",
    "carbonate_Fe_bearing",
    "calcite.5+dolomite.5",
]

# Carbonate arbitration sub-families (per abundance tier, v1.5.0): classify
# calls _reassign_by_absorption_center once per sub-family instead of once
# for the whole CARBONATE_MINERALS group.
CARBONATE_ABUNDANT_MINERALS = [
    "calcite_abundant",
    "dolomite_abundant",
]
CARBONATE_PLAIN_MINERALS = [
    "calcite",
    "dolomite",
]


# =============================================================================
# Pure-function algorithm layer (zero state dependency)
# =============================================================================

def _read_1nm_npz(filename: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Read the splib07 rule-face 1 nm reference bundle (rf77_splib07_1nm.npz).

    Returns (grid, rule_names, rule_labels, spectra) directly from the npz:
      - grid: [2151] float64, 0.350 .. 2.500 um in 1 nm steps
      - rule_names: [77] object(str), one entry per rule (matches rf.keys() order
        in temp_rf_notfeatures_renamed.json — the 1nm rule library)
      - rule_labels: [77] object(str), provenance tags (record / [AMX] /
        [alias] / synth)
      - spectra: [77, 2151] float64, rows aligned to rule_names; out-of-range
        entries are NaN and are naturally dropped by _resample_'s ``temp > 0``
        filter exactly like deletion zeros in legacy splib06b.
    """
    z = np.load(filename, allow_pickle=False)
    grid = np.asarray(z["grid"], dtype="float64")
    rule = np.asarray(z["rule"], dtype=object)
    label = np.asarray(z["label"], dtype=object)
    spectra = np.asarray(z["spectra"], dtype="float64")
    if spectra.shape != (len(rule), len(grid)):
        raise ValueError(
            f"{filename}: spectra shape {spectra.shape} inconsistent with "
            f"rule ({len(rule)}) x grid ({len(grid)})")
    if len(grid) < 2 or not (np.diff(grid) > 0).all():
        raise ValueError(f"{filename}: master grid is not strictly increasing")
    return grid, rule, label, spectra


def _resample_(bands: np.ndarray, data: np.ndarray, w: np.ndarray, bp: np.ndarray) -> np.ndarray:
    """
    Gaussian-resample spectral data onto target bands.

    For each target band (center x, FWHM y):
      - Window: strict open interval (x - y/2, x + y/2), i.e. the full width at
        half maximum (window-edge weight is exactly 0.5)
      - Weight: Gaussian wt = exp(-(lambda-x)^2 / sigma^2), sigma = ((y/2)^2 / ln2) ** 0.5
      - Invalid values: specpr deletion markers were already set to 0 at read
        time, so only samples > 0 participate in the weighted average here;
        if the window has no valid sample the output is NaN (downstream
        _diagnostic_feature excludes NaN bands)

    Performance optimizations:
      - data.astype("double") hoisted out of the band loop (the original
        implementation repeated it 285 times per record)
      - Window located via searchsorted binary search O(log n), replacing the
        per-band full-array boolean scan O(n)
      - Fast-path precondition: the positive part of bands is strictly
        increasing (all non-increasing points come from the leading/trailing
        padding segments zeroed by deletion markers),
        and every window lower bound x - y/2 > 0 (always true for EMIT bands;
        a window can never contain a 0-wavelength padding point); otherwise
        fall back to the original boolean path. Both paths sum over exactly
        the same subset of elements in the same order.

    Bit-exactness note (2026-09-02 audit): the vectorized sigma computation
    ``(halfs**2 / np.log(2)) ** 0.5`` is special-cased by numpy's pow ufunc
    to ``sqrt``, while the original per-band scalar ``** 0.5`` used libm
    ``pow``; the two can differ by 1 ulp at isolated bands (observed: EMIT
    band 231, FWHM 8.734 nm -> 24/77x285 resampled values differ by
    1.11e-16, all other bands bit-identical). The same 1-ulp caveat applies
    to the fast-vs-slow path equivalence. This is inconsequential for
    classification (relative magnitude 1e-16 on reference spectra) and does
    not affect the golden regression chain, which is produced and verified
    with this same implementation -- but the historical "bit-exact vs the
    pre-optimization version" claim holds only up to this 1-ulp exception.
    """
    data64 = data.astype("double")  # hoist once (the original repeated it inside the band loop)
    res1 = np.empty(len(w), dtype="float64")
    halfs = bp / 2
    sigmas = (halfs**2 / np.log(2)) ** 0.5

    # Fast-path conditions: all window lower bounds > 0, and the positive part
    # of bands is strictly increasing
    fast = bool((w - halfs).min() > 0)
    sb = sd = None
    if fast:
        posb = bands > 0
        sb_cand = bands[posb]
        fast = bool(len(sb_cand) > 0 and (np.diff(sb_cand) > 0).all())
        if fast:
            sb = sb_cand
            sd = data64[posb]

    for j in range(len(w)):
        x = w[j]
        half = halfs[j]
        if fast:
            # Strict open interval (x-half, x+half): lo = first > x-half, hi = first >= x+half
            lo = np.searchsorted(sb, x - half, side="right")
            hi = np.searchsorted(sb, x + half, side="left")
            win_b = sb[lo:hi]
            temp = sd[lo:hi]
        else:
            mask = (bands < x + half) & (bands > x - half)
            win_b = bands[mask]
            temp = data64[mask]
        if len(temp) == 0:
            res1[j] = np.nan
            continue
        sigma = sigmas[j]
        xx = win_b - x
        wt = np.exp(-1 * xx**2 / sigma**2)
        pos = temp > 0
        wt = wt[pos]
        temp = temp[pos]
        if len(temp) == 0:
            res1[j] = np.nan
        else:
            res1[j] = (temp * wt).sum() / wt.sum()
    return res1


def _get_quadratic_center(
    spectrum: np.ndarray, wl: np.ndarray, CONTINUUM_ENDPTS: List[float], mask_const: np.ndarray
) -> np.ndarray:
    mask = (wl <= CONTINUUM_ENDPTS[3]) & (wl >= CONTINUUM_ENDPTS[0])
    mask_left_end = (wl <= CONTINUUM_ENDPTS[1]) & (wl >= CONTINUUM_ENDPTS[0])
    mask_right_end = (wl <= CONTINUUM_ENDPTS[3]) & (wl >= CONTINUUM_ENDPTS[2])
    x_av = np.array([wl[mask_left_end].mean(), wl[mask_right_end].mean()], dtype="float64")
    # rows style (same principle as _diagnostic_feature): fetch data only on
    # the rows alive in mask_const; a single np.ix_ copy replaces "copy all N
    # columns then take a row subset"; same elements in the same order, so the
    # result is bit-exact identical.
    rows = np.nonzero(mask_const)[0]
    idx = np.nonzero(mask)[0]
    idx_l = np.nonzero(mask_left_end)[0]
    idx_r = np.nonzero(mask_right_end)[0]
    y_av = np.array(
        [spectrum[np.ix_(rows, idx_l)].mean(1), spectrum[np.ix_(rows, idx_r)].mean(1)],
        dtype="float64",
    ).T
    con = y_av[:, [0]] + (y_av[:, [1]] - y_av[:, [0]]) / (x_av[1] - x_av[0]) * (
        wl[mask].reshape([1, -1]) - x_av[0]
    )
    con = spectrum[np.ix_(rows, idx)] / con
    index = con.argmin(1)
    mas = ((index - 1) >= 0) & (index + 1 < mask.sum())
    con = con[mas]
    x2 = wl[mask][index[mas]]
    x1 = wl[mask][index[mas] - 1]
    x3 = wl[mask][index[mas] + 1]
    r, c = con.shape
    y2 = con.ravel()[index[mas] + c * np.arange(r)]
    y1 = con.ravel()[index[mas] - 1 + c * np.arange(r)]
    y3 = con.ravel()[index[mas] + 1 + c * np.arange(r)]
    # errstate: a collinear triple makes the vertex denominator 0 -> the
    # division legitimately produces inf/nan, folded to NaN just below
    with np.errstate(invalid="ignore", divide="ignore"):
        temp = ((y2 - y1) * (x3**2 - x2**2) - (y3 - y2) * (x2**2 - x1**2)) / (
            (y3 - y2) * (x2 - x1) - (y2 - y1) * (x3 - x2)
        ) / 2
    cen = np.zeros(len(index)) * np.nan
    cen[mas] = -1 * temp
    # The parabola-vertex denominator is 0 for collinear triples (noise /
    # flat-topped spectra), yielding +-inf: fold every non-finite vertex to
    # NaN so the caller's NaN->0 fold catches them too (an inf would survive
    # into mus_center and corrupt the tiered coloring downstream)
    cen[~np.isfinite(cen)] = np.nan
    center = np.zeros(len(spectrum)) * np.nan
    center[mask_const] = cen
    return center


def _reassign_by_absorption_center(
    im: np.ndarray,
    FIT: np.ndarray,
    fit_nan: np.ndarray,
    mus_c: np.ndarray,
    spectrum1: np.ndarray,
    wl: np.ndarray,
    rf: Dict,
    index_d: Dict[str, int],
    fit_pos: np.ndarray,
    family: List[str],
) -> None:
    """
    Wavelength-based reassignment among the windowed members of ONE
    mineral family. ``family`` locks the arbitration group to the
    caller's member list (the pure muscovites / chlorites / carbonates);
    within it, only rules carrying
    ``diagnostic_features[0]["absorption_center_range"]`` participate
    (windowless members — the illites, the kaolinite/calcite x muscovite
    mixtures, carbonate_Fe_bearing, calcite.5+dolomite.5 — are never
    arbitrated). The three bundled families are:

      - muscovite: four pure rules with seamless windows around the
        2.2 um Al-OH band;
      - chlorite: four pure rules with deliberately overlapping windows
        around the 2250 nm Fe-OH band;
      - carbonate: two per-tier pairs (abundant / plain) with disjoint
        windows around the 2330 nm C-O band (v1.5.0: band position
        arbitrates dolomite<->calcite within a tier; the abundant/plain
        axis remains fit-decided because the tier groups are disjoint);

    Inter-family segregation is STRUCTURAL, not emergent: each call can
    only ever reassign among its own family's rules, no matter what
    windows a (custom) rule library carries. The ``mus_c > 0`` member
    gate and the ~25 nm (mus-chl) / ~42 nm (chl-cal) window spacing
    remain as defense in depth, but the locked group is what guarantees
    a muscovite pixel can never flip to a chlorite rule.

    For each pixel whose best match ``im`` is one of the family's
    windowed rules, the quadratic-fit absorption center ``mus_c``
    arbitrates the final attribution:

      - center invalid (0 after the NaN->0 fold) or outside every range
        -> keep the original match (conservative);
      - center inside exactly one rule's left-closed right-open ``[lo, hi)``
        range, different from the current match, and that rule itself
        accepted the pixel (its fit is not NaN) -> reassign: ``im`` follows
        the target rule and ``mus_c`` is refitted once with the target
        rule's feat0 continuum endpoints (single pass, no iteration);
      - center inside several overlapping ranges -> ambiguous, keep the
        original. The bundled chlorite windows exploit exactly this: their
        overlaps are tolerance zones where the intermediate
        composition keeps its argmax attribution. (The pre-v1.5.0
        carbonate duplicate-window scheme pushed this to the extreme —
        identical abundant+plain windows made every in-window center
        ambiguous, a declarative zero-flip; v1.5.0 replaced it with
        per-tier pair arbitration, see CARBONATE_ABUNDANT_MINERALS /
        CARBONATE_PLAIN_MINERALS.)

    ``classify`` calls this helper four times per segment: with
    ``mus_center`` + MUSCOVITE_MINERALS, ``chl_center`` +
    CHLORITE_MINERALS, and ``cal_center`` + CARBONATE_ABUNDANT_MINERALS /
    CARBONATE_PLAIN_MINERALS (one call per carbonate abundance tier).

    Custom rule libraries opt in per family: append the new rule's name
    to the corresponding module-level family list AND give it
    ``absorption_center_range``; a window on a rule outside every family
    list is ignored (the family lock takes precedence).

    All decisions are computed from the pre-reassignment state in one
    vectorized pass (no sequential dependence between pixels), and this
    helper is the single implementation shared by the serial and parallel
    paths -> bit-exact identical in both.

    In-place: ``im`` and ``mus_c`` are modified; ``FIT`` / ``fit_nan`` are
    read-only (the caller re-derives FIT_/DEPTH_/NUM_ from the updated im).
    """
    group = []  # (column index, rule name, lo, hi), in family-list order
    for name in family:
        i = index_d.get(name)
        if i is None:
            continue  # a custom rule library may lack some built-in members
        feats = rf[name].get("diagnostic_features") or []
        if not feats:
            continue
        rng = feats[0].get("absorption_center_range")
        if rng is None:
            continue  # windowless family member: never arbitrated
        group.append((i, name, float(rng[0]), float(rng[1])))
    if len(group) < 2:
        return
    gidx = np.array([g[0] for g in group])
    member = np.isin(im, gidx) & fit_pos & (mus_c > 0)
    if not member.any():
        return
    cen = mus_c[member]
    hits = np.stack([(cen >= lo) & (cen < hi) for _, _, lo, hi in group], axis=1)
    uniq = hits.sum(1) == 1
    if not uniq.any():
        return
    rows = np.nonzero(member)[0][uniq]          # pixel rows within the segment
    tgt_local = hits[uniq].argmax(1)            # unique hit, as group index
    # Target must (a) differ from the current match, (b) have accepted the
    # pixel (fit not NaN), (c) have a positive fit -- a zero-but-not-NaN fit
    # (custom rules with min_weighted_fit=None) would reassign the pixel into
    # a state indistinguishable from background downstream (fit_pos semantic)
    ok = (gidx[tgt_local] != im[rows]) & ~fit_nan[rows, gidx[tgt_local]] & (
        FIT[rows, gidx[tgt_local]] > 0
    )
    if not ok.any():
        return
    rows, tgt_local = rows[ok], tgt_local[ok]
    im[rows] = gidx[tgt_local]
    # Refit mus_c once per target rule with that rule's own feat0 endpoints,
    # so the stored center is consistent with the final attribution
    for local_i in np.unique(tgt_local):
        name = group[local_i][1]
        mask = np.zeros(len(im), dtype=bool)
        mask[rows[tgt_local == local_i]] = True
        cen2 = _get_quadratic_center(
            spectrum1, wl,
            rf[name]["diagnostic_features"][0]["continuum_endpoints"],
            mask,
        )
        # A failed refit (collinear triple -> NaN) must not discard the
        # pre-reassignment center: fall back to it so mus_center stays
        # consistent with the pixel having had a valid absorption center
        newc = cen2[mask]
        bad = ~np.isfinite(newc)
        newc[bad] = mus_c[mask][bad]
        mus_c[mask] = newc


def _precompute_feature(reference: np.ndarray, wl: np.ndarray, CONTINUUM_ENDPTS: List[float]) -> dict:
    """
    Precompute a feature's **reference-side constants** (the parts independent
    of the input spectrum), speeding up repeated single-spectrum evaluation.

    The expressions and operation order are exactly the same as the inline
    reference-side computations in _diagnostic_feature / _get_fit (only moved
    earlier to compile time); per-element spectrum-side operations are
    unaffected -> bit-exact identical.

    Returned dict:
      exc          -- endpoint exception decidable at compile time
                      (InvalidRangeError etc.), None if absent; at evaluation
                      time it is raised at the same position as a **new
                      instance of the same type** (repeatedly raising a shared
                      instance would accumulate __traceback__ frames, growing
                      the chain without bound in long sessions)
      idx/idx_l/idx_r -- integer column indices of the feature window /
                      left endpoint / right endpoint
      x_av         -- mean wavelengths of the left/right endpoints [2]
      wdiff        -- wl[mask] - x_av[0] (continuum-line abscissa offset, 1-D)
      con_         -- reference continuum-removed curve
      B            -- closed-form least-squares matrix [2, n]; None when
                      singular (det==0)
      depth_factor -- (1 - con_.min()) or (con_.max() - 1) (absorption/emission
                      branch, decided at compile time)
    """
    mask = (wl <= CONTINUUM_ENDPTS[3]) & (wl >= CONTINUUM_ENDPTS[0])
    mask = mask & (~np.isnan(reference))
    if not mask.any():
        return {"exc": InvalidRangeError()}
    mask_left_end = (wl <= CONTINUUM_ENDPTS[1]) & (wl >= CONTINUUM_ENDPTS[0])
    if not mask_left_end.any():
        return {"exc": InvalidLeftEndPointError()}
    mask_right_end = (wl <= CONTINUUM_ENDPTS[3]) & (wl >= CONTINUUM_ENDPTS[2])
    if not mask_right_end.any():
        return {"exc": InvalidRightEndPointError()}
    idx = np.nonzero(mask)[0]
    idx_l = np.nonzero(mask_left_end)[0]
    idx_r = np.nonzero(mask_right_end)[0]

    x_av = np.array([wl[mask_left_end].mean(), wl[mask_right_end].mean()], dtype="float64")
    r_l = reference[mask_left_end]
    r_r = reference[mask_right_end]
    y_r_av = np.array(
        [r_l[~np.isnan(r_l)].mean(), r_r[~np.isnan(r_r)].mean()], dtype="float64"
    )
    con_ = y_r_av[0] + (y_r_av[1] - y_r_av[0]) / (x_av[1] - x_av[0]) * (wl[mask] - x_av[0])
    con_ = reference[mask] / con_
    # Closed-form 2x2 least-squares matrix (matches the closed-form solution in
    # mica_app.py, including the det==0 singularity guard)
    n = len(con_)
    Scc = np.dot(con_, con_)
    Sc = con_.sum()
    det = Scc * n - Sc * Sc
    if det == 0:
        B = None
    else:
        B = np.empty((2, n), dtype="float64")
        B[0, :] = (n * con_ - Sc) / det
        B[1, :] = (Scc - Sc * con_) / det
    if con_.mean() < 1:
        depth_factor = 1 - con_.min()
    else:
        depth_factor = con_.max() - 1
    return {
        "exc": None,
        "idx": idx,
        "idx_l": idx_l,
        "idx_r": idx_r,
        "x_av": x_av,
        "wdiff": wl[mask] - x_av[0],
        "con_": con_,
        "B": B,
        "depth_factor": depth_factor,
    }


# Process- and thread-local r2-chain buffer (independent in the main process,
# in each worker process, and in every thread). Grows on demand and never
# shrinks; slice views feed out= in-place operations -- collapsing the 6 large
# temporaries of the r2 chain into 1 persistent buffer, eliminating
# per-feature-call bulk allocation and first-touch page faults
# (microbenchmark: this chain 2.1x).
# Threading: the buffer is scratch space whose contents are fully rewritten
# inside each _fit_r2_depth call (no values survive between calls), so
# thread-local storage makes concurrent classify_spectrum / classify calls
# from multiple threads of the same process safe. Multiprocessing workers
# are independent processes (spawn) and were never affected.
_R2_TLS = threading.local()


def _r2_buf(m: int, n: int) -> np.ndarray:
    """Return this thread's persistent buffer view of shape (m, n) (reused
    across calls, contents rewritten each time)."""
    buf = getattr(_R2_TLS, "buf", None)
    if buf is None:
        _R2_TLS.buf = buf = np.empty((max(m, 1), max(n, 1)))
    elif buf.shape[0] < m or buf.shape[1] < n:
        _R2_TLS.buf = buf = np.empty((max(m, buf.shape[0]), max(n, buf.shape[1])))
    return buf[:m, :n]


def _fit_r2_depth(
    con: np.ndarray, con_: np.ndarray, B: Optional[np.ndarray], depth_factor: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Closed-form 2x2 least squares + r2/depth chain (the single implementation
    shared by _diagnostic_feature and _get_fit, avoiding divergence of two
    copies of bit-exact-sensitive code).

    con = k0*con_ + k1; r2 is the goodness of fit, depth = depth_factor*k0.
    r2-chain buffer reuse: y_fit -> difference -> square -> sum: the original
    implementation's 6 large (M2,n) temporaries are collapsed into 1
    process-level persistent buffer (_r2_buf), eliminating per-call bulk
    allocation / first-touch page faults (microbenchmark: this chain 2.1x).
    Bit-exactness preserved: all are element-wise IEEE operations (out=
    in-place writes are safe); the input sequence of the sum(1) reduction is
    element-for-element identical to the original (bit-exactness of reducing
    over a strided cross-row view is empirically verified); np.square == **2;
    con_mf hoisting reused (the original copied con[mask_fit] twice, with
    identical values).
    """
    if B is None:
        k0 = np.zeros(len(con)) * np.nan
        k1 = np.zeros(len(con)) * np.nan
    else:
        # np.einsum (pure C loop, no BLAS): each pixel's k0/k1 depends only on
        # its own row -- independent of the row count m, the row-subset
        # composition, and the BLAS thread count. The previous B.dot(con.T)
        # went through BLAS dgemm, whose kernel/blocking selection varies with
        # m and thread pool (empirically: MKL2025 switches kernels below
        # m~150 and reblocks under multithreading), so identical pixels could
        # receive ulp-different k0/k1 in subset vs full calls -- breaking the
        # bit-exactness of the alive-pixel restriction vs full computation
        # and of the serial (default threads) vs parallel (1-thread workers)
        # paths. einsum costs only ~1.2-1.9x the dgemm call here.
        k = np.einsum("mj,kj->mk", con, B)
        k0 = k[:, 0]
        k1 = k[:, 1]
    mask_fit = k0 > 0
    con_mf = con[mask_fit]
    cm = con_mf.mean(1)
    buf = _r2_buf(len(cm), con.shape[1])
    np.multiply(k0[mask_fit].reshape([-1, 1]), con_.reshape([1, -1]), out=buf)
    buf += k1[mask_fit].reshape([-1, 1])
    buf -= cm.reshape([-1, 1])
    np.square(buf, out=buf)
    ss_reg = buf.sum(1)
    np.subtract(con_mf, cm.reshape([-1, 1]), out=buf)
    np.square(buf, out=buf)
    ss_tot = buf.sum(1)
    r2 = np.zeros(len(con)) * np.nan
    r2[mask_fit] = ss_reg / ss_tot
    depth = np.zeros(len(con)) * np.nan
    depth[mask_fit] = depth_factor * k0[mask_fit]
    return r2, depth


def _diagnostic_feature(
    spectrum: np.ndarray,
    reference: np.ndarray,
    wl: np.ndarray,
    CONTINUUM_ENDPTS: List[float],
    FEATURE_WEIGHT: float,
    CONTINUUM_CONSTRAINTS: Optional[List] = None,
    FIT_CONSTRAINTS: Optional[float] = None,
    DEPTH_CONSTRAINTS: Optional[List] = None,
    rows: Optional[np.ndarray] = None,
    pre: Optional[dict] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Single diagnostic feature: continuum removal -> closed-form least squares
    -> weighted r2 / depth.

    Returns
    -------
    r2*weight, depth*weight, r2*weight*depth (raw), depth (raw, unweighted)
        All are N-length arrays; rejected/non-participating pixels are NaN.
        The 4th value serves the not_rel relative threshold and the depth-ratio
        constraint (physical depth comparison, unrelated to scoring weights).

    rows : np.ndarray, optional
        Indices of pixels participating in this evaluation (int array, "alive
        pixel restriction"). None = all pixels. Pixels already rejected by
        earlier features in the discrimination chain have no effect on the
        final verdict for this mineral (NaN propagates through accumulation and
        constraints), so they are skipped. All computations are row-independent
        (mean/sum along axis=1, element-wise operations, and a BLAS-free
        np.einsum normal-equation solve in _fit_r2_depth -- BLAS dgemm results
        vary with the row count and thread pool), so the subset result is
        bit-exact identical to the full computation; the output is still an
        N-length array with NaN at non-participating positions.

    pre : dict, optional
        Compiled product of _precompute_feature (reference-side constants).
        None = compute on the spot (the default path, used by the main
        classify(); the operation sequence is exactly the same as the compiled
        version).
    """
    if CONTINUUM_CONSTRAINTS is None:
        CONTINUUM_CONSTRAINTS = [None] * 8
    if DEPTH_CONSTRAINTS is None:
        DEPTH_CONSTRAINTS = [None, None]

    n_all = len(spectrum)
    if rows is None:
        rows = np.arange(n_all)

    # Reference-side constants (masks / endpoint statistics / con_ / B / depth
    # factor): compiled on the spot with the same operation order when pre is
    # not given.
    # Contract: when pre is provided, reference/CONTINUUM_ENDPTS may be None
    # (compiled path), and neither may be touched afterwards -- all
    # reference-side information comes from pre.
    if pre is None:
        pre = _precompute_feature(reference, wl, CONTINUUM_ENDPTS)
    if pre["exc"] is not None:
        # Raise a new instance of the same type: repeatedly raising a shared
        # instance would accumulate __traceback__ frames
        raise type(pre["exc"])()
    idx = pre["idx"]
    idx_l = pre["idx_l"]
    idx_r = pre["idx_r"]
    x_av = pre["x_av"]
    wdiff = pre["wdiff"]
    con_ = pre["con_"]
    B = pre["B"]
    depth_factor = pre["depth_factor"]

    y_av = np.array(
        [spectrum[np.ix_(rows, idx_l)].mean(1), spectrum[np.ix_(rows, idx_r)].mean(1)], dtype="float64"
    ).T

    mask_const = np.ones(len(rows), dtype="bool")
    if CONTINUUM_CONSTRAINTS[0] is not None:
        mask_const = mask_const & (y_av[:, 0] >= CONTINUUM_CONSTRAINTS[0])
    if CONTINUUM_CONSTRAINTS[1] is not None:
        mask_const = mask_const & (y_av[:, 0] <= CONTINUUM_CONSTRAINTS[1])
    if CONTINUUM_CONSTRAINTS[2] is not None:
        mask_const = mask_const & ((y_av.mean(1)) >= CONTINUUM_CONSTRAINTS[2])
    if CONTINUUM_CONSTRAINTS[3] is not None:
        mask_const = mask_const & ((y_av.mean(1)) <= CONTINUUM_CONSTRAINTS[3])
    if CONTINUUM_CONSTRAINTS[4] is not None:
        mask_const = mask_const & (y_av[:, 1] >= CONTINUUM_CONSTRAINTS[4])
    if CONTINUUM_CONSTRAINTS[5] is not None:
        mask_const = mask_const & (y_av[:, 1] <= CONTINUUM_CONSTRAINTS[5])
    # errstate: a zero left-endpoint reflectance legitimately yields inf/nan in
    # the ratio, which then correctly fails the >= / <= comparisons (the
    # warnings are noise; same rationale as the depth-ratio constraint below)
    with np.errstate(invalid="ignore", divide="ignore"):
        if CONTINUUM_CONSTRAINTS[6] is not None:
            mask_const = mask_const & ((y_av[:, 1] / y_av[:, 0]) >= CONTINUUM_CONSTRAINTS[6])
        if CONTINUUM_CONSTRAINTS[7] is not None:
            mask_const = mask_const & ((y_av[:, 1] / y_av[:, 0]) <= CONTINUUM_CONSTRAINTS[7])

    con = y_av[mask_const][:, [0]] + (y_av[mask_const][:, [1]] - y_av[mask_const][:, [0]]) / (
        x_av[1] - x_av[0]
    ) * wdiff.reshape([1, -1])
    # Column-first indexing: select columns (~30) before rows, avoiding the
    # wasted N x 285 copy of row-first selection; the result is bit-exact
    # identical to spectrum[mask_const][:, mask]. With rows restriction, a
    # single np.ix_ copy of M x 30 is used.
    scol = spectrum[np.ix_(rows, idx)]
    con = scol[mask_const] / con
    # Closed-form least squares + r2/depth chain (single implementation shared
    # with _get_fit, see _fit_r2_depth)
    r2, depth = _fit_r2_depth(con, con_, B, depth_factor)
    mask_c = np.ones(len(con), dtype="bool")
    if FIT_CONSTRAINTS is not None:
        mask_c = mask_c & (r2 >= FIT_CONSTRAINTS)
    if DEPTH_CONSTRAINTS[0] is not None:
        mask_c = mask_c & (depth >= DEPTH_CONSTRAINTS[0])
    if DEPTH_CONSTRAINTS[1] is not None:
        mask_c = mask_c & (depth <= DEPTH_CONSTRAINTS[1])
    r2[~mask_c] = np.nan
    depth[~mask_c] = np.nan
    # Map back to original pixel positions: rows[mask_const] are the original
    # row numbers actually computed this time
    out_rows = rows[mask_const]
    r2_ = np.zeros(n_all) * np.nan
    r2_[out_rows] = r2
    depth_ = np.zeros(n_all) * np.nan
    depth_[out_rows] = depth
    return r2_ * FEATURE_WEIGHT, depth_ * FEATURE_WEIGHT, r2_ * FEATURE_WEIGHT * depth_, depth_


def _get_fit(
    spectrum: np.ndarray, reference: np.ndarray, wl: np.ndarray, CONTINUUM_ENDPTS: List[float],
    rows: Optional[np.ndarray] = None,
    pre: Optional[dict] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fit used for non-features: continuum removal + closed-form least squares,
    returning per-pixel (r2, depth).

    rows : np.ndarray, optional
        Indices of pixels participating in the evaluation (same as the rows of
        _diagnostic_feature). The returned arrays have length len(rows) (all
        pixels when rows=None); row-independent and bit-exact identical.
    pre : dict, optional
        Compiled product of _precompute_feature (reference-side constants).
        None = compute on the spot.
    """
    if rows is None:
        rows = np.arange(len(spectrum))

    # Contract: when pre is provided, reference/CONTINUUM_ENDPTS may be None
    # (compiled path), and neither may be touched afterwards -- all
    # reference-side information comes from pre.
    if pre is None:
        pre = _precompute_feature(reference, wl, CONTINUUM_ENDPTS)
    if pre["exc"] is not None:
        # Raise a new instance of the same type: repeatedly raising a shared
        # instance would accumulate __traceback__ frames
        raise type(pre["exc"])()
    idx = pre["idx"]
    idx_l = pre["idx_l"]
    idx_r = pre["idx_r"]
    x_av = pre["x_av"]
    wdiff = pre["wdiff"]
    con_ = pre["con_"]
    B = pre["B"]
    depth_factor = pre["depth_factor"]

    y_av = np.array(
        [spectrum[np.ix_(rows, idx_l)].mean(1), spectrum[np.ix_(rows, idx_r)].mean(1)], dtype="float64"
    ).T
    con = y_av[:, [0]] + (y_av[:, [1]] - y_av[:, [0]]) / (x_av[1] - x_av[0]) * wdiff.reshape([1, -1])
    con = spectrum[np.ix_(rows, idx)] / con
    # Closed-form least squares + r2/depth chain (single implementation shared
    # with _diagnostic_feature, see _fit_r2_depth)
    r2, depth = _fit_r2_depth(con, con_, B, depth_factor)
    return r2, depth


def _not_absolute_feature(
    spectrum: np.ndarray,
    reference: np.ndarray,
    wl: np.ndarray,
    CONTINUUM_ENDPTS: List[float],
    NOT_FEATURE_FIT_CONSTRAINTS: float,
    NOT_FEATURE_ABSOLUTE_DEPTH_CONSTRAINTS: float,
    rows: Optional[np.ndarray] = None,
    pre: Optional[dict] = None,
) -> np.ndarray:
    """Absolute non-feature: return the **original row numbers** of the pixels
    to be removed (those hit within the rows subset)."""
    if rows is None:
        rows = np.arange(len(spectrum))
    r2, depth = _get_fit(spectrum, reference, wl, CONTINUUM_ENDPTS, rows, pre=pre)
    mask_c = r2 >= NOT_FEATURE_FIT_CONSTRAINTS
    mask_c = mask_c & (depth >= NOT_FEATURE_ABSOLUTE_DEPTH_CONSTRAINTS)
    return rows[mask_c]


def _not_relative_feature(
    spectrum: np.ndarray,
    reference: np.ndarray,
    wl: np.ndarray,
    CONTINUUM_ENDPTS: List[float],
    NOT_FEATURE_FIT_CONSTRAINTS: float,
    RELATIVE_FEATURE_DEPTH: np.ndarray,
    NOT_FEATURE_RELATIVE_DEPTH_CONSTRAINTS: float,
    rows: Optional[np.ndarray] = None,
    pre: Optional[dict] = None,
) -> np.ndarray:
    """Relative non-feature: return the **original row numbers** of the pixels
    to be removed (those hit within the rows subset).

    RELATIVE_FEATURE_DEPTH is an N-length array (raw depth of the 1st
    diagnostic feature), subsetted by rows.
    """
    if rows is None:
        rows = np.arange(len(spectrum))
    r2, depth = _get_fit(spectrum, reference, wl, CONTINUUM_ENDPTS, rows, pre=pre)
    mask_c = r2 >= NOT_FEATURE_FIT_CONSTRAINTS
    mask_c = mask_c & (depth >= (RELATIVE_FEATURE_DEPTH[rows] * NOT_FEATURE_RELATIVE_DEPTH_CONSTRAINTS))
    return rows[mask_c]


def _continuum_constraints_list(cc_obj: dict) -> list:
    """Convert an object-format continuum constraint to an 8-element list."""
    return [
        cc_obj["left_min"],
        cc_obj["left_max"],
        cc_obj["mean_min"],
        cc_obj["mean_max"],
        cc_obj["right_min"],
        cc_obj["right_max"],
        cc_obj["ratio_min"],
        cc_obj["ratio_max"],
    ]


def _judge_reference_entry(
    spectrum: np.ndarray,
    wl: np.ndarray,
    rf: Optional[dict],
    resampled1: Optional[dict],
    chanels: np.ndarray,
    compiled: Optional[dict] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Single-mineral rule evaluation: accumulate diagnostic features -> remove
    via non-features -> depth-ratio constraint -> weighted constraints.

    Alive-pixel restriction (bit-exact identical to full computation):
    pixels rejected by any stage (fit/depth/fd set to NaN) no longer
    participate in subsequent feature computations -- NaN propagates through
    accumulation, comparison, and constraints, so skipping them changes
    neither any alive pixel's values nor the final verdict (all computations
    are row-independent). The first diagnostic feature is always evaluated on
    all pixels.

    compiled : dict, optional
        Compiled product of MicaClassifier._get_compiled_rules (all
        reference-side constants + rule parameters). When provided,
        resampled1/rf are no longer consulted (both may be passed as None),
        and evaluation results are bit-exact identical to the direct path
        (verified by the check_compiled_path.py differential test).
    """
    # When compiled is provided, the reference-side constants are precomputed;
    # no need to consult resampled1.
    #
    # The main reference is keyed by rf["output_name"] (the rule's own name).
    # On the 1 nm rule-face track the rule name is the sole key into
    # resampled1 (int-record aliases no longer exist -- raw int
    # reflectance_record fields are rejected at from_paths). output_name is
    # the canonical lookup that the 1 nm mica_core notebook/standalone used,
    # keeping us bit-exact with that baseline.
    reference = (
        None if compiled is not None else resampled1[rf["output_name"]][chanels]
    )
    fit = np.zeros(len(spectrum))
    depth = np.zeros(len(spectrum))
    fd = np.zeros(len(spectrum))

    alive_rows: Optional[np.ndarray] = None  # None = all pixels (first diagnostic feature)
    # Raw (unweighted) depth of each diagnostic feature: serves the not_rel
    # relative threshold and the depth-ratio constraint -- both are physical
    # depth comparisons, unrelated to scoring accumulation weights (with
    # weight=0 the weighted value is always 0, e.g. mixture mineral diag1).
    _feat_raw: List[np.ndarray] = []

    # Diagnostic features
    diag_feats = compiled["diag"] if compiled is not None else rf["diagnostic_features"]
    for feat in diag_feats:
        if alive_rows is not None and len(alive_rows) == 0:
            break  # no alive pixels: subsequent feature results are all NaN and do not affect the final verdict
        if compiled is not None:
            pre, FEATURE_WEIGHT, CONTINUUM_CONSTRAINTS, FIT_CONSTRAINTS, DEPTH_CONSTRAINTS = feat
            CONTINUUM_ENDPTS = None
        else:
            pre = None
            FEATURE_WEIGHT = feat["feature_weight"]
            CONTINUUM_ENDPTS = feat["continuum_endpoints"]
            CONTINUUM_CONSTRAINTS = _continuum_constraints_list(feat["continuum_constraints"])
            FIT_CONSTRAINTS = feat["fit_constraint"]
            DEPTH_CONSTRAINTS = feat["depth_constraints"]
        r, d, fdd, raw_d = _diagnostic_feature(
            spectrum,
            reference,
            wl,
            CONTINUUM_ENDPTS,
            FEATURE_WEIGHT,
            CONTINUUM_CONSTRAINTS,
            FIT_CONSTRAINTS,
            DEPTH_CONSTRAINTS,
            rows=alive_rows,
            pre=pre,
        )
        fit = fit + r
        depth = depth + d
        fd = fd + fdd
        _feat_raw.append(raw_d)
        # r is NaN both outside the participating rows and at rejected pixels:
        # ~isnan(r) is exactly the current alive set
        alive_rows = np.nonzero(~np.isnan(r))[0]

    # Absolute non-features
    na_feats = compiled["not_abs"] if compiled is not None else rf.get("not_absolute_features", [])
    for feat in na_feats:
        if alive_rows is not None and len(alive_rows) == 0:
            break
        if compiled is not None:
            pre, NOT_FEATURE_FIT_CONSTRAINTS, NOT_FEATURE_ABSOLUTE_DEPTH_CONSTRAINTS = feat
            CONTINUUM_ENDPTS = None
        else:
            pre = None
            reference = resampled1[feat["reflectance_record"]][chanels]
            CONTINUUM_ENDPTS = feat["continuum_endpoints"]
            NOT_FEATURE_FIT_CONSTRAINTS = feat["fit_constraint"]
            NOT_FEATURE_ABSOLUTE_DEPTH_CONSTRAINTS = feat["absolute_depth_constraint"]
        bad = _not_absolute_feature(
            spectrum,
            reference,
            wl,
            CONTINUUM_ENDPTS,
            NOT_FEATURE_FIT_CONSTRAINTS,
            NOT_FEATURE_ABSOLUTE_DEPTH_CONSTRAINTS,
            rows=alive_rows,
            pre=pre,
        )
        fit[bad] = np.nan
        depth[bad] = np.nan
        fd[bad] = np.nan
        if len(bad):
            alive_rows = np.nonzero(~np.isnan(fit))[0]

    # Relative non-features
    nr_feats = compiled["not_rel"] if compiled is not None else rf.get("not_relative_features", [])
    for feat in nr_feats:
        if alive_rows is not None and len(alive_rows) == 0:
            break
        if compiled is not None:
            pre, NOT_FEATURE_FIT_CONSTRAINTS, NOT_FEATURE_RELATIVE_DEPTH_CONSTRAINTS = feat
            CONTINUUM_ENDPTS = None
        else:
            pre = None
            reference = resampled1[feat["reflectance_record"]][chanels]
            CONTINUUM_ENDPTS = feat["continuum_endpoints"]
            NOT_FEATURE_FIT_CONSTRAINTS = feat["fit_constraint"]
            NOT_FEATURE_RELATIVE_DEPTH_CONSTRAINTS = feat["relative_depth_threshold"]
        RELATIVE_FEATURE_DEPTH = _feat_raw[0] if _feat_raw else np.zeros(len(spectrum))
        bad = _not_relative_feature(
            spectrum,
            reference,
            wl,
            CONTINUUM_ENDPTS,
            NOT_FEATURE_FIT_CONSTRAINTS,
            RELATIVE_FEATURE_DEPTH,
            NOT_FEATURE_RELATIVE_DEPTH_CONSTRAINTS,
            rows=alive_rows,
            pre=pre,
        )
        fit[bad] = np.nan
        depth[bad] = np.nan
        fd[bad] = np.nan
        if len(bad):
            alive_rows = np.nonzero(~np.isnan(fit))[0]

    # Depth-ratio constraint (optional): depth of 2nd diagnostic feature /
    # depth of 1st diagnostic feature < threshold, otherwise set NaN.
    # Uses the raw depths _feat_raw (= (1-con_.min) * k0, unweighted) directly
    # -- with weight=0 the weighted value is always 0; uniformly taking raw
    # avoids the double rounding of reconstructing by division. When diag1 is
    # invalid (depth NaN) the pixel does not participate in the verdict
    # (conservatively not rejected).
    _ratio_max = compiled["ratio_max"] if compiled is not None else rf.get("max_depth_ratio_feat1_over_feat0")
    if _ratio_max is not None and len(_feat_raw) >= 2:
        _raw0 = _feat_raw[0]
        _raw1 = _feat_raw[1]
        with np.errstate(invalid="ignore", divide="ignore"):
            _ratio = _raw1 / _raw0
        _valid = (~np.isnan(_raw0)) & (~np.isnan(_raw1)) & (_raw0 > 0)
        _bad = _valid & (_ratio >= _ratio_max)
        fit[_bad] = np.nan
        depth[_bad] = np.nan
        fd[_bad] = np.nan

    # Weighted constraints
    if compiled is not None:
        (
            minimum_weighted_fit,
            minimum_weighted_depth,
            maximum_weighted_depth,
            minimum_fit_depth,
        ) = compiled["wc"]
    else:
        wc = rf["weighted_constraints"]
        minimum_weighted_fit = wc["min_weighted_fit"]
        minimum_weighted_depth = wc["min_weighted_depth"]
        maximum_weighted_depth = wc["max_weighted_depth"]
        minimum_fit_depth = wc["min_fit_depth_product"]

    mask_c = np.ones(len(spectrum), dtype="bool")
    if minimum_weighted_fit is not None:
        mask_c = fit >= minimum_weighted_fit
    if minimum_weighted_depth is not None:
        mask_c = mask_c & (depth >= minimum_weighted_depth)
    if maximum_weighted_depth is not None:
        mask_c = mask_c & (depth <= maximum_weighted_depth)
    if minimum_fit_depth is not None:
        mask_c = mask_c & (fd > minimum_fit_depth)
    fit[~mask_c] = np.nan
    depth[~mask_c] = np.nan
    fd[~mask_c] = np.nan
    return fit, fd


# =============================================================================
# Multiprocessing parallelism: mineral-level workers (module level, picklable under spawn)
# =============================================================================

# Per-worker-process private state (written by the initializer, read by tasks)
_WORKER: Dict = {}

# Serializes the parallel path's BLAS-env override window across threads of
# this process: the env override must stay in effect until the spawned workers
# have imported numpy, and the save/restore pairing would break if two threads
# ran parallel classify concurrently. Unrelated to worker-process isolation
# (spawn already guarantees that).
_PARALLEL_ENV_LOCK = threading.Lock()


def _init_worker(spec_path, resampled1, wl, chanels):
    """At worker startup, attach spec_sel as a read-only memmap, cache
    read-only data, and limit BLAS threads to 1."""
    try:
        from threadpoolctl import ThreadpoolController
        _WORKER["_tpl"] = ThreadpoolController()
        _WORKER["_tpl"].limit(limits=1)
    except Exception:
        try:
            import mkl
            mkl.set_num_threads(1)
        except Exception:
            pass

    _WORKER["spec"] = np.load(spec_path, mmap_mode="r")
    _WORKER["resampled1"] = resampled1
    _WORKER["wl"] = wl
    _WORKER["chanels"] = chanels


def _judge_task(args):
    """Run the rule for a single mineral k on the row range [a_c, b_c),
    returning (k, fit, fd, err)."""
    k, a_c, b_c, value = args
    spectrum1 = _WORKER["spec"][a_c:b_c]  # memmap view, no copy
    try:
        fit, fd = _judge_reference_entry(
            spectrum1, _WORKER["wl"], value, _WORKER["resampled1"], _WORKER["chanels"]
        )
    except (InvalidRangeError, InvalidLeftEndPointError, InvalidRightEndPointError) as e:
        return k, None, None, str(e)  # column stays 0 (same as the serial path on exception); the main process logs it
    return k, fit, fd, None


def _cleanup_temp(path: str) -> None:
    """atexit callback: delete the temporary memmap file at interpreter exit
    (by then the handle is necessarily released)."""
    try:
        os.remove(path)
    except OSError:
        pass


# =============================================================================
# MicaClassifier: spectral analysis core
# =============================================================================

class MicaClassifier:
    """
    Per-pixel mineral discrimination core (1 nm rule-face track).

    Parameters
    ----------
    rf : dict
        Mineral rule library (the "rf" key of temp_rf_notfeatures_renamed.json).
        Every ``reference.reflectance_record`` and every
        ``not_(abs/rel)_features[].reflectance_record`` is a rule-name **string**
        in ``rf.keys()`` -- the rule name is the sole link between the expert
        rules and the reference spectra library. Each rule's ``output_name``
        (also a rule-name string in ``rf.keys()``) is the canonical key under
        which its main reference spectrum is looked up at classification time.
    reference_1nm_bundle : tuple
        ``(grid, rule_names, rule_labels, spectra)`` as returned by
        :func:`_read_1nm_npz`. ``rule_names`` is indexed by rule-name string.

    Notes
    -----
    The cache keys contain only the band configuration (w, bp, wl, chanels),
    not the rule-library contents: **after modifying self.rf /
    self._1nm_bundle in place you must call invalidate_caches()** (or simply
    create a new instance), otherwise classify_spectrum / classify keep using
    the old reference-side constants and results are silently wrong.
    """

    def __init__(
        self,
        rf: Dict,
        reference_1nm_bundle: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    ):
        """
        Parameters
        ----------
        rf : dict
            Mineral rule library. Every ``reflectance_record`` field is a
            rule-name string in ``rf.keys()``; the rule name is the sole key
            into the resampled reference-spectra dict.
        reference_1nm_bundle : tuple
            ``(grid, rule_names, rule_labels, spectra)`` as returned by
            :func:`_read_1nm_npz`.
        """
        self.rf = rf
        # Early rule-count guard: classify() uses uint8 NUM_ indexing, so
        # >256 rules would silently overflow. Fail at construction rather than
        # mid-classify (where the error surfaces only inside a long-running
        # segment loop, with no actionable context).
        if len(rf) > 256:
            raise ValueError(
                f"rule library has {len(rf)} minerals, exceeding the uint8 "
                f"index limit of 256 (NUM_ dtype); trim the rule library or "
                f"upgrade ClassificationResult.num dtype")
        self.track = "1nm"
        self._1nm_bundle = reference_1nm_bundle
        # get_resample memoization cache (keyed by (w content, bp content))
        self._resample_cache_key: Optional[Tuple[bytes, bytes]] = None
        self._resample_cache: Optional[Dict[str, np.ndarray]] = None
        # _get_compiled_rules compilation cache (keyed by (resample_key, wl, chanels))
        self._compiled_key: Optional[tuple] = None
        self._compiled_rules: Optional[Dict[str, dict]] = None
        # rf fingerprint snapshot at cache-build time (best-effort stale-cache
        # detection: catches ``clf.rf = new_dict`` reassignment, but NOT in-place
        # mutation ``clf.rf["x"] = ...`` or ``clf.rf["new"] = ...`` — those still
        # require an explicit invalidate_caches() call; the latter deliberately
        # raises KeyError as a stale-trap, validated by test_cache_contract).
        self._rf_fp_at_build: Optional[int] = None

    def invalidate_caches(self) -> None:
        """
        Clear the resampling and compiled-rule caches.

        The cache keys contain only the band configuration (w, bp, wl,
        chanels), not the rule-library contents -- after modifying self.rf /
        self._1nm_bundle in place you must call this method
        (or simply create a new MicaClassifier instance), otherwise subsequent
        evaluations reuse the old constants and results are silently wrong.
        """
        self._resample_cache_key = None
        self._resample_cache = None
        self._compiled_key = None
        self._compiled_rules = None
        self._rf_fp_at_build = None

    @classmethod
    def from_paths(
        cls,
        rf_path: Optional[str] = None,
        splib_path: Optional[str] = None,
        reference_track: Optional[str] = None,
    ) -> "MicaClassifier":
        """
        Load all resources from paths and construct the classifier
        (self-contained, no manual loading needed).

        Parameters
        ----------
        rf_path : str, optional
            Path to the 1 nm rule library (temp_rf_notfeatures_renamed.json
            or an equivalent rewrite whose not-feature reflectance_record
            fields are rule-name strings). None uses the package-bundled
            copy at cramm/data/temp_rf_notfeatures_renamed.json.
        splib_path : str, optional
            Path to a rule-face 1 nm npz bundle (rf77_splib07_1nm.npz or
            equivalent). None uses the package-bundled copy at
            cramm/data/rf77_splib07_1nm.npz.
        reference_track : ignored
            Kept for API compatibility; the classifier always runs the
            1 nm rule-face track.
        """
        import json
        from pathlib import Path

        if reference_track not in (None, "1nm"):
            raise ValueError(
                f"reference_track must be None or '1nm' (only the 1 nm track "
                f"is supported), got {reference_track!r}")

        if rf_path is None:
            # Package-bundled 1 nm rule library (cramm/data/). The rule file
            # is NOT searched in CWD any more; users wanting a custom rule
            # library must pass rf_path=... explicitly.
            rf_path = Path(__file__).parent / "data" / "temp_rf_notfeatures_renamed.json"
            if not rf_path.exists():
                raise FileNotFoundError(
                    "Package-bundled 1 nm rule library not found: "
                    f"{rf_path}. The 1 nm track needs a rule library whose "
                    "not-feature reflectance_record fields are rule-name "
                    "strings; provide rf_path=... pointing at such a file.")
        rf_p = Path(rf_path)
        if not rf_p.exists():
            raise FileNotFoundError(f"{rf_p} not found.")
        with rf_p.open("r", encoding="utf-8") as f:
            mica_data = json.load(f)
        rf = mica_data["rf"]

        if splib_path is None:
            # Package-bundled 1 nm rule-face spectra (cramm/data/).
            candidate = Path(__file__).parent / "data" / "rf77_splib07_1nm.npz"
            if not candidate.exists():
                raise FileNotFoundError(
                    "Package-bundled 1 nm rule-face spectra not found: "
                    f"{candidate}. Pass splib_path=... pointing at a rule-face "
                    "1 nm npz bundle.")
            splib_path = candidate
        splib_p = Path(splib_path)
        if not splib_p.exists():
            raise FileNotFoundError(f"{splib_p} not found.")

        # ---- 1 nm (rule-face) track ----
        try:
            bundle = _read_1nm_npz(str(splib_p))
        except Exception as exc:
            raise ValueError(
                f"{splib_p.name}: not a readable 1 nm rule-face npz bundle "
                f"({type(exc).__name__}: {exc}). Note: the legacy splib06b "
                f"binary library was dropped in v1.4.0 -- pass the rule-face "
                f"1 nm npz (rf77_splib07_1nm.npz or equivalent).") from exc
        grid_1nm, rule_1nm, label_1nm, spectra_1nm = bundle  # noqa: F841 (label kept for debugging/inspect)
        # Validation: every rf key must exist in rule_1nm (1-to-1 mapping)
        missing_rf_keys = [k for k in rf.keys() if k not in rule_1nm]
        if missing_rf_keys:
            raise ValueError(
                f"{splib_p.name}: rule-name references missing from 1 nm bundle: "
                f"{missing_rf_keys[:5]}{'...' if len(missing_rf_keys) > 5 else ''}")
        # Validation: every reflectance_record field MUST be a rule-name
        # **string** in rf.keys() -- the rule name is the sole link between
        # the expert rules and the reference spectra library. Raw int
        # records or mix_XXXX strings here mean the user passed an
        # un-renamed file (the original .mcf-derived json prior to
        # temp_rf_notfeatures_renamed.json); raising immediately with a
        # diagnostic list avoids silent wrong-track behavior.
        all_bad = []
        for rname, value in rf.items():
            rec = value["reference"]["reflectance_record"]
            if not isinstance(rec, str) or rec not in rf:
                all_bad.append(
                    f"reference of {rname}: expected rule-name string in "
                    f"rf.keys(), got {type(rec).__name__}: {rec!r}")
            # output_name is the canonical main-reference lookup key used by
            # _judge_reference_entry / _get_compiled_rules / renderer -- it
            # must be a rule-name string in rf.keys(), otherwise classification
            # crashes with KeyError or (worse) silently uses another rule's
            # spectrum as this rule's main reference.
            out = value.get("output_name")
            if not isinstance(out, str) or out not in rf:
                all_bad.append(
                    f"output_name of {rname}: expected rule-name string in "
                    f"rf.keys(), got {type(out).__name__}: {out!r}")
            for ftype in ("not_absolute_features", "not_relative_features"):
                for feat in value.get(ftype, []):
                    r = feat["reflectance_record"]
                    if not isinstance(r, str) or r not in rf:
                        all_bad.append(
                            f"{ftype} of {rname}: expected rule-name string in "
                            f"rf.keys(), got {type(r).__name__}: {r!r}")
        if all_bad:
            raise ValueError(
                "The 1 nm track requires a rule library matching the 1 nm "
                "rule-face contract. Load temp_rf_notfeatures_renamed.json "
                "(every reflectance_record field is a rule-name string in "
                "rf.keys(); the rule name is the sole link to the reference "
                "spectra library). "
                f"Found {len(all_bad)} nonconforming references. First few:\n  - "
                + "\n  - ".join(all_bad[:8]))
        return cls(rf, reference_1nm_bundle=bundle)

    def get_resample(self, w: np.ndarray, bp: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Resample all reference spectra onto the target wavelengths/FWHM.

        The rule name is the sole key into the dict: every rule in ``self.rf``
        takes its pre-baked spectrum from the 1 nm bundle row indexed by the
        rule name. Custom rules added by in-place mutation (cloned
        ``zz_test_*`` names not present in the bundle) inherit the spectrum
        of their source rule via ``reference.reflectance_record`` (which is
        itself a rule-name string after the id-purge migration).

        Results are memoized by ``(w content, bp content)``; call
        :meth:`invalidate_caches` after mutating ``self.rf`` /
        ``self._1nm_bundle``. As a best-effort safety net, reassignment of
        ``self.rf`` to a different dict object (different ``id()``) is
        detected automatically and the cache is dropped; in-place mutation
        (``self.rf["x"] = ...`` or ``self.rf["new"] = ...``) is **not**
        detected — the former silently keeps stale results, the latter
        raises ``KeyError`` from the compiled-rules cache (a deliberate
        stale-trap, see ``test_cache_contract``). Both require an explicit
        :meth:`invalidate_caches` call.
        """
        # Stale-cache check: if rf has been reassigned to a different dict
        # object since the cache was built (id() changed), drop the cache.
        # id() alone is unsafe because CPython may reuse a freed id, but in
        # practice the old dict is usually still referenced (e.g. via
        # MicaEngine.rf alias), making collisions practically impossible.
        # Deliberately does NOT catch in-place mutation (value or key
        # addition) — that is a documented stale-trap; see the docstring
        # above and test_cache_contract.
        if self._resample_cache is not None and self._rf_fp_at_build is not None:
            if id(self.rf) != self._rf_fp_at_build:
                self.invalidate_caches()

        cache_key = (
            np.ascontiguousarray(w).tobytes(),
            np.ascontiguousarray(bp).tobytes(),
        )
        if self._resample_cache_key == cache_key:
            return self._resample_cache

        resampled1: Dict[str, np.ndarray] = {}
        grid_1nm, rule_1nm, _label_1nm, spectra_1nm = self._1nm_bundle
        name_to_row: Dict[str, int] = {str(n): i for i, n in enumerate(rule_1nm)}

        # Two-pass resolution: pass 1 installs every rule that has a direct
        # row in the 1 nm bundle; pass 2 resolves custom rules (clones not in
        # the bundle) via reference.reflectance_record, iterating until no
        # further progress (handles clone-of-clone chains). This removes the
        # implicit dependence on rf.keys() insertion order that the original
        # single-pass loop had (a clone whose owner name sorted later would
        # spuriously raise KeyError("cyclic / missing")).
        pending: List[str] = []
        for canon_id in self.rf.keys():
            row = name_to_row.get(canon_id)
            if row is not None:
                resampled1[canon_id] = _resample_(grid_1nm, spectra_1nm[row], w, bp)
            else:
                pending.append(canon_id)

        while pending:
            progressed = False
            still_pending: List[str] = []
            for canon_id in pending:
                owner = self.rf[canon_id]["reference"]["reflectance_record"]
                if owner in resampled1:
                    resampled1[canon_id] = resampled1[owner]
                    progressed = True
                else:
                    still_pending.append(canon_id)
            pending = still_pending
            if not progressed:
                break

        if pending:
            canon_id = pending[0]
            owner = self.rf[canon_id]["reference"]["reflectance_record"]
            raise KeyError(
                f"get_resample: rule {canon_id!r} has no row in the "
                f"1 nm bundle and its reference {owner!r} is not resolvable "
                f"(cyclic / missing reference).")

        self._resample_cache_key = cache_key
        self._resample_cache = resampled1
        self._rf_fp_at_build = id(self.rf)
        return resampled1

    def _get_compiled_rules(
        self, w: np.ndarray, bp: np.ndarray, wl: np.ndarray, chanels: np.ndarray
    ) -> Dict[str, dict]:
        """
        Compile the reference-side constants of all rules (cached, keyed by
        ``(w, bp, wl, chanels)`` content — the composite key here reuses
        :meth:`get_resample`'s cache key as its base.

        For repeated single-spectrum evaluation scenarios such as
        classify_spectrum: reference-spectrum masks / continuum con_ /
        closed-form least-squares matrix B / depth factors / endpoint indices
        and other input-spectrum-independent computations are done only once.
        The compiled product drives the compiled path of
        :func:`_judge_reference_entry`, bit-exact identical to direct
        evaluation (verified by the check_compiled_path.py differential test).
        Callers must not modify the returned dict; after modifying ``self.rf``
        in place, call :meth:`invalidate_caches` first.
        """
        resampled1 = self.get_resample(w, bp)  # memoized; also ensures _resample_cache_key is ready
        key = (
            self._resample_cache_key,
            np.ascontiguousarray(wl).tobytes(),
            np.ascontiguousarray(chanels).tobytes(),
        )
        if self._compiled_key == key:
            return self._compiled_rules
        rules: Dict[str, dict] = {}
        for name, rf in self.rf.items():
            # Main reference: use rf["output_name"] as the canonical lookup
            # (matches the non-compiled path in _judge_reference_entry and
            # therefore produces bit-exact identical compiled constants vs
            # direct evaluation).
            ref = resampled1[rf["output_name"]][chanels]
            diag = [
                (
                    _precompute_feature(ref, wl, f["continuum_endpoints"]),
                    f["feature_weight"],
                    _continuum_constraints_list(f["continuum_constraints"]),
                    f["fit_constraint"],
                    f["depth_constraints"],
                )
                for f in rf["diagnostic_features"]
            ]
            not_abs = [
                (
                    _precompute_feature(resampled1[f["reflectance_record"]][chanels], wl, f["continuum_endpoints"]),
                    f["fit_constraint"],
                    f["absolute_depth_constraint"],
                )
                for f in rf.get("not_absolute_features", [])
            ]
            not_rel = [
                (
                    _precompute_feature(resampled1[f["reflectance_record"]][chanels], wl, f["continuum_endpoints"]),
                    f["fit_constraint"],
                    f["relative_depth_threshold"],
                )
                for f in rf.get("not_relative_features", [])
            ]
            wc = rf["weighted_constraints"]
            rules[name] = {
                "diag": diag,
                "not_abs": not_abs,
                "not_rel": not_rel,
                "ratio_max": rf.get("max_depth_ratio_feat1_over_feat0"),
                "wc": (
                    wc["min_weighted_fit"],
                    wc["min_weighted_depth"],
                    wc["max_weighted_depth"],
                    wc["min_fit_depth_product"],
                ),
            }
        self._compiled_key = key
        self._compiled_rules = rules
        return rules

    def classify_spectrum(
        self,
        spectrum: np.ndarray,
        wl: np.ndarray,
        w: np.ndarray,
        bp: np.ndarray,
        chanels: np.ndarray,
        top_n: int = 10,
    ) -> List[Dict]:
        """
        Run all mineral rules on a single spectrum, returning the Top-N results
        sorted by fit.

        Parameters
        ----------
        spectrum : np.ndarray
            A single spectrum, which must be a 2-D array of shape
            [1, len(chanels)] (band selection by chanels already applied; the
            engine facade handles the reshape -- check this yourself when
            calling this method directly).

        Performance: reference-side constants go through the
        _get_compiled_rules compilation cache (keyed by w/bp/wl/chanels
        content), so repeated calls under the same band configuration only do
        spectrum-side computation; the compiled path is bit-exact identical to
        per-rule direct evaluation (verified by the check_compiled_path.py
        differential test).
        """
        if spectrum.ndim != 2 or spectrum.shape[0] != 1 or spectrum.shape[1] != len(chanels):
            raise ValueError(
                f"spectrum must be a 2-D array of shape [1, len(chanels)] (one spectrum per row), "
                f"got ndim={spectrum.ndim}, shape={spectrum.shape}, len(chanels)={len(chanels)}"
            )
        compiled = self._get_compiled_rules(w, bp, wl, chanels)
        results = []
        for key in self.rf:
            try:
                fit, fd = _judge_reference_entry(
                    spectrum, wl, None, None, chanels, compiled=compiled[key]
                )
            except (InvalidRangeError, InvalidLeftEndPointError, InvalidRightEndPointError):
                continue
            fit_v = float(fit[0])
            fd_v = float(fd[0])
            if not np.isnan(fit_v) and fit_v > 0:
                results.append({"name": key, "fit": fit_v, "fd": fd_v})
        results.sort(key=lambda x: x["fit"], reverse=True)
        return results[:top_n]

    def classify(
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
    ) -> ClassificationResult:
        """
        Spectral analysis core: per-pixel mineral discrimination, producing raw
        classification results (no coloring/image).

        Returns
        -------
        ClassificationResult
            fit / depth / num / mus_center / chl_center / r / c / index / index_d

        Notes
        -----
        Concurrency: concurrent calls from multiple threads of the same
        process are safe -- the r2-chain scratch buffer is thread-local and
        the parallel path's BLAS-env window is serialized by a process-wide
        lock (parallel calls from different threads run one after another).
        Do NOT mutate self.rf / the caches while a call is
        running (segment tasks are re-enumerated from self.rf per segment).
        Caller scripts using n_workers > 1 need the standard
        ``if __name__ == "__main__":`` guard (spawn re-imports __main__).
        """
        index = list(self.rf.keys())
        index_d = {name: i for i, name in enumerate(index)}
        # Rule-count guard lives in __init__ (fail-fast at construction), but
        # a caller may have grown self.rf in place afterwards (the documented
        # mutation flow is: mutate, then invalidate_caches()). NUM_ is uint8,
        # so >256 rules would silently wrap indices mod 256 and attribute
        # pixels to the wrong minerals -- must be a real raise, not an
        # assert (python -O strips asserts), and must precede the resample.
        if len(index) > 256:
            raise ValueError(
                f"rule library has {len(index)} minerals, exceeding the uint8 "
                f"index limit of 256 (NUM_ dtype); trim the rule library or "
                f"upgrade ClassificationResult.num dtype")

        resampled1 = self.get_resample(w, bp)
        r, c, s = spectrum.shape

        mus_center = np.zeros(r * c, dtype="float")
        chl_center = np.zeros(r * c, dtype="float")
        cal_center = np.zeros(r * c, dtype="float")
        FIT_ = np.zeros(r * c, dtype="float")
        DEPTH_ = np.zeros(r * c, dtype="float")
        NUM_ = np.zeros(r * c, dtype="uint8")

        segments = [(0, int(r / 3)), (int(r / 3), int(r * 2 / 3)), (int(r * 2 / 3), r)]

        nw = n_workers if n_workers is not None else min(os.cpu_count() or 1, 8)
        parallel = nw > 1

        # ---- Parallel path: write the channel-selected spec_sel of the whole
        # image to disk as a memmap for read-only sharing ----
        pool = None
        spec_path = None
        env_saved = None
        try:
            if parallel:
                # Serialize the BLAS-env window across threads (see
                # _PARALLEL_ENV_LOCK). Limit BLAS threads to 1 before the
                # spawned child processes import numpy, avoiding N_worker x
                # multi-thread oversubscription. Child processes inherit these
                # environment variables, which take effect when numpy/MKL is
                # imported. The original values are saved and restored in
                # finally, avoiding polluting the main process's os.environ and
                # affecting child processes spawned later by the caller.
                _PARALLEL_ENV_LOCK.acquire()
                env_saved = {}
                for _v in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
                    env_saved[_v] = os.environ.get(_v)
                    os.environ[_v] = "1"

                spec_sel = np.ascontiguousarray(spectrum.reshape(r * c, s)[:, chanels])
                fd, spec_path = tempfile.mkstemp(suffix=".npy", prefix="mica_spec_")
                os.close(fd)
                np.save(spec_path, spec_sel)
                del spec_sel  # written to disk only for the workers' read-only memmap; the main process holds no file handle, avoiding an os.remove leak
                # The main process's muscovite second pass instead slices from the
                # original spectrum (see inside the loop) and does not touch the memmap file

                # Explicit spawn context: Windows/macOS default to spawn, Linux
                # defaults to fork -- fork would inherit the main process's already
                # initialized MKL/OpenBLAS state (including thread locks and memory
                # allocator internal locks), risking deadlock and inconsistent
                # behavior across the three platforms. With uniform spawn: workers
                # start as fresh interpreters, attach the memmap via the
                # initializer (data does not go through pickle), and BLAS is
                # limited to 1 thread by the environment variables before numpy is
                # imported -- identical semantics on all three platforms.
                pool = mp.get_context("spawn").Pool(
                    nw,
                    initializer=_init_worker,
                    initargs=(spec_path, resampled1, wl, chanels),
                )
            # NOTE: the env/mkstemp/Pool setup above lives INSIDE this try so
            # that a failure there (e.g. spawn denied by the platform) still
            # hits the finally cleanup (env restore / temp-file removal / lock
            # release) instead of leaking.

            for seg_idx, (a, b) in enumerate(segments):
                if cancel_flag is not None and not cancel_flag():
                    raise RuntimeError("cancelled by user")

                a_c, b_c = a * c, b * c
                seg_n = b_c - a_c
                # Channel-selected slice needed by the main process's muscovite
                # second pass, from the same source as the serial path
                # (workers use the memmap file, whose values are bit-exact
                # identical to this slice)
                spectrum1 = spectrum[a:b].reshape([-1, s])[:, chanels]

                if parallel:
                    FIT = np.zeros([seg_n, len(self.rf)])
                    DEPTH = np.zeros([seg_n, len(self.rf)])
                    tasks = [(k, a_c, b_c, value) for k, (key, value) in enumerate(self.rf.items())]
                    for k, fit, fd_val, err in pool.imap_unordered(_judge_task, tasks):
                        if err is not None:
                            msg = f"{index[k]}: {err}"
                            if log_callback:
                                log_callback(msg)
                            else:
                                print(msg)
                            continue
                        FIT[:, k] = fit
                        DEPTH[:, k] = fd_val
                else:
                    FIT = np.zeros([len(spectrum1), len(self.rf)])
                    DEPTH = np.zeros([len(spectrum1), len(self.rf)])
                    # Column-alignment invariant (critical): column k of
                    # FIT/DEPTH must always equal index[k], consistent with the
                    # explicit k of the parallel path's tasks. Using enumerate
                    # guarantees this structurally -- when a rule raises, the
                    # column stays 0 but the column index is still consumed
                    # (k must not be skipped here).
                    for k, (key, value) in enumerate(self.rf.items()):
                        try:
                            fit, depth = _judge_reference_entry(spectrum1, wl, value, resampled1, chanels)
                        except (InvalidRangeError, InvalidLeftEndPointError, InvalidRightEndPointError) as e:
                            msg = f"{key}: {e}"
                            if log_callback:
                                log_callback(msg)
                            else:
                                print(msg)
                            continue
                        FIT[:, k] = fit
                        DEPTH[:, k] = depth

                fit_nan = np.isnan(FIT)  # pre-zeroing snapshot: the center-based
                # reassignment below distinguishes "the rule rejected this pixel"
                # (NaN) from a legitimate zero fit
                FIT[fit_nan] = 0
                DEPTH[np.isnan(DEPTH)] = 0
                im = FIT.argmax(1)

                # Quadratic fit of the muscovite absorption center (mus_center
                # feeds the renderer's tiered coloring)
                fit_pos = FIT.max(1) > 0  # hoisted out of the loop: one reduction shared by 13 minerals (the original repeated it each time)
                for item in MUSCOVITE_MINERALS:
                    if item not in index_d:
                        continue  # a custom rule library may not contain all built-in muscovite-group minerals
                    t_mask = (im == index_d[item]) & fit_pos
                    if not t_mask.any():
                        continue
                    center = _get_quadratic_center(
                        spectrum1,
                        wl,
                        self.rf[item]["diagnostic_features"][0]["continuum_endpoints"],
                        t_mask,
                    )
                    center[np.isnan(center)] = 0
                    mus_center[a * c : b * c] = mus_center[a * c : b * c] + center

                # Quadratic fit of the chlorite 2250 nm absorption center
                # (chl_center: the chlorite product line analog of mus_center;
                # composition proxy via the chl13 M1 calibration). Same shared
                # code path for serial and parallel -> bit-exact.
                for item in CHLORITE_MINERALS:
                    if item not in index_d:
                        continue  # a custom rule library may not contain all built-in chlorites
                    t_mask = (im == index_d[item]) & fit_pos
                    if not t_mask.any():
                        continue
                    center = _get_quadratic_center(
                        spectrum1,
                        wl,
                        self.rf[item]["diagnostic_features"][0]["continuum_endpoints"],
                        t_mask,
                    )
                    center[np.isnan(center)] = 0
                    chl_center[a * c : b * c] = chl_center[a * c : b * c] + center

                # Quadratic fit of the carbonate 2330 nm absorption center
                # (cal_center: the carbonate product line analog of mus_center;
                # band position tracks the 7-anchor C-O sequence from magnesite
                # 2311 nm to rhodochrosite ~2369 nm). Same shared code path for
                # serial and parallel -> bit-exact.
                for item in CARBONATE_MINERALS:
                    if item not in index_d:
                        continue  # a custom rule library may not contain all built-in carbonates
                    t_mask = (im == index_d[item]) & fit_pos
                    if not t_mask.any():
                        continue
                    center = _get_quadratic_center(
                        spectrum1,
                        wl,
                        self.rf[item]["diagnostic_features"][0]["continuum_endpoints"],
                        t_mask,
                    )
                    center[np.isnan(center)] = 0
                    cal_center[a * c : b * c] = cal_center[a * c : b * c] + center

                # Wavelength-based reassignment among the windowed pure
                # muscovites (group locked to MUSCOVITE_MINERALS):
                # mus_center arbitrates the final attribution. Single
                # shared implementation for the serial and parallel paths
                # (bit-exact); see the helper's docstring.
                _reassign_by_absorption_center(
                    im, FIT, fit_nan, mus_center[a * c : b * c],
                    spectrum1, wl, self.rf, index_d, fit_pos,
                    MUSCOVITE_MINERALS,
                )
                # Same arbitration among the four pure-chlorite rules
                # (group locked to CHLORITE_MINERALS), driven by
                # chl_center. Their windows deliberately overlap
                # (tolerant scheme): a center landing in an overlap hits
                # two ranges -> ambiguous -> keep the original match;
                # only a center falling exclusively inside another
                # rule's window flips the attribution.
                _reassign_by_absorption_center(
                    im, FIT, fit_nan, chl_center[a * c : b * c],
                    spectrum1, wl, self.rf, index_d, fit_pos,
                    CHLORITE_MINERALS,
                )
                # Carbonate arbitration (v1.5.0): one call per abundance
                # tier — the abundant pair (calcite_abundant vs
                # dolomite_abundant) and the plain pair (calcite vs
                # dolomite) each form their own locked arbitration group.
                # Within a pair the windows are disjoint
                # ([2.308, 2.328) vs [2.334, 2.350)), so band position
                # arbitrates dolomite<->calcite flips; the abundant/plain
                # axis can never flip because the two groups are disjoint
                # (a pixel's winner belongs to at most one tier's group).
                # The 6 nm dead zone [2.328, 2.334) keeps siderite-ish
                # centers with their argmax winner. Driven by cal_center;
                # same shared implementation for serial and parallel
                # (bit-exact).
                _reassign_by_absorption_center(
                    im, FIT, fit_nan, cal_center[a * c : b * c],
                    spectrum1, wl, self.rf, index_d, fit_pos,
                    CARBONATE_ABUNDANT_MINERALS,
                )
                _reassign_by_absorption_center(
                    im, FIT, fit_nan, cal_center[a * c : b * c],
                    spectrum1, wl, self.rf, index_d, fit_pos,
                    CARBONATE_PLAIN_MINERALS,
                )
                FIT_[a * c : b * c] = FIT.flatten()[im + np.arange(len(im)) * len(self.rf)]
                DEPTH_[a * c : b * c] = DEPTH.flatten()[im + np.arange(len(im)) * len(self.rf)]
                NUM_[a * c : b * c] = im

                if progress_callback:
                    progress_callback(int((seg_idx + 1) / 3 * 100))
        finally:
            if pool is not None:
                if sys.exc_info()[0] is not None:
                    # Exception in flight (worker crash, cancellation, ...):
                    # kill the workers NOW instead of close()-draining the
                    # remaining queued tasks. Dead/OOMing workers can hold the
                    # memmap handle and block the temp-file removal below
                    # (observed: 1.5 GB mica_spec_*.npy leaked after a worker
                    # MemoryError); terminate() releases it promptly.
                    pool.terminate()
                else:
                    pool.close()
                pool.join()
            if spec_path is not None:
                # The main process holds no file handle (spec_sel was del'ed,
                # muscovite uses the original spectrum); only the workers hold
                # it via memmap and have exited after pool.join. On Windows,
                # releasing a large memmap handle may be delayed, so retry a
                # few times; if still failing, register an atexit handler to
                # delete the file at interpreter exit.
                removed = False
                for _ in range(15):
                    try:
                        os.remove(spec_path)
                        removed = True
                        break
                    except OSError:
                        import time as _time
                        _time.sleep(0.2)
                if not removed:
                    import atexit as _atexit
                    _atexit.register(_cleanup_temp, spec_path)
            if env_saved is not None:
                # Restore the main process's os.environ, avoiding polluting
                # child processes spawned later by the caller
                for _k, _v in env_saved.items():
                    if _v is None:
                        os.environ.pop(_k, None)
                    else:
                        os.environ[_k] = _v
                _PARALLEL_ENV_LOCK.release()

        return ClassificationResult(
            fit=FIT_, depth=DEPTH_, num=NUM_, mus_center=mus_center,
            chl_center=chl_center, cal_center=cal_center,
            r=r, c=c, index=index, index_d=index_d,
        )
