# CRAMM verification matrix

Every claim below is reproducible from the repo root. Suites marked
*[scene]* require the EMIT test granule
(`EMIT_L2A_RFL_001_20220819T061448_2223104_025.nc`, 1.85 GB, not
distributed) in the working directory; all other suites run offline on any
platform.

| # | Suite | What it proves | Scale | Result (2026-08-23) |
|---|---|---|---|---|
| 1 | `tests/test_core.py` | API contracts and behavior: resampling fast-vs-slow equivalence, rule-compile freshness, graceful VNIR-only input, band-selection equivalence, cache-invalidation contract, muscovite depth-ratio guard, **synthetic window-arbitration units for all three families** (muscovite seamless / chlorite seamless / carbonate duplicate windows — 8 carbonate cases all keep), render/PDF/CLI guards, dtype uniformity | 18 offline tests | all pass |
| 2 | `tests/test_core.py` integration section *[scene]* | End-to-end contracts on a real 100×100 tile: EMIT reader contract, real-pixel classification, `chl_center` product contract, `cal_center` product contract (winner⇒center consistency > 99.9 %) | 4 tests | all pass |
| 3 | `tests/test_custom_rules.py` | Custom rule libraries: `rf_path` construction, in-place mutation + `invalidate_caches()`, constraint/window edits take effect, new rules classify, extension fields are validated as executable | 14 scenarios | all pass |
| 4 | `tests/test_parallel_isolation.py` | Worker-process and thread isolation, environment restoration, temp-file cleanup | 6 checks | all pass |
| 5 | `tests/check_rows_logic.py` *[scene]* | Row-subset semantics: every per-feature intermediate (continuum removal, r², depth, exclusion sets, quadratic center) is bit-exact between subset and full computation; duplicate/empty row handling | 12 check groups (incl. per-feature loops) | all pass |
| 6 | `tests/test_single_spectrum.py` *[scene]* | Single-spectrum identification: self-identification of library references, noise robustness, determinism, Top-N ordering | 7 tests | all pass |
| 7 | `tests/check_compiled_path.py` *[scene]* | Compiled (precomputed-constant) path vs direct path, bit-level | 302 pixels × 77 rules | zero diff |
| 8 | `tests/test_parallel.py 1` / `4` *[scene]* | Full-scene golden regression: serial and 4-worker outputs vs `tests/golden_arrays.npz`, all 5 arrays (orth_rgb, color_enhanced, mus, chl, cal images) | 1280×1242 px, 5 keys | bit-identical |
| 9 | `tests/rebaseline_golden.py` *[scene]* | Golden-baseline regeneration with per-pixel audit gates (e.g. carbonate rebaseline proved the four pre-existing arrays bit-identical and the new cal layer ≥ 50 k non-black pixels) | full scene | gated tool |
| 10 | `tests/check_arbitration_independence.py` *[scene]* | Family isolation of wavelength arbitration: six-direction cross-family flip census over the full scene | full scene | 0 cross-family flips |
| 11 | `docs/verify_mcf_rfjson.py` | Rule-library fidelity vs the official USGS `.mcf` (2014 v6a): entry set, diagnostic features, continuum slots, NOT references, material constraints, reference identities, color table | 77 rules | zero discrepancies (three documented design deviations declared in `docs/MCF_vs_rfjson_verification.md`) |
| 12 | `arbitration_stats.py` *[scene]* | Production arbitration census, two-pass NUM diff (windowed vs windows-stripped): muscovite 46,823 flips, chlorite 16,209, carbonate 0 (total 63,032); archive `docs/arbitration_stats.md`/`.json` | full scene ×2 | archived |
| 13 | `benchmark.py --full` *[scene]* | Authoritative performance record `docs/benchmark.md`/`.json`: serial 131.73 s, nw=4 61.88 s (2.13×), warm single-spectrum 9.8 ms | full scene | archived |

Notes

- 2026-11-24 per-pixel golden audit: C2 reproduces the golden arrays exactly;
  joint reversion of the 0.55 threshold, lowFe 2.244 window and refit fallback
  restores C2 labels/RGB/numeric arrays; current serial and parallel outputs are
  identical. All 28,226 label changes and all center/RGB differences are
  attributed, including the two explained lowFe/fallback interaction pixels.
  `output/golden_pixel_audit_20261124/audit_summary.json` passes all 11 gates.
  The audited candidate was atomically installed on 2026-11-24 after the
  explicit user decision; the original baseline is preserved as
  `output/golden_pixel_audit_20261124/golden_before_rebaseline.npz`.
  Post-rebaseline serial and four-worker golden suites both PASS with all five
  arrays bit-identical; offline pytest is 40 passed, 2 warnings. See
  `docs/golden_pixel_audit_20261124.md`.

- 2026-11-20 current algorithm-logic audit: compiled/direct, row-subset,
  chained alive-pixel and single-spectrum suites all pass; offline pytest is
  40 passed. The legacy full-scene golden was FAIL at that audit date and was
  subsequently re-audited and rebuilt on 2026-11-24; see the dated update above.
  See `docs/cramm_algorithm_logic_audit.md`.

