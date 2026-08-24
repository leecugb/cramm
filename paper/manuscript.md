# Manuscript draft — Computers & Geosciences

> Status: draft v0.4 (2026-08-24) — full manuscript prose complete (Sections 1–7 + back matter); remaining: [Evidence needed] items (Earthdata metadata, carbonate coverage reconciliation, author block, CRediT/acknowledgments), figure regeneration (Fig. 3), reference completion pass.
> Name: CRAMM = Continuum-Removed Absorption Mineral Mapping (author-confirmed 2026-08-23); PyPI https://pypi.org/project/CRAMM/ ; GitHub https://github.com/leecugb/cramm.
> Wording discipline (locked, do not regress): "composition proxy" (never "quantitative composition"); "interpretive framework / isopleth / constraint locus" (never "inversion", "two-dimensional pointer"); no "10× faster" claim until a same-machine IDL-vs-CRAMM timing is archived (docs/academic_value_assessment.md R2).
> Source of facts: docs/paper_preparation.md §0 (all numbers traceable); docs/verification_matrix.md; docs/MCF_vs_rfjson_verification.md; docs/arbitration_stats.md.

---

## Title

**From mineral detection to mineral composition: CRAMM, an open Python toolkit extending USGS MICA with wavelength-arbitrated subtyping and absorption-center mapping**

## Author block

[Author name]^a,\* — *[author name / affiliation / email pending]*

^a [Affiliation, City, Country]
\* Corresponding author: [email]

## Highlights

- First open-source Python implementation of the USGS MICA mineral-mapping rule system
- Rule library verified field-by-field against the official MICA command file
- Sensor-agnostic core resamples reference spectra to any band set at runtime
- Wavelength-arbitrated subtyping plus per-pixel absorption-center composition maps
- A full EMIT granule classified in about one minute with bit-exact reproducibility

## Abstract

The USGS Material Identification and Characterization Algorithm (MICA) is a widely used expert system for mapping minerals from imaging spectroscopy, but it is distributed only as closed-source IDL code tied to the ENVI environment and to sensor-specific pre-convolved reference libraries, which limits reproduction, extension, and uptake by new spaceborne missions such as EMIT. Here we present CRAMM, the first open-source, pure-Python implementation of MICA. Its rule library — 77 decision rules with 142 diagnostic features — was verified field-by-field against the official 2014 v6a MICA command file with zero discrepancies, and reference spectra are resampled to arbitrary band configurations at runtime, making the classification core sensor-agnostic. CRAMM extends MICA in three ways: an optional secondary-feature depth-ratio constraint that suppresses white-mica false positives; wavelength-arbitrated attribution of muscovite, chlorite, and carbonate subtypes against calibrated absorption-center windows; and per-pixel absorption-center maps that turn subtype labels into continuous composition proxies anchored to measured mineral chemistry. A full EMIT granule (1280 × 1242 pixels) is classified in about one minute with four workers — more than an order of magnitude faster than the IDL/PRISM implementation on the same granule — with bit-exact serial–parallel reproducibility guarded by a golden regression suite. CRAMM is cross-platform, self-contained, and available on PyPI, lowering the barrier from mineral detection to mineral composition mapping.

## Keywords

Hyperspectral imaging; Mineral mapping; USGS MICA; Decision-rule classification; EMIT; Absorption-center wavelength

---

## 1. Introduction

Imaging spectroscopy measures the mineralogical composition of the Earth's surface at pixel scales of metres to tens of metres, and mineral maps derived from it underpin hydrothermal alteration studies, mineral exploration, geothermal resource assessment, and dust-cycle research. Spaceborne instruments have turned this capability from an airborne specialty into an operational one: since 2022 the Earth Surface Mineral Dust Source Investigation (EMIT) has delivered openly licensed L2A surface-reflectance products at global scale, and a growing user community needs mapping tools that are open, auditable, and easy to adapt to new sensors.

Among mapping approaches, expert rule systems occupy a distinct niche. Rather than learning class boundaries from labelled data, they encode spectroscopic expert knowledge directly: minerals are identified by the presence, position, and strength of diagnostic absorption features, evaluated against explicit thresholds. The lineage runs from the USGS Tetracorder system (Clark et al., 2003) to the Material Identification and Characterization Algorithm (MICA; Kokaly et al., 2011), whose command file distils 77 minerals and mixtures into decision rules over continuum-removal features. Because every decision traces back to named absorption features and explicit constraints, rule systems remain auditable where statistical classifiers are not — a property that underpinned the largest operational demonstration to date, the USGS mineral map of Afghanistan compiled from 218 HyMap flight lines covering more than 438,000 km² (Kokaly et al., 2013).

