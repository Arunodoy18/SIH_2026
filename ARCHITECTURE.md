# Architecture & methodology

## Data model

**Habitation** (unit of analysis) — a Gram Panchayat Unit / Census village, one polygon +:

| group | fields |
|---|---|
| identity | `hab_id`, `name`, `block`, `district`, `lat`, `lon` (settlement point), `area_sqkm` |
| exposure | `population`, `households` |
| social (Census/SECC) | `sc_pct`, `st_pct`, `kutcha_pct`, `elderly_pct`, `children_pct`, `bpl_pct`, `literacy_pct`, `isolation_index` |
| physiography | `forest_pct`, `slope_gt30_pct`, `annual_rainfall_mm`, `spring_discharge_lpm`, `lifeline_road_count`, `hospital_beds`, `school_seats`, `landslide_incidents`, `river_dist_km` |
| **hazard** (computed) | `haz_landslide`, `haz_glof`, `haz_seismic`, `haz_flood`, `haz_composite`, `haz_tier` |
| **capacity** (computed) | `cc_water_pop`, `cc_land_pop`, `cc_evacuation_pop`, `cc_services_pop`, `cc_sustainable_pop`, `cc_effective_pop`, `cc_deficit_ratio`, `cc_limiting_factor`, `cc_status` |
| **vulnerability** (computed) | `svi` + `svi_<indicator>` normalised components |
| **priority** (computed) | `priority_index` (absolute), `priority_score` (rank 0–1), `priority_tier` |
| **relocation** (computed) | `persons_relocated`, `assigned_site_id`, `eal_inr`, `relocation_capex_inr`, `pv_benefit_inr`, `benefit_cost_ratio`, `payback_years` |

Supporting layers: `glacial_lakes` (area 2000 vs 2024, dam type, volume, downstream path), `rivers`, `faults`, `destination_sites` (spare capacity, servicing cost, hazard tier), `historical_losses` (event type, year, deaths, houses damaged).

## Deliverable 1 — hazard red zones  (`redzone/hazard/`)

1. **Common grid** — everything resampled to a 0.0025° (~250 m) raster over the AOI.
2. **Per-hazard susceptibility 0–1** (`fields.py`, `glof.py`), each a transparent proxy for the real layer:
   - **landslide** — slope proxy (IDW of `slope_gt30_pct` + alpine trend) + antecedent rainfall × monsoon + chronic-incident hotspots + valley-wall steepness.
   - **GLOF** — per lake: hazard potential from dam type (moraine > ice > bedrock) × impounded volume × observed area growth (+ N-year projection); trace the downstream path (snap to river network → follow the Teesta main stem to outlet); attenuate intensity along-channel (scale = reach ∝ √volume) inside a valley-floor corridor (half-width ∝ √volume).
   - **seismic** — BIS Zone IV baseline + near-fault uplift + **valley-fill site amplification** (the spatial structure that lets a uniformly-Zone-IV district vary).
   - **flood** — channel proximity + downstream flow accumulation + rainfall × monsoon.
3. **Calibration** (`calibrate.py`) — NNLS of standardised historical loss (`log1p(houses + 20·deaths)`) on per-hazard susceptibility at each event location → fitted weights; **capped** (no fitted weight > 0.60), **blended** with the AHP prior (45%), **floored** at 0.6 × prior so no hazard drops out. Diagnostics: composite R² and Spearman vs loss, ranking AUC (event sites vs random cells), plus the raw 4-way decomposition R²/LOO-R² (reported but not featured — individual attribution is uncertain at n≈20).
4. **Composite + tiers** (`composite.py`) — weighted sum → 0–1; tiers cut at **quantiles** of the composite over the grid (relative zonation, as GSI/BMTPC susceptibility maps are classed).
5. **Per-habitation exposure** — blend of hazard *at the settlement point* (0.60) + polygon p85 (0.25) + polygon mean (0.15); linear hazards only touch the valley floor where people live, so a plain polygon mean under-reads them.

Current calibrated weights on the synthetic seed: **GLOF ~0.49, landslide ~0.23, seismic ~0.16, flood ~0.12** (shifts slightly run to run depending on the landslide method — see below) — AHP put GLOF at 0.24; the loss record (dominated by Oct 2023) moves it to ~0.49.

### Landslide susceptibility — trained model, not a fixed formula

`redzone/ml/` replaces the hand-tuned decay-kernel landslide field with a **RandomForestClassifier**, the standard technique in landslide susceptibility mapping (LSM) literature:

