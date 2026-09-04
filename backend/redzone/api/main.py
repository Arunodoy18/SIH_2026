"""RedZone API — serves the pre-computed DDMA analysis and runs on-the-fly scenarios.

    GET  /health
    GET  /summary                       headline numbers + calibration diagnostics
    GET  /habitations                   FeatureCollection, all scores per habitation
    GET  /habitations/{hab_id}          one habitation + factor breakdown
    GET  /layers/{name}                 hazard_tiers | glacial_lakes | rivers |
                                        destination_sites | historical_losses
    GET  /relocation/plan               phased plan, ranked table, flows, cost-benefit
    POST /scenario                      re-run the pipeline with overrides (in-memory)

Static endpoints read data/processed/ (populated by `python -m redzone.pipeline`).
"""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from redzone.api.schemas import ScenarioRequest
from redzone.config import CRS_GEO
from redzone.data import store
from redzone.pipeline import run_pipeline

app = FastAPI(title="RedZone API", version="0.1.0",
              description="Hazard red zones, carrying capacity & relocation priority — Mangan DDMA, Sikkim")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_LAYER_FILES = {
    "hazard_tiers", "glacial_lakes", "rivers", "destination_sites", "historical_losses",
}


def _geojson_file(name: str) -> dict:
    path = store.PROCESSED_DIR / f"{name}.geojson"
    if not path.exists():
        raise HTTPException(404, f"{name}.geojson not built — run `python -m redzone.pipeline`")
    return json.loads(path.read_text())


@app.get("/health")
def health():
    return {
        "status": "ok",
        "interim_ready": store.interim_ready(),
        "processed_ready": store.processed_ready(),
    }


@app.get("/summary")
def summary():
    try:
        return store.load_json("summary")
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@app.get("/habitations")
def habitations():
    try:
        gdf = store.load_processed_gdf("habitations").to_crs(CRS_GEO)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    return JSONResponse(json.loads(gdf.to_json()))


@app.get("/habitations/{hab_id}")
def habitation(hab_id: str):
    gdf = store.load_processed_gdf("habitations").to_crs(CRS_GEO)
    row = gdf[gdf["hab_id"] == hab_id]
    if row.empty:
        raise HTTPException(404, f"no habitation {hab_id}")
    r = row.iloc[0]
    breakdown = {
        "hazard": {k: _f(r.get(f"haz_{k}")) for k in ("landslide", "glof", "seismic", "flood")},
        "hazard_composite": _f(r.get("haz_composite")),
        "hazard_tier": r.get("haz_tier"),
        "svi": _f(r.get("svi")),
        "svi_components": {c[4:]: _f(r.get(c)) for c in gdf.columns if c.startswith("svi_")},
        "carrying_capacity": {
            "water_pop": _i(r.get("cc_water_pop")), "land_pop": _i(r.get("cc_land_pop")),
            "evacuation_pop": _i(r.get("cc_evacuation_pop")),
            "services_pop": _i(r.get("cc_services_pop")),
            "sustainable_pop": _i(r.get("cc_sustainable_pop")),
            "effective_pop": _i(r.get("cc_effective_pop")),
            "deficit_ratio": _f(r.get("cc_deficit_ratio")),
            "limiting_factor": r.get("cc_limiting_factor"), "status": r.get("cc_status"),
        },
        "priority": {
            "score": _f(r.get("priority_score")), "index": _f(r.get("priority_index")),
            "tier": r.get("priority_tier"),
        },
        "relocation": {
            "persons_relocated": _i(r.get("persons_relocated")),
            "assigned_site_id": r.get("assigned_site_id"),
            "eal_inr": _f(r.get("eal_inr")),
            "relocation_capex_inr": _f(r.get("relocation_capex_inr")),
            "benefit_cost_ratio": _f(r.get("benefit_cost_ratio")),
            "payback_years": _f(r.get("payback_years")),
        },
    }
    return {
        "hab_id": hab_id, "name": r.get("name"), "block": r.get("block"),
        "district": r.get("district"), "population": _i(r.get("population")),
        "households": _i(r.get("households")), "breakdown": breakdown,
        "geometry": row.to_crs(CRS_GEO).geometry.iloc[0].__geo_interface__,
    }


@app.get("/layers/{name}")
def layer(name: str):
    if name not in _LAYER_FILES:
        raise HTTPException(404, f"unknown layer {name!r}; try one of {sorted(_LAYER_FILES)}")
    return JSONResponse(_geojson_file(name))


@app.get("/relocation/plan")
def relocation_plan():
    try:
        return store.load_json("relocation_plan")
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@app.post("/scenario")
def scenario(req: ScenarioRequest):
    settings = req.as_settings()
    r = run_pipeline(settings, persist=False)
    habs = r.habitations.to_crs(CRS_GEO)
    return JSONResponse({
        "summary": r.summary,
        "habitations": json.loads(habs.to_json()),
        "hazard_tiers": json.loads(r.tier_polygons.to_crs(CRS_GEO).to_json()),
        "glacial_lakes": json.loads(r.lakes.to_crs(CRS_GEO).to_json()),
        "relocation_plan": r.plan,
    })


def _f(v):
    try:
        import math
        f = float(v)
        return None if math.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _i(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