MICA, however, reaches users only as a module of the PRISM processing environment, distributed as compiled IDL byte-code (a save-file for the ENVI `save_add` directory) that requires a licensed ENVI + IDL installation — the official release was compiled against ENVI 4.8 + IDL 8.0 (Kokaly, 2011) — and its reference spectra must be convolved to a specific sensor's band configuration before use (the standard distribution ships, for example, a HyMap 126-band library copy). Adopting MICA for a new sensor therefore means rebuilding the reference chain inside a licensed IDL/ENVI installation: results cannot be independently reproduced, the rule logic cannot be audited or extended by the community, and each new mission repeats the porting effort behind closed doors. In the EMIT era this gap is increasingly conspicuous — the data are open, but one of the field's reference rule systems is not.

Here we present CRAMM (Continuum-Removed Absorption Mineral Mapping), the first open-source, pure-Python implementation of the MICA decision-rule system. Fidelity is established by direct evidence: the bundled rule library was verified field-by-field against the official 2014 v6a MICA command file, with zero discrepancies across all 77 rule entries, 142 diagnostic features, 1,136 continuum-constraint slots, 80 NOT-feature references, material-level constraints, reference-spectrum identities, and the class colour table, and the verification script is shipped with the package for re-execution. Instead of pre-convolved libraries, CRAMM resamples the bundled splib06b reference spectra to the sensor's bands at runtime, so the classification core accepts any VNIR–SWIR reflectance cube described by its band configuration. Beyond fidelity, CRAMM extends MICA in three directions. First, an enhanced rule schema adds an optional secondary-feature depth-ratio constraint that suppresses white-mica false positives passing the original five-layer filtering. Second, muscovite, chlorite, and carbonate subtype labels are re-arbitrated against per-rule calibrated absorption-center wavelength windows, replacing pure best-fit attribution with attribution along the spectroscopically meaningful axis on which these subtypes are defined. Third, per-pixel absorption-center products recast discrete subtype labels as continuous composition proxies, anchored to measured mineral chemistry and interpreted within a thermodynamic activity diagram compiled from a GEMS/MINES23.1 reaction-path model.

The remainder of the paper is organized as follows. Section 2 summarizes the MICA decision-rule formalism that CRAMM implements. Section 3 describes the design and implementation, including the sensor-agnostic input contract, the fidelity verification, the depth-ratio constraint, and the wavelength-arbitration scheme. Section 4 reports the verification matrix, scene-scale arbitration statistics, and performance. Section 5 illustrates the products on a full EMIT granule. Section 6 discusses design principles, limitations, and outlook, and Section 7 concludes.

---

## 2. Background: the MICA decision-rule system

> Sources: docs/DS787_summary.md (formalism), docs/kokaly2011.md (distribution), docs/MCF_v6a_summary.md (command-file structure). Drafted from the verified fact table (paper_preparation.md §0).

MICA identifies minerals by matching diagnostic absorption features in a pixel spectrum against laboratory reference spectra in continuum-removal space. For a feature defined over a wavelength interval, the continuum is the straight line connecting the spectrum levels at the two endpoint ranges; the continuum-removed spectrum is R_C(λ) = R_O(λ) / R_L(λ), and the feature depth is D = 1 − R_C at the absorption minimum. The agreement between a pixel feature and the corresponding reference feature is scored by the coefficient of determination r² of the two continuum-removed shapes (the "fit"), while feature strength enters through a depth factor obtained by scaling the reference depth rather than by reading the pixel minimum directly, tying the score to the reference shape (Kokaly et al., 2013). Each material is thereby reduced to a compact numeric descriptor: endpoint ranges for each diagnostic feature, fit and depth thresholds, and weighting parameters.

A MICA command file (.mcf) packages these descriptors into decision rules. Each rule names one or more diagnostic features together with not-absolute and not-relative features whose presence excludes the pixel; a candidate is scored against a rule only if it passes a cascade of constraints on fit, depth, continuum level, weighted feature combinations, and a fit/depth ratio ceiling. The pixel is finally assigned to the admissible rule maximizing the product fit × depth. Mixture rules extend the system to binary mixtures of endmembers, which in the original distribution are represented by measured physical-mixture reference spectra.

Two properties of the official 2014 v6a command file matter for what follows. First, it is a complete, self-contained artifact: 77 rule entries (including 19 mixture rules) with their feature descriptors, constraint parameters, references to 64 pure reference spectra, and a 77-class colour table — the entire expert knowledge of the system in one inspectable file. Second, it is sensor-bound: header parameters and the accompanying reference library are convolved to a specific instrument grid (the standard distribution ships, for example, a HyMap 126-band copy), and PRISM dedicates two functions (spectral interpolation, Function 2.8; convolution, Function 2.9) precisely to rebuilding the library for each spectrometer (Kokaly, 2011), so the rule logic and the sensor addressing are entangled in a single distribution. Section 3.1 describes how CRAMM separates the two.