- 2026-11-18 extension-contract update: suite 3 now has 14 scenarios, adding
  fail-fast checks for non-executable depth-ratio fields and orphan,
  misplaced, invalid or single-member arbitration windows. Full `pytest -q`
  result: **40 passed, 2 warnings**. Synthetic EMIT predictions are
  bit-identical before and after this validation update.
- `docs/audit_extension_execution.py` additionally expands all 3,623 synthetic
  EMIT spectra × 77 rules. It confirms direct/compiled fit equality, 285
  depth-ratio candidate rejections across all nine configured rules, and
  pre-acceptance of every arbitration target (42 M00→M01 and 41 M10→M11
  changes), with zero fire-state changes.
- 2026-11-18 lowFe window update: `[2.244, 2.248)`; current-engine full-scene
  isolation adds 11 clinochlore→lowFe changes and no other label changes.
  Arbitration refits now fall back to the pre-change center when non-finite
  or outside the selected target window. Two real-scene fallback cases and
  synthetic out-of-window regression checks pass; full pytest remains 40 passed.
- 2026-11-19 carbonate scene audit: 1,599 plain-tier calcite→dolomite changes,
  zero reverse/abundant/cross-tier/non-carbonate changes. All 1,599 targets
  pass full constraints and all refitted centers satisfy the target window;
  no fallback was required. `docs/audit_carbonate_arbitration_scene.py` can
  rerun the scene audit and verify every changed pixel.
- 2026-11-19 low-frequency targeted synthesis: 4,883 spectra including 1,260
  targeted white-mica/illite–carbonate/chlorite/epidote mixtures. Arbitration
  alone gives 7 exact-subtype improvements and 0 degradations. Depth-ratio
  effects are mixed: higher confuser detection and component-set exactness,
  but lower white-mica retention and dominant-family hit. Retention changes are
  component-detection metrics, not automatic errors when pure rules are
  intended to reject mixed spectra. Under that exclusion semantics, pure
  white-mica/illite winners decrease from 275 to 57 and correct mixture
  component sets increase from 89 to 136. The three 0.4-threshold
  kaolinite–muscovite references have ratios 0.1972–0.2375 and retain
  self-identification; no dedicated white-mica–smectite rule currently exists.
  See
  `docs/low_frequency_synthetic_audit.md` and the archived stratified CSVs.
- Semantic reassessment (`docs/reassess_synthetic_semantics.py`) verifies 223
  high-ratio pure-mica/illite winners, 218 departures from the pure-rule pool,
  52 unchanged low-ratio winners and zero high-ratio survivors. Correct targeted
  mixture component sets increase 89→136, but 13 perturbed pure-reference
  spectra are additionally excluded. In the 90 white-mica–kaolinite mixtures,
  correct component sets change 11→9. See `docs/algorithm_semantic_reassessment.md`.
- Extended batch (seed 20261119, 6,053 spectra): high-ratio confuser mixtures
  improve correct component sets 86→140, while low-ratio clay mixtures decrease
  100→75. Arbitration alone has 5 exact-subtype improvements and 0 degradations.
  All extended data, predictions and semantic CSVs reproduce bit-exactly.
- Detailed low-ratio clay audit: all 25 lost correct component sets occur in
  the kaolinite subset; smectite remains at zero because no direct white-mica/
  illite–smectite rule exists. No correct sets are gained, and no-fire stays
  at 44. See `docs/low_ratio_clay_detailed_audit.md`.
- Threshold development update: pure white-mica/illite remains 0.6; the three
  kaolinite–muscovite rules move from 0.4 to 0.55. Correct targeted component
  sets increase 215→229 with gains in all five pair folds and no added no-fire.
  Actual classifier output matches the selected simulation, and SYN02031 is
  corrected. Full-scene A/B changed 28,215 labels before the 2026-11-24 audited
  rebaseline. The legacy golden regression FAIL recorded here is historical;
  the subsequent audit and replacement are documented above. See
  `docs/depth_ratio_threshold_optimization.md`.
- Consolidated extension audit: `docs/introduced_extensions_audit.md` covers
  arbitration invariants and current 0.6/0.55 depth-ratio semantics. At 0.55,
  high-ratio correct sets are 86→140 and low-ratio clay sets are 100→89;
  current semantic outputs are under `output/semantic_reassessment_tclay055_v1/`.
- Reference diagnostic audit (`docs/audit_reference_diagnostic_features.py`):
  142/142 features pass their own constraints on 1 nm and EMIT; 140/142 centers
  are valid, with two edge minima. Six exact-duplicate reference groups explain
  all seven Top-1 self-identification misses. No arbitration-window feature has
  a center anomaly. See `docs/reference_diagnostic_feature_audit.md`.
- The golden baseline (#8) is platform-bound (BLAS ulp differences); on a new
  platform run #9 first. This is documented in README *Testing*.
- Suites 1–4 constitute the offline CI core; 5–10 and 12–13 need the test
  granule.
- Pixel-count convention used everywhere in this repo: the scene grid is
  1280×1242 = 1,589,760 px.
- Carbonate-count convention: suite 12's archived census and README's separate
  current-tier carbonate run are different arbitration configurations. The
  archived census reports 63,032 muscovite + chlorite changes, while the
  current-tier run reports 1,599 plain-tier calcite→dolomite changes. These
  results are reported separately and must not be summed or read as a single
  total.
