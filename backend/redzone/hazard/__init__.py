"""Deliverable 1 — intelligent identification of hazard-based red zones.

`build_hazard(settings)` runs the whole chain and returns a HazardResult:
  stack      dict of 4 per-hazard 0..1 grids (landslide, glof, seismic, flood)
  weights    final composite weights (calibrated + AHP prior, or AHP-only)
  composite  0..1 composite hazard grid
  tiers      uint8 grid (0 green .. 3 red)
  habitations  GeoDataFrame with haz_* columns + haz_tier per habitation
  tier_polygons  dissolved tier polygons for the map
  lakes      per-lake GLOF records (potential, downstream path, reach, inundation)
  calibration  weights + fit diagnostics
"""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import numpy as np

from redzone.config import AHP_WEIGHTS, HAZARDS, Settings
from redzone.data import store
from redzone.hazard import composite as C
from redzone.hazard import fields as F
from redzone.hazard import synth_losses
from redzone.hazard.calibrate import calibrate_weights
from redzone.hazard.glof import LakeHazard, build_glof


@dataclass
class HazardResult:
    stack: dict
    weights: dict
    composite: np.ndarray
    tiers: np.ndarray
    habitations: gpd.GeoDataFrame
    tier_polygons: gpd.GeoDataFrame
    lakes: list  # list[LakeHazard]
    calibration: dict
    losses: gpd.GeoDataFrame  # historical events with (synthesised) loss magnitudes


def build_hazard(settings: Settings | None = None) -> HazardResult:
    settings = settings or Settings()
    p = settings.hazard

    habitations = store.load_interim("habitations")
    rivers = store.load_interim("rivers")
    faults = store.load_interim("faults")
    lakes_gdf = store.load_interim("glacial_lakes")
    losses = store.load_interim("historical_losses")

    glof_grid, lake_records = build_glof(lakes_gdf, rivers, p)
    stack = {
        "landslide": F.landslide_field(habitations, rivers, p),
        "glof": glof_grid,
        "seismic": F.seismic_field(faults, rivers),
        "flood": F.flood_field(rivers, habitations, p),
    }

    losses = synth_losses.synthesize(stack, losses)
    calib = calibrate_weights(
        stack, losses, composite_of=lambda w: C.composite_grid(
            stack, {h: float(w[i]) for i, h in enumerate(HAZARDS)})
    )
    if p.weight_override:
        weights = {h: float(p.weight_override.get(h, calib["weights"][h])) for h in HAZARDS}
    elif p.use_calibrated_weights:
        weights = dict(calib["weights"])
    else:
        weights = dict(AHP_WEIGHTS)
    _wsum = sum(weights.values()) or 1.0
    weights = {h: round(weights[h] / _wsum, 3) for h in HAZARDS}

    comp = C.composite_grid(stack, weights)
    if p.tier_mode == "quantile":
        breaks = C.tier_breaks_from_quantiles(comp, p.tier_quantiles)
    else:
        breaks = dict(p.tier_breaks)
    tiers = C.tier_grid(comp, breaks)
    hab_scored = C.zonal_stats(habitations, stack, comp, breaks)
    tier_polys = C.tier_polygons(tiers)
    calib["tier_breaks"] = {k: round(v, 3) for k, v in breaks.items()}

    return HazardResult(
        stack=stack, weights=weights, composite=comp, tiers=tiers,
        habitations=hab_scored, tier_polygons=tier_polys, lakes=lake_records,
        calibration=calib, losses=losses,
    )


__all__ = ["HazardResult", "LakeHazard", "build_hazard"]