---

## 3. CRAMM: design and implementation

### 3.1 Sensor-agnostic input contract

The defining design decision in CRAMM is to sever the rule logic from sensor addressing. The classification core accepts a reflectance spectrum together with an explicit band configuration — center wavelengths, per-band widths (FWHM), and a valid-band mask — and nothing else; it contains no sensor-specific constants. The bundled splib06b reference spectra are resampled to the given band configuration at runtime by convolution with a Gaussian kernel matched to each band, and the resampled library is cached so that each unique (reference × sensor grid) product is computed only once per run. Channels flagged invalid by the mask are excluded from every feature evaluation. As a consequence, supporting a new sensor requires only a reader that delivers spectra and the band configuration: the EMIT L2A netCDF reader shipped with CRAMM is the sole sensor-specific module (106 lines), and the classification of Section 4 runs on rule logic that has never seen an EMIT-specific constant.

### 3.2 Rule engine

For each pixel and each rule, the engine evaluates the MICA scoring cascade in a single vectorized pass: continuum removal within the endpoint ranges of each diagnostic feature; fit (r²) and depth against the resampled reference feature obtained from closed-form 2 × 2 normal equations; exclusion by not-absolute and not-relative features; the five constraint layers (fit, depth, continuum level, weighted combination, ratio ceiling); and, for admissible rules, the score fit × depth. Rules are compiled once per run into precomputed constants — normal-equation coefficients and depth factors — held in a two-level cache keyed by the rule set and the band configuration, so repeated scene processing and repeated scene chunks never recompile. The winning rule per pixel is the argmax of fit × depth, with invalid or inadmissible evaluations propagating as NaN rather than silent zeros.

### 3.3 Rule library and fidelity verification

The rule logic ships as an inspectable JSON file (rf.json): 77 decision rules, 19 mixture definitions, and a 53-entry wavelength map covering the four instrument grids of the original distribution. Fidelity to USGS MICA is not asserted but demonstrated: every field of every rule was compared programmatically against the official 2014 v6a command file (Table 1), and the comparison script is distributed with the package so the claim can be re-executed. Three design deviations from the original artifact are declared explicitly. First, the 13 mixture references that the original distribution stores as measured physical-mixture spectra are synthesized in CRAMM as linear combinations of endmember spectra; for two of these rules (kaolinite–muscovite and alunite–kaolinite) the kaolinite endmember is KGa-2 rather than KGa-1, because the two reference clays differ in the sharpness of the 2.2 µm doublet. Second, the sensor-bound header parameters of the command file are replaced by the runtime band-configuration contract of Section 3.1. Third, rf.json carries optional CRAMM-specific fields — the depth-ratio threshold (Section 3.4), per-rule absorption-center windows (Section 3.5), and structural-formula metadata (Section 3.5) — which have no counterpart in the original schema and never enter the MICA scoring path unless the corresponding CRAMM extension is engaged.

### 3.4 Secondary-feature depth-ratio constraint

White-mica rules in MICA key on the 2.2 µm Al–OH absorption; pixels whose secondary absorption is anomalously deep relative to the primary feature can pass all five constraint layers while being spectroscopically implausible white micas. CRAMM adds an optional per-rule threshold, `max_depth_ratio_feat1_over_feat0`, that rejects a candidate when the ratio of the secondary-feature depth to the primary-feature depth exceeds the threshold. Nine bundled rules carry the constraint — six at 0.6 and three at 0.4, spanning the muscovite, illite, and kaolinite–muscovite mixture rules — and any custom rule can opt in through the same schema field. The thresholds are empirical; we report them as tuned constants and return to their status in Section 6.

### 3.5 Absorption-center products and wavelength arbitration

Beyond discrete labels, CRAMM fits for each classified pixel the wavelength of its diagnostic absorption center: the vertex of the quadratic through the three continuum-removed samples bracketing the feature minimum, evaluated within the winning rule's feature endpoints (a collinear triplet folds to NaN rather than to a spurious wavelength). Applied to the 2.2 µm feature of white micas, the 2.25 µm feature of chlorites, and the 2.3 µm feature of carbonates, this yields three continuous product layers — `mus_center`, `chl_center`, and `cal_center` — on top of the discrete mineral map.

