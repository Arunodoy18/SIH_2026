"""End-to-end analytics pipeline.

    seed (interim)  ->  hazard  ->  vulnerability  ->  capacity  ->  relocation  ->  processed/

Run:  python -m redzone.pipeline            (uses default Settings)
The API calls run_pipeline(settings) in-memory for POST /scenario.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import geopandas as gpd

from redzone.capacity import assess_capacity
from redzone.config import CRS_GEO, HAZARDS, PROCESSED_DIR, Settings
from redzone.data import store
from redzone.hazard import build_hazard
from redzone.hazard.grid import write_cog
from redzone.relocation import build_relocation
from redzone.vulnerability import build_svi

_HAB_DROP_FOR_GEOJSON = set()  # keep everything — the drawer uses it all


@dataclass
class PipelineResult:
    habitations: gpd.GeoDataFrame
    tier_polygons: gpd.GeoDataFrame
    lakes: gpd.GeoDataFrame
    plan: dict
    summary: dict


def run_pipeline(settings: Settings | None = None, persist: bool = False) -> PipelineResult:
    settings = settings or Settings()
    t0 = time.time()

    hz = build_hazard(settings)
    hab = build_svi(hz.habitations, method=None)
    hab = assess_capacity(
        hab, settings.capacity,
        population_growth_pct=settings.population_growth_pct,
        tourist_load_factor=settings.tourist_load_factor,
    )
    rel = build_relocation(hab, settings)
    hab = rel.habitations

    lakes = _lake_gdf(hz.lakes)
    summary = _summary(hab, hz, rel.plan, settings, time.time() - t0)

    result = PipelineResult(
        habitations=hab, tier_polygons=hz.tier_polygons, lakes=lakes,
        plan=rel.plan, summary=summary,
    )
    if persist:
        _persist(result, hz)
    return result


def _lake_gdf(lake_records) -> gpd.GeoDataFrame:
    rows = [{
        "lake_id": l.lake_id, "name": l.name, "hazard_potential": l.hazard_potential,
        "projected_area_ha": l.projected_area_ha, "reach_km": l.reach_km,
        "corridor_halfwidth_km": l.corridor_halfwidth_km, "geometry": l.path,
    } for l in lake_records]
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS_GEO)


def _summary(hab, hz, plan, settings: Settings, secs: float) -> dict:
    by_haz = hab["haz_tier"].value_counts().to_dict()
    by_pri = hab["priority_tier"].value_counts().to_dict()
    by_cc = hab["cc_status"].value_counts().to_dict()
    return {
        "aoi": "Mangan DDMA / Teesta corridor, Sikkim (synthetic seed)",
        "generated_s": round(secs, 2),
        "settings": settings.to_dict(),
        "counts": {
            "habitations": len(hab),
            "population": int(hab["population"].sum()),
            "hazard_tiers": {k: int(by_haz.get(k, 0)) for k in ("red", "orange", "yellow", "green")},
            "priority_tiers": {k: int(by_pri.get(k, 0))
                               for k in ("relocate_now", "plan", "monitor", "safe")},
            "capacity_status": {k: int(by_cc.get(k, 0))
                                for k in ("overshoot", "stressed", "balanced", "surplus")},
        },
        "hazard": {
            "weights": hz.weights,
            "tier_breaks": hz.calibration.get("tier_breaks"),
            "calibration": hz.calibration["metrics"],
        },
        "relocation": {
            "phases": plan["phases"],
            "persons_moved": plan["totals"]["persons_moved"],
            "persons_unmet": plan["totals"]["persons_unmet"],
            "total_relocation_capex_inr": plan["totals"]["total_relocation_capex_inr"],
            "pv_losses_avoided_inr": plan["totals"]["pv_losses_avoided_inr"],
            "portfolio_benefit_cost_ratio": plan["totals"]["portfolio_benefit_cost_ratio"],
            "portfolio_payback_years": plan["totals"]["portfolio_payback_years"],
            "solver": plan["solver"],
        },
    }


def _persist(r: PipelineResult, hz) -> None:
    store.save_processed_gdf(r.habitations.to_crs(CRS_GEO), "habitations")
    store.save_geojson(r.habitations, "habitations")
    store.save_processed_gdf(r.tier_polygons, "hazard_tiers")
    store.save_geojson(r.tier_polygons, "hazard_tiers")
    store.save_processed_gdf(r.lakes, "glacial_lakes")
    store.save_geojson(r.lakes, "glacial_lakes")
    for layer in ("rivers", "destination_sites", "historical_losses"):
        store.save_geojson(store.load_interim(layer), layer)
    store.save_json(r.plan, "relocation_plan")
    store.save_json(r.summary, "summary")
    write_cog("hazard_stack", {h: hz.stack[h] for h in HAZARDS})
    write_cog("hazard_composite", {"composite": hz.composite})
    print(f"  processed/ written  ({PROCESSED_DIR})")


def main() -> None:
    if not store.interim_ready():
        raise SystemExit("interim data missing — run `python -m redzone.seed.generate_sikkim`")
    r = run_pipeline(persist=True)
    s = r.summary
    print(f"\npipeline OK in {s['generated_s']}s")
    print(f"  hazard tiers    : {s['counts']['hazard_tiers']}")
    print(f"  priority tiers  : {s['counts']['priority_tiers']}")
    print(f"  capacity status : {s['counts']['capacity_status']}")
    rl = s["relocation"]
    print(f"  relocation      : {rl['persons_moved']:,} moved, {rl['persons_unmet']:,} unmet "
          f"| capex ₹{rl['total_relocation_capex_inr']/1e7:.1f} cr "
          f"| BCR {rl['portfolio_benefit_cost_ratio']} "
          f"| payback {rl['portfolio_payback_years']} yr | solver {rl['solver']}")


if __name__ == "__main__":
    main()
