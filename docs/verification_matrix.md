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
| 3 | `tests/test_custom_rules.py` | Custom rule libraries: `rf_path` construction, in-place mutation + `invalidate_caches()`, constraint/window edits take effect, new rules classify | 7 scenarios | all pass |
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

- The golden baseline (#8) is platform-bound (BLAS ulp differences); on a new
  platform run #9 first. This is documented in README *Testing*.
- Suites 1–4 constitute the offline CI core; 5–10 and 12–13 need the test
  granule.
- Pixel-count convention used everywhere in this repo: the scene grid is
  1280×1242 = 1,589,760 px.