These centers are then used to re-arbitrate subtype attribution. MICA assigns muscovite, chlorite, and carbonate subtypes by best fit alone, although the subtypes are defined along absorption-wavelength axes. CRAMM's arbitrator gates candidates by family membership and a positive fitted center, counts how many calibrated windows of the family the center falls into, and acts on the count: exactly one window — the attribution is flipped to that window's rule and the center is refitted once at the target rule's endpoints (reverting on failure); more than one window — the attribution is declared ambiguous and kept; no valid window — the attribution is conservatively kept. The arbitrator is vectorized in a single pass shared by the serial and parallel code paths, so arbitration is bit-exact across execution modes.

The window geometry encodes a prior about each family's subtype axis, and we treat the correspondence as a design principle. Muscovite subtypes form a discrete axis anchored at the measured wv2200 of the four reference spectra, so the four windows tile the axis contiguously: [2195, 2200), [2200, 2206), [2206, 2210), [2210, 2220) nm; the nine family members without calibrated windows (illites and mixtures) are excluded from arbitration. Chlorite compositions vary continuously, so the three windows overlap deliberately by 1 nm — a tolerance set equal to the leave-one-out RMSE (1.0 nm, n = 13) of the closed-form chlorite calibration pos2250 = 2218.8·xAl + 2279.6·xFe + 2249.7·xMg, i.e. the replicate-measurement noise floor; pixels falling in the overlap are kept as ambiguous rather than forced onto a reference composition. The carbonate rule pairs are indistinguishable on the center axis, so their windows are duplicated outright (calcite pair at 2334–2350 nm, dolomite pair at 2308–2328 nm): arbitration flips zero pixels by construction, and the compositional content lives entirely in the continuous `cal_center` layer, read against a seven-anchor literature sequence from magnesite (2311.3 nm) through dolomite (2321.2 nm) and calcite (2339.4 nm) to rhodochrosite (~2369 nm). Family isolation is structural: the muscovite–chlorite and chlorite–carbonate window gaps are 25 nm and 52 nm respectively, membership gating prevents cross-family candidacy, and scene-wide all six cross-family flip directions measure zero (Section 4.2).

The chemical anchoring of these products is carried as metadata, not as classification logic. Seven muscovite-family and chlorite-family rules are annotated with parsed structural formulas (tier A: wet-chemistry dual-valence analyses; tier B: all-iron conventions), the muscovite windows derive from a 14-sample wv2200–composition calibration on an O = 11 anhydrous basis, and the chlorite windows from the 13-sample calibration above on an O₁₀(OH)₈ basis. These annotations make the composition-proxy interpretation of the center products auditable; they do not alter any classification decision.

### 3.6 Reproducibility engineering and extensibility

Two engineering properties guard the claims above. First, reproducibility is bit-exact: worker processes are spawned with the BLAS thread count pinned to one, and the serial and parallel paths share a single implementation, so outputs are bit-identical across worker counts; a golden regression suite over the five output keys, with platform-aware rebaseline tooling gated by a pixel-level audit, protects this property across platforms (residual BLAS ulp differences make baselines platform-dependent, which the tooling records rather than hides). Second, the rule library is user-extensible: a custom rf.json can be supplied at construction or edited in place followed by an explicit cache-invalidation call, a mechanism covered by seven dedicated test scenarios. The package is pure Python with NumPy as the only top-level dependency, runs on Python 3.9–3.13 across Windows, Linux, and macOS, and keeps heavier imports lazy so that worker spawn stays cheap.

**Table 1 (pre-filled, verified — source docs/MCF_vs_rfjson_verification.md).** Field-by-field verification of the CRAMM rule library against the official 2014 v6a MICA command file: 77/77 rule entries; 142/142 diagnostic features; 1,136/1,136 continuum-constraint slots; 80/80 NOT-feature references; 77×4 material-level constraints; 64/64 pure reference-spectrum identities (6 records confirmed by manual review as the same physical samples); 77/77 class colours. Zero discrepancies. Verification script shipped as docs/verify_mcf_rfjson.py in the repository.

---

## 4. Verification and performance

### 4.1 The verification matrix

CRAMM's correctness claims are organized as a verification matrix of thirteen reproducible suites (Table 2), each executable from the repository root. Suites 1–4 form an offline CI core that runs on any platform without external data: API and behaviour contracts (including synthetic window-arbitration units for all three families), custom rule-library scenarios, worker-process isolation, and numerical-path equivalence (compiled versus direct evaluation, bit-level, over 302 pixels × 77 rules). Suites 5–10, 12, and 13 require the EMIT test granule and cover end-to-end contracts on real pixels, row-subset bit-exactness, single-spectrum identification, full-scene golden regression, family isolation of arbitration, the production arbitration census, and the performance record. Suite 11 is the rule-library fidelity verification of Section 3.3, shipped as a re-executable script. Because floating-point summation order can differ across BLAS builds, the golden baseline of suite 8 is platform-bound; suite 9 provides a gated rebaseline tool with per-pixel audit, so platform differences are recorded rather than silently absorbed.

