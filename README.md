# RedZone — Hazard Red Zones, Carrying Capacity & Relocation Priority

Pre-disaster planning and decision-support for a **District Disaster Management Authority (DDMA)**.
Primary demo state: **Sikkim** — Mangan DDMA / Teesta-corridor (Chungthang → Dikchu → Singtam → Rangpo, extending into Gangtok district).

SIH 2026 · Problem: *Intelligent Identification of Hazard-Based Red Zones, Carrying Capacity Assessment, and Immediate Relocation Needs for Vulnerable Habitations.*

Deploying? Frontend → Netlify, backend → Render — see **[DEPLOYMENT.md](DEPLOYMENT.md)** for why that split is necessary and the exact steps.

---

## What it does (three deliverables)

| # | Deliverable | Module | Status |
|---|---|---|---|
| 1 | **Hazard red zones** — multi-hazard composite (landslide + GLOF + seismic + flash flood) on a common grid → red / orange / yellow / green tiers, weights **calibrated on historical disaster loss**; landslide susceptibility from a **trained RandomForest** (falls back to a heuristic if untrained); seismic exposure adds a **Gutenberg–Richter + elastic-rebound (BPT renewal) temporal outlook** | `redzone/hazard/`, `redzone/ml/` | real impl |
| 2 | **Carrying capacity** — sustainable vs current population from water, buildable land, evacuation-road capacity, health/school capacity → **deficit ratio** per habitation | `redzone/capacity/` | working stub (deterministic; norms not yet calibrated) |
| 3 | **Relocation priority** — composite = hazard × social vulnerability × capacity deficit → tiers (relocate now / plan / monitor / safe), **capacitated assignment** to nearest green destination sites, **cost–benefit** (relocation capex vs expected annual loss → payback) | `redzone/relocation/` | real impl |

Delivered as a **planner's dashboard**: hazard-tier map, per-habitation factor breakdown, ranked table, relocation flow map, scenario sliders, exportable DDMA report.

## USP

1. **Calibrated, not assumed** — hazard weights fit against historical loss records (`hazard/calibrate.py`), not hand-picked AHP. AHP weights are only the prior/fallback.
2. **Trained, not hand-tuned** — landslide susceptibility is a RandomForest trained on a presence/pseudo-absence inventory (`redzone/ml/`), evaluated by held-out ROC-AUC, not a fixed decay-kernel formula. Swappable back to the heuristic via one config flag.
3. **Seismic hazard has a clock** — `hazard/seismic_gr.py` adds a Gutenberg–Richter frequency model plus an elastic-rebound (Brownian Passage Time) renewal probability anchored to the real 2011 M6.9 Sikkim earthquake, so near-term seismic risk reflects time-since-last-rupture, not just a static BIS zone.
4. **Relocation as optimization** — `relocation/optimizer.py` solves a capacitated generalized-assignment problem (MILP via SciPy/HiGHS, PuLP/greedy fallback): which habitations move first, to which green site, respecting each site's spare capacity, minimizing cost + distance + community-split. Surfaces **unmet demand** when safe land runs out.
5. **Cost–benefit per settlement** — `relocation/costbenefit.py`: one-time relocation capex vs 25-year discounted expected losses → payback years and benefit–cost ratio. The language a DDMA uses to request funds.
6. **GenAI report narrative** — `redzone/report/narrative.py` drafts the DDMA report prose from the computed facts via Groq (primary — fast, generous free tier, `GROQ_API_KEY`) or Anthropic (secondary, `ANTHROPIC_API_KEY`), falling back to a deterministic template when neither is set or a call fails — the MVP is complete either way. All money figures are pre-formatted in code before the model ever sees them; it drafts prose, never arithmetic.

## Stack (lightweight, file-based — migrates to PostGIS later behind `redzone/data/store.py`)

- **Pipeline / API**: Python 3.9+ · GeoPandas · Shapely 2 · rasterio · NumPy · SciPy · scikit-learn + joblib (landslide RF) · PuLP · FastAPI · Uvicorn · Groq + Anthropic SDKs (both optional, GenAI narrative)
- **Storage**: GeoParquet + GeoJSON + Cloud-Optimized GeoTIFF + trained model artifacts (all in `backend/data/`)
- **Frontend**: React + Vite + TypeScript + MapLibre GL + Recharts

## Layout

```
backend/
  redzone/
    config.py            AOI, CRS, grid resolution, default weights, cost params, norms
    seed/                synthetic Sikkim generator (habitations, glacial lakes, rivers,
                         destination sites, historical losses)
    data/
      store.py           data-access layer (file-based now, PostGIS-swappable)
      adapters/          real-source adapters — Bhuvan/GSI/BIS/IMD/Census/SECC/glacial-lake (stubs)
    hazard/              fields · glof · seismic_gr (G-R + elastic rebound) · composite ·
                         calibrate   [DELIVERABLE 1]
    ml/                  features · generate_landslide_inventory · train_landslide_model ·
                         landslide_ml (trained RandomForest, falls back to the heuristic)
    capacity/            water · land · evacuation · services · deficit   [DELIVERABLE 2 — stub]
    vulnerability/       svi (social vulnerability index)
    relocation/          priority · destinations · optimizer · costbenefit · plan   [DELIVERABLE 3]
    report/              narrative.py — GenAI (Anthropic) or template DDMA report prose
    pipeline.py          orchestrates all stages -> data/processed/
    api/                 FastAPI app + routes + pydantic schemas
  data/models/           trained model artifacts (gitignored, regenerate via `make train-ml`)
  tests/
frontend/
  src/                   MapView · LayerPanel · ScenarioPanel · HabitationDrawer ·
                         RelocationView · RankedTable · SummaryStats
DATA_SOURCES.md          real dataset registry (source, level, licence, how to acquire)
ARCHITECTURE.md          data model + scoring methodology + calibration + judge-defence notes
```

## Quickstart

```bash
# 1. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install -e .

python -m redzone.seed.generate_sikkim              # -> data/interim/  synthetic Sikkim
python -m redzone.ml.generate_landslide_inventory   # -> data/interim/landslide_inventory.parquet
python -m redzone.ml.train_landslide_model          # -> data/models/landslide_rf.joblib (+ metrics)
python -m redzone.pipeline                          # -> data/processed/ hazard grid, scores, plan
export GROQ_API_KEY=...                             # optional — enables GenAI report narrative (fast, free tier)
export ANTHROPIC_API_KEY=...                        # optional secondary provider, same fallback
uvicorn redzone.api.main:app --reload               # http://127.0.0.1:8000/docs

# 2. Frontend  (separate terminal)
cd frontend
npm install
npm run dev                                 # http://127.0.0.1:5173
```

Or: `make seed && make train-ml && make pipeline && make api` / `make web`. Skipping the ML steps
is fine — `hazard/` falls back to the heuristic landslide field automatically when no trained
model is on disk, and `/report/narrative` falls back to a template when no API key is set.

## Team split (6)

| Role | Owns |
|---|---|
| Geo/data pipeline ×2 | `seed/`, `data/adapters/`, real dataset acquisition (`DATA_SOURCES.md`), `hazard/normalize.py`, DEM/slope/river derivation |
| Modelling ×1 | `hazard/composite.py` + `calibrate.py`, `relocation/optimizer.py` + `costbenefit.py`, `vulnerability/svi.py` |
| Full-stack ×2 | `api/`, entire `frontend/` |
| Domain / validation / deck ×1 | `capacity/` norms + citations, historical-loss validation, `ARCHITECTURE.md` judge-defence, report template |

See `ARCHITECTURE.md` for methodology and the anticipated judge questions.