1. `generate_landslide_inventory.py` — since no real GSI/Bhukosh inventory is wired in yet, presence points are drawn from a *latent* occurrence probability with the same physical drivers as the old heuristic (slope, rainfall, forest cover, river/fault proximity) but a **different functional form** — a logistic model with a slope×rainfall interaction, sampled with probability ∝ latent⁵ (landslides occur past a susceptibility threshold, not smoothly proportional to it) — plus 15% uniform noise for realism. Pseudo-absence points are uniform-random, standard LSM practice. This makes training a genuine fit, not a relabelled reproduction of the heuristic.
2. `train_landslide_model.py` — 300-tree RandomForest, 6 features (slope, rainfall, forest cover, river/fault distance, northness), stratified 80/20 split. Current held-out **ROC-AUC ≈ 0.78** — a credible number for 6 coarse 250 m-resolution proxy features, not suspiciously perfect.
3. `landslide_ml.py` — inference; `hazard/__init__.py` uses it automatically when a trained model is on disk (`HazardParams.landslide_method = "ml"`), falling back to the original heuristic otherwise — no hard dependency, no crash if untrained.

Swap step 1's synthetic points for a real inventory (GSI Bhukosh) and steps 2–3 are unchanged.

### Seismic temporal outlook — Gutenberg–Richter + elastic rebound

The spatial seismic field (BIS zone + fault proximity + site amplification) has no time dimension. `hazard/seismic_gr.py` adds one, district-level:

- **Gutenberg–Richter law** `log₁₀N(≥M) = a − b·M` — the long-run annual rate of earthquakes at or above a magnitude, anchored so M≥6.0 has a ~75-year regional return period (b = 0.9, typical for the Himalaya) → converted to a Poisson exceedance probability.
- **Elastic rebound (Reid, 1910) → Brownian Passage Time renewal model** — strain resets near zero right after a rupture, so recurrence isn't memoryless. Closed-form BPT CDF (Matthews, Ellsworth & Reasenberg, 2002), anchored to the real **2011 M6.9 Sikkim earthquake** as the last reset. Result: near-term probability is currently *suppressed* relative to naive Poisson (10-yr window: ~1.6% renewal vs ~12.5% Poisson) — the actual signature elastic rebound predicts, and a real, testable property (`tests/test_seismic_gr.py`).

Both parameters are literature-typical for the Eastern Himalaya, not fit to a project-specific catalog — flagged the same way as the capacity norms. Exposed in `summary.seismic_outlook`, not yet decomposed to individual fault segments (needs finer public seismotectonic data than exists at this scale).

## Deliverable 2 — carrying capacity  (`redzone/capacity/`) — WORKING STUB

`sustainable_pop = combine(water, land, evacuation, services)`; `deficit_ratio = effective_pop / sustainable_pop` where `effective_pop = population × (1 + growth%) × tourist_load`.

- **water** — local rainfall-runoff (bounded footprint × runoff coeff × usable yield) + spring discharge, ÷ per-capita demand (70 lpcd).
- **land** — bounded footprint × (1 − forest) × (1 − steep) × habitable-altitude fraction ÷ built-area-per-capita (150 m²).
- **evacuation** — lifeline-road count × lane capacity (800 pph) × warning window (6 h).
- **services** — own beds/seats vs IPHS/RTE norms + referral headroom from the nearest town, scaled down by isolation.
- **combine** — generalised mean, exponent −3 (binding constraint dominates, others still matter).

**Provisional:** the coefficients above are placeholders. The remaining work for this deliverable is to source each to its norm (BIS 1172 / IS 10500 for water, IRC for road capacity, IPHS 2022 for health, RTE norms for schools, FSI for forest, Dhara Vikas spring atlas) with citations, and to replace the bounded-footprint heuristic with a real built-up mask (Open Buildings). Pipeline wiring and outputs are final.

## Deliverable 3 — relocation priority  (`redzone/relocation/`)

1. **Priority score** (`priority.py`) — `hazard^1.0 · svi^0.7 · (0.3 + deficit_factor)^0.5`, min-max ranked → `priority_score`; also kept absolute as `priority_index`.
   **Hazard gate:** `relocate_now` requires `haz_tier == red`; `plan` requires red/orange. A low-hazard but overcrowded/vulnerable habitation is surfaced as `monitor`, never "relocate now".