**Table 2.** Verification matrix (condensed from docs/verification_matrix.md; all suites reproducible from the repository root; *[scene]* marks suites requiring the test granule).

| # | Suite | What it proves | Scale | Result |
|---|---|---|---|---|
| 1 | test_core.py (offline) | API contracts; synthetic arbitration units for all three families; render/PDF/CLI guards | 18 tests | all pass |
| 2 | test_core.py integration *[scene]* | End-to-end product contracts on a real 100×100 tile; winner⇒center consistency > 99.9 % | 4 tests | all pass |
| 3 | test_custom_rules.py | Custom rule libraries: construction, in-place edit + cache invalidation, edits take effect | 7 scenarios | all pass |
| 4 | test_parallel_isolation.py | Worker-process/thread isolation, environment restoration, temp-file cleanup | 6 checks | all pass |
| 5 | check_rows_logic.py *[scene]* | Every per-feature intermediate bit-exact between row-subset and full computation | 12 check groups | all pass |
| 6 | test_single_spectrum.py *[scene]* | Reference self-identification, noise robustness, determinism, Top-N ordering | 7 tests | all pass |
| 7 | check_compiled_path.py *[scene]* | Compiled vs direct numerical path, bit-level | 302 px × 77 rules | zero diff |
| 8 | test_parallel.py *[scene]* | Full-scene golden regression, serial vs 4 workers, all 5 output arrays | 1280×1242 px × 5 keys | bit-identical |
| 9 | rebaseline_golden.py *[scene]* | Golden-baseline regeneration with per-pixel audit gates | full scene | gated tool |
| 10 | check_arbitration_independence.py *[scene]* | Six-direction cross-family flip census | full scene | 0 cross-family flips |
| 11 | verify_mcf_rfjson.py | Rule-library fidelity vs official 2014 v6a .mcf (Table 1) | 77 rules | zero discrepancies |
| 12 | arbitration_stats.py *[scene]* | Production arbitration census, windowed vs windows-stripped two-pass diff | full scene ×2 | archived (Section 4.2) |
| 13 | benchmark.py --full *[scene]* | Authoritative performance record | full scene | archived (Section 4.3) |

### 4.2 Scene-scale arbitration statistics

On the full granule, wavelength arbitration re-attributed 62,128 pixels (3.9 % of the scene), and every flip stayed within its family: the six-direction cross-family census measures zero (Table 2, suite 10), confirming that the 25/52 nm window gaps plus membership gating isolate the three families structurally. Within families, the flips are strongly directional. In the muscovite family (46,823 flips), the dominant move is medAl → lowAl (37,968 px), followed by lowAl → Fe-rich (6,492 px): best-fit attribution alone systematically places pixels one subtype away from the attribution consistent with their measured 2.2 µm absorption center. In the chlorite family (15,305 flips), the dominant move is clinochlore → clinochlore_Fe (14,969 px), with the reverse direction accounting for only 286 px and the low-Fe window for 50 px; pixels whose centers fell inside the 1 nm window overlap kept their attribution, consistent with the declared-ambiguity design. The carbonate family flips zero pixels by construction (Section 3.5). Family members without calibrated windows — illites and all mixture rules — are never arbitrated; among them the clinochlore–muscovite mixture rule alone accounts for 643,612 px (40.5 % of the scene), a reminder that mixture rules, not pure endmembers, carry much of the attribution in real scenes. Arbitration adds no measurable cost: the windowed production run took 59.8 s against 60.0 s for the same rules with all windows stripped (n_workers = 4).

**Table 3.** Production arbitration census (docs/arbitration_stats.md/.json; windows in nm; flips in/out per rule; totals: muscovite 46,823, chlorite 15,305, carbonate 0, grand total 62,128). [Table to be typeset from the archived JSON at submission; content frozen.]

### 4.3 Performance

Table 4 reports the authoritative benchmark (Windows 11, 24 logical CPUs, Python 3.13.9, NumPy 2.3.5): the full granule — classification plus all three absorption-center product lines plus arbitration — processes in 131.73 s serial and 61.88 s with four workers (25,689 px/s, 2.13×); eight workers exceed available memory on this machine (~590 MiB float64 per worker chunk), so four is the practical setting. Warm single-spectrum classification takes 9.8 ms, and resampling the entire reference library to the sensor grid costs 133.4 ms once per run. For comparison, USGS PRISM (IDL MICA) required approximately 25 minutes of pure classification time for the same granule on the same machine, under ENVI Classic 5.6.2 + IDL 8.8.2 with the official 2014 v6a EMIT-convolved command file (author-reported timing; protocol recorded in the repository). CRAMM is therefore more than an order of magnitude faster — ~11× serial, ~24× with four workers — and the comparison is conservative in PRISM's favour on three counts: PRISM ran on a far newer runtime than its official ENVI 4.8 + IDL 8.0 target; its 25 minutes exclude the library convolution and command-file adaptation that PRISM requires beforehand, while CRAMM's figure includes three product lines and arbitration on top of classification; and CRAMM's runtime library resampling (133.4 ms) makes the preprocessing that PRISM excludes effectively free.

**Table 4.** Full-scene performance (1280×1242 px, 1,589,760 px; classification + three center products + arbitration). Serial 131.73 s (12,068 px/s); n_workers = 2: 93.00 s (17,093 px/s); n_workers = 4: 61.88 s (25,689 px/s). Other operations: granule load 3.75 s; reference resampling cold 133.4 ms; single-spectrum classify cold 159.1 ms / warm 9.8 ms; orthorectify + 3 GeoTIFFs 4.66 s; Top-3 single-spectrum diagnostic PDF 2.42 s. [To be typeset.]

---

## 5. Illustrative application: an EMIT granule

### 5.1 Scene and data

We demonstrate CRAMM on the public NASA LP DAAC product EMIT_L2A_RFL_001_20220819T061448_2223104_025 (EMIT L2A surface reflectance, acquired 19 August 2022): 1280 × 1242 pixels (1,589,760 px) with 285 bands, of which 244 are valid after masking. The granule footprint, read from the L2A geolocation arrays, is centred near 99.65 °E, 41.03 °N in the Gobi Desert close to the China–Mongolia border. [Evidence needed: Earthdata granule metadata confirmation (DOI/download URL) and a literature-supported geological-background paragraph — to be written only from citable sources.]

### 5.2 Mineral maps

The scene product comprises five layers (Fig. [2]): the discrete mineral map, an enhanced colour composite, and the three continuous absorption-center layers `mus_center`, `chl_center`, and `cal_center`. Pure carbonate rules win 78,672 px (4.9 % of the scene), and carbonate–muscovite mixture rules carry a further substantial fraction [Evidence needed: reconcile the "~39 % carbonate-influenced coverage" estimate with the archived winner census before any coverage statement]. Attribution is dominated by mixture rules: the clinochlore–muscovite mixture alone covers 40.5 % of the scene (Section 4.2), so the discrete map should be read as a mixture-aware attribution rather than an endmember census.

### 5.3 Composition-proxy products

The three center layers convert the discrete map into continuous compositional information, with family-specific evidence levels. For carbonates, `cal_center` is read against a seven-anchor laboratory sequence — magnesite 2311.3 < aragonite 2315.2 < Fe-dolomite 2319.2 < dolomite 2321.2 < siderite ~2327 < calcite 2339.4 < rhodochrosite ~2369 nm — of which the rule library carries only three (calcite, dolomite, Fe-bearing carbonate); minerals without rules (aragonite, magnesite) are silently absorbed into the nearest rule class in the discrete map but remain distinguishable in the continuous layer, which thus exceeds the resolution of the rule library itself (Fig. [4]). For chlorite, `chl_center` maps to composition through the closed-form chl13 calibration (Section 3.5; LOO-RMSE 1.0 nm), with the stated applicability bounds — chlorite should dominate the pixel (≳ 50 %) under comparable sample preparation — carried over from the calibration. For white mica, `mus_center` is interpreted within a GEMS/MINES23.1 reaction-path activity diagram (Fig. [5]): the wv2200 isopleths are derived by chaining the empirical wavelength–composition calibration through the modelled Tschermak-substitution field, so they track the composition contours by construction. A fitted `mus_center` therefore selects one isopleth — muscovite composition (X_Ts) is read directly, while in the T–log(aK⁺/aH⁺) plane the value defines a one-dimensional constraint locus, not a unique point; pinning down both formation temperature and fluid K⁺/H⁺ requires a second independent constraint, for example the `chl_center` of a coexisting chlorite under a same-pressure, same-fluid equilibrium assumption. We stress that the diagram is an interpretive framework for the product, not a ground-validated inversion.

### 5.4 Per-pixel interpretability