2. **Destination sites** — green/yellow sites only, each with spare capacity and servicing cost.
3. **Optimiser** (`optimizer.py`) — min-cost flow with a community-split penalty, solved as a MILP with `scipy.optimize.milp` (HiGHS — no external binary; PuLP/CBC and a greedy heuristic are fallbacks):
   - minimise Σ person-km cost + Σ split penalty + Σ unmet penalty
   - s.t. every at-risk habitation fully accounted for, site capacity respected, distance ≤ cap, a site "opened" before use.
   - **`unmet` demand is a finding**, not an error — it means Phase 1 needs new safe land identified.
4. **Cost–benefit** (`costbenefit.py`) — per habitation:
   `capex = housing + infra/capita + land + servicing + transport`;
   `EAL = (0.30 · haz_composite²) · (0.9·(0.3 + 0.7·svi)) · population · ₹9L`;
   `pv_benefit = EAL · annuity(6%, 25 yr)`; `BCR = pv_benefit / capex`; `payback = capex / EAL`.
5. **Phased plan** (`plan.py`) — Phase 1 = relocate_now, Phase 2 = plan; ordered by BCR within phase; origin→site flow lines (one per leg, so splits are visible).

Current baseline (with the ML landslide model): 3 habitations relocate-now + 4 plan, ~11,300 people, ₹647 cr capex, **portfolio BCR 1.23, payback ~10.4 yr** — figures move a little run to run as the landslide method or calibration shifts; the mechanism, not the exact number, is what to defend.

## Report narrative (GenAI)

`redzone/report/narrative.py` drafts the DDMA report's prose from the already-computed `summary` + `relocation_plan` facts — never asked to invent a number. If `ANTHROPIC_API_KEY` is set, an LLM (`claude-sonnet-5` by default, `NIRNAY_NARRATIVE_MODEL` env override) drafts four short paragraphs (situation, method, plan, economics); any failure — no key, no network, rate limit — falls back silently to a deterministic template built from the same facts dict, so `GET /report/narrative` always returns something usable. This is the one genuinely optional piece in the whole pipeline: the MVP is complete with or without a key.

## Scenario engine

`POST /scenario` patches a copy of `DEFAULT_SETTINGS` (hazard weights, monsoon, glacial-lake growth projection, population growth, tourist load, max relocation distance, discount rate, horizon) and re-runs the whole pipeline in-memory (~2 s). Determinism is per-call (RNGs seeded inside each function), so scenarios don't perturb each other. It does **not** call the narrative endpoint — that stays an explicit, on-demand action so an LLM call (when a key is configured) isn't fired on every slider drag.

## Anticipated judge questions

| question | answer |
|---|---|
| Why these hazard weights? | Not chosen — fitted against the loss record (`calibrate.py`), AHP only as a floored prior. We show R²/AUC vs held-out and random points. |
| Census is 2011. | `population_growth_pct` projects forward per scenario; SVI indicators are ratios (stable); real deployment adds Open Buildings / WorldPop for current built-up. |
| Carrying capacity looks arbitrary. | It partly is today (stub) — every coefficient is a named lever in `config.py` pending norm citations; that sourcing is the stated remaining task. |
| How is this different from the BMTPC Vulnerability Atlas? | That is static, national, coarse, hazard-only. This is GPU-level, hazard × vulnerability × capacity, scenario-driven, and outputs a costed, capacity-constrained relocation plan — a decision, not an atlas. |
| Is the optimiser real? | Yes — a MILP (HiGHS), not a sort. It splits habitations across sites, respects capacity, and reports unmet demand when safe land runs out. |
| Is the landslide "ML" real, or is it your heuristic renamed? | It's a trained RandomForest, evaluated on a held-out split (ROC-AUC ≈ 0.78) — see `redzone/ml/`. The training points are synthetic (no real GSI inventory wired in yet) but generated from a *different* functional form than the heuristic specifically so training is a genuine fit, not a relabelling. Swappable back to the heuristic with one config flag. |
| Why Gutenberg–Richter / elastic rebound for seismic — isn't the BIS zone enough? | The BIS zone is spatial only; it says nothing about *when*. G-R gives the long-run frequency; the BPT renewal model (standard USGS/WGCEP practice) shows near-term probability is presently suppressed because the 2011 M6.9 reset the clock — a real, testable property, not a static label. |
| What if there's no Anthropic API key for the "AI" report? | It falls back to a deterministic template built from the same facts — same endpoint, same shape of output, no crash, clearly marked `mode: "template"` vs `"ai"`. |