Because every CRAMM decision traces to named features and explicit constraints, any pixel can be audited individually: the single-spectrum diagnostic report (Fig. [6]; 2.42 s per report) decomposes a pixel spectrum rule by rule — continuum-removed feature fits, depths, constraint pass/fail, and the winning fit × depth score — providing the per-pixel evidence trail that operational rule systems promise but closed distributions cannot demonstrate.

---

## 6. Discussion

Two properties distinguish CRAMM from a routine re-implementation. The first is demonstrated trust: fidelity to USGS MICA is not an assertion but a re-executable measurement (Table 1), and behavioural correctness is guarded by a thirteen-suite verification matrix whose scene-scale census (62,128 within-family flips, zero cross-family flips) confirms that the arbitration layer behaves as designed on real data. The second is a portable design principle: the three families show that the topology of arbitration windows should follow the prior about the subtype axis — contiguous windows where subtypes are discrete anchors (muscovite), deliberately overlapping windows where composition is continuous and borderline pixels should be declared ambiguous rather than forced (chlorite, with the tolerance set at the calibration's own noise floor), and duplicated windows where classes are indistinguishable on the axis, making "no reassignment" an explicit declaration rather than an omission (carbonate). We expect this correspondence to be useful beyond this rule library, wherever expert systems quantize intrinsically continuous spectral axes.

Relative to the MICA lineage, the muscovite upgrade is the sharpest: the four white-mica subtypes were originally discriminated by best fit against multiple reference spectra — effectively a vote among library entries — whereas CRAMM arbitrates them on the continuous 2.2 µm absorption-center axis along which the subtypes are spectroscopically defined, recovering the compositional meaning that pure best-fit attribution discards (Section 4.2 shows the re-attribution is large and directional). Relative to statistical unmixing and machine-learning classifiers, rule systems trade representational power for auditability: every CRAMM decision decomposes into named features and explicit thresholds (Section 5.4), which is why such systems remain in operational use and why an open, verified implementation matters independently of algorithmic fashion.

The limitations are specific. The composition products are proxies whose evidence level differs by family: the muscovite interpretation rests on a 14-sample calibration plus a thermodynamic model chain (itself an interpretive framework, not ground truth), the chlorite calibration is stronger statistically (LOO-RMSE 1.0 nm, n = 13) but bounded to chlorite-dominated pixels under comparable sample preparation, and the carbonate reading relies on literature anchors without a dedicated calibration. The depth-ratio thresholds (0.6/0.4) are empirical constants without a sensitivity study. One bundled rule (calcite_abundant, 5 px scene-wide) is effectively dormant on this scene. Coverage gaps inherited from the official command file persist: the library contains no muscovite–smectite mixture rule, for example, so the common illite–smectite mixed-layer assemblage can only be attributed to the nearest pure rule or the two illite entries; the custom rule-library mechanism (Section 3.6) is the intended remedy. The golden regression baselines are platform-bound by BLAS last-bit differences and are governed by an explicit rebaseline procedure rather than hidden. The 1-µm command-file group (Fe-bearing minerals, VNIR) of the original two-file distribution is not yet ported. Most importantly, no scene-level ground validation exists for any product: the demonstration granule was chosen as a public, reproducible workload, and its geology is not yet independently characterized.

These boundaries define the follow-on work rather than undermine the present claims. The isopleth geometry of Section 5.3 points to a concrete upgrade: where muscovite and chlorite coexist, the `mus_center` and `chl_center` constraint loci can be intersected under an explicit same-pressure, same-fluid equilibrium assumption to yield point estimates of temperature and fluid composition — a validation and application study in its own right, to which the present paper supplies the verified engine. Adding a sensor now costs one reader (Section 3.1), and the custom rule-library mechanism (Section 3.6) opens the rule base itself to community extension; porting the 1-µm rule group would complete the original two-file distribution.

## 7. Conclusions

CRAMM re-implements the USGS MICA decision-rule system as an open, pure-Python, sensor-agnostic engine and extends it from mineral detection to composition-proxy mapping. Fidelity is measured, not claimed — field-by-field verification against the official 2014 v6a command file yields zero discrepancies with three declared design deviations — and reproducibility is engineered to the bit level across serial and parallel execution. Wavelength arbitration against calibrated absorption-center windows re-attributes subtypes along their spectroscopically meaningful axes (62,128 px re-attributed on the demonstration granule, zero cross-family flips), and the per-pixel center products read as continuous composition proxies anchored to measured mineral chemistry. A full EMIT granule is processed in about one minute, more than an order of magnitude faster than the IDL/PRISM implementation under conditions recorded in the repository. The composition products remain proxies pending scene-level ground validation; within that boundary, CRAMM provides the open, auditable rule-engine infrastructure that the open-data era of spaceborne imaging spectroscopy requires.

---

## Figures (provisional numbering; final captions at submission)

- **Fig. 1.** CRAMM processing pipeline. Source: docs/cramm_algorithm_flowchart_nature.{svg,pdf,tiff,png} (ready).
- **Fig. 2.** Scene products for the demonstration granule: discrete mineral map, enhanced colour composite, `mus_center`, `chl_center`, `cal_center`. Source: docs/figures/ five-panel product figure (make_paper_figures.py; ready). Candidate graphical abstract.
- **Fig. 3.** Muscovite wavelength arbitration: before/after subtype map, arbitrated center distribution vs calibrated windows, flip-pair census. Source: fig_muscovite_arbitration (make_paper_figures.py). **Regenerate** — flip total corrected to 46,823 (2026-08-24 consistency fix).
- **Fig. 4.** Carbonate anchors: seven-anchor laboratory sequence with the three rule-covered anchors marked; `cal_center` histogram. Source: fig_carbonate (make_paper_figures.py; ready).
- **Fig. 5.** Interpretive framework: wv2200 isopleths on the GEMS/MINES23.1 T–log(aK⁺/aH⁺) activity diagram with Tschermak-substitution contours. Source: diag111_muscovite_wv2200_application_en (D:\gems\results\). Caption must carry: thermodynamic conditions (P, system, activity model, MINES23.1 version); chaining-by-construction statement; 2190 nm segment beyond spectral calibration domain; 14-sample calibration provenance. [Pending C2 uncertainty bands / C4 caption duties per docs/figure_eval_gems_phase_diagrams.md §7.]
- **Fig. 6.** Single-spectrum diagnostic report example. Source: docs/single_spectrum_diagnostic.png (ready).
- **Fig. 7.** Performance scaling (wall time and throughput vs n_workers; PRISM reference line). To be generated from docs/benchmark.json.

---

## Code availability

CRAMM is open-source under the MIT license. Source code: https://github.com/leecugb/cramm (v1.0.0). Installable from PyPI (https://pypi.org/project/CRAMM/; `pip install cramm`). Archived release: https://doi.org/10.5281/zenodo.22024483. Language: Python 3.9–3.13; top-level dependency: NumPy. The rule-library verification script (docs/verify_mcf_rfjson.py) and the full verification matrix are included in the repository.

## Data availability

The demonstration scene is the public NASA LP DAAC product EMIT_L2A_RFL_001_20220819T061448_2223104_025 (EMIT L2A surface reflectance). [Evidence needed: Earthdata granule metadata confirmation and download URL.]

## CRediT authorship contribution statement

[Author input needed]

## Declaration of competing interest

The author(s) declare no competing interests. [confirm]

## Acknowledgments

[Author input needed — funding, data courtesy]

---

## References (anchors verified in-repo; remaining entries to be completed — paper_preparation.md §8-6)

- Kokaly, R.F., 2011. PRISM: Processing Routines in IDL for Spectroscopic Measurements (Installation Manual and User's Guide, Version 1.0). U.S. Geological Survey Open-File Report 2011-1155. [archived: docs/prism_users_guide_ofr2011-1155.md; page count per TOC ~430 p., verify in final reference pass]
- Kokaly, R.F., King, T.V.V., Hoefen, T.M., 2011. Mapping the distribution of materials in hyperspectral data using the USGS Material Identification and Characterization Algorithm (MICA). Proceedings of IGARSS 2011, pp. 1569–1572. [archived: docs/kokaly2011.md]
- Kokaly, R.F., King, T.V.V., Hoefen, T.M., Dudek, K.B., Livo, K.E., 2013. Surface materials map of Afghanistan: carbonates, phyllosilicates, sulfates, altered minerals, and other materials. U.S. Geological Survey Scientific Investigations Map 3152-A (DS 787). [verify against archived PDF: docs/DS787_summary.md]
- [Reference to verify: Clark et al. 2003, Tetracorder / imaging spectroscopy expert systems, JGR 108(E12)]
- [Reference to verify: Clark et al. 2007, USGS digital spectral library splib06b, USGS DS 231]
- [Reference to verify: EMIT mission and L2A ATBD entries]
- [Reference to verify: chlorite calibration set (chl13) source; muscovite 14-sample calibration source; structural-formula data sources (Bartel XRF for CCa-1)]
- [Reference to verify: GEMS / MINES23.1 thermodynamic database entries]
- [Reference to verify: Duke 1994 / Post & Noble 1993 wv2200–Tschermak lineage if cited in Discussion]
