"""Composite hazard grid, tier classification, and per-habitation zonal statistics."""

from __future__ import annotations

import geopandas as gpd
import numpy as np

from redzone.config import CRS_GEO, HAZARD_TIERS, HAZARDS
from redzone.hazard import grid as G

# per-habitation exposure = blend of (value at the settlement point) + (upper tail of the
# admin polygon) + (polygon mean). Linear hazards (GLOF, flash flood) only touch the valley
# floor where people live, so the plain polygon mean under-reads them badly.
_ZONAL_BLEND = (0.60, 0.25, 0.15)  # point, p85, mean


def composite_grid(stack: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    w = np.array([weights[h] for h in HAZARDS], dtype="float32")
    w = w / w.sum()
    out = sum(w[i] * stack[h] for i, h in enumerate(HAZARDS))
    return np.clip(out, 0.0, 1.0).astype("float32")


def tier_breaks_from_quantiles(comp: np.ndarray, q: dict[str, float]) -> dict[str, float]:
    vals = comp[comp > 0.02]
    if vals.size == 0:
        vals = comp.ravel()
    return {k: float(np.quantile(vals, qv)) for k, qv in q.items()}


def classify(value: float, breaks: dict[str, float]) -> str:
    if value >= breaks["red"]:
        return "red"
    if value >= breaks["orange"]:
        return "orange"
    if value >= breaks["yellow"]:
        return "yellow"
    return "green"


def tier_grid(comp: np.ndarray, breaks: dict[str, float]) -> np.ndarray:
    t = np.zeros(comp.shape, dtype="uint8")
    t[comp >= breaks["yellow"]] = 1
    t[comp >= breaks["orange"]] = 2
    t[comp >= breaks["red"]] = 3
    return t


def tier_name(idx: int) -> str:
    return HAZARD_TIERS[int(idx)]


def _zonal_value(arr: np.ndarray, geom, pt_lon: float, pt_lat: float) -> float:
    pv = float(G.sample_points(arr, [pt_lon], [pt_lat])[0])
    mask = G.burn(gpd.GeoDataFrame(geometry=[geom], crs=CRS_GEO)) > 0
    if mask.any():
        cells = arr[mask]
        p85 = float(np.quantile(cells, 0.85))
        mean = float(cells.mean())
    else:
        p85 = mean = pv
    a, b, c = _ZONAL_BLEND
    return a * pv + b * p85 + c * mean


def zonal_stats(habitations: gpd.GeoDataFrame, stack: dict[str, np.ndarray],
                comp: np.ndarray, breaks: dict[str, float]) -> gpd.GeoDataFrame:
    hab = habitations.to_crs(CRS_GEO).copy()
    for h in HAZARDS:
        hab[f"haz_{h}"] = [
            round(_zonal_value(stack[h], g, lon, lat), 3)
            for g, lon, lat in zip(hab.geometry, hab["lon"], hab["lat"])
        ]
    hab["haz_composite"] = [
        round(_zonal_value(comp, g, lon, lat), 3)
        for g, lon, lat in zip(hab.geometry, hab["lon"], hab["lat"])
    ]
    hab["haz_tier"] = hab["haz_composite"].map(lambda v: classify(v, breaks))
    return hab


def tier_polygons(tiers: np.ndarray) -> gpd.GeoDataFrame:
    gdf = G.polygonize(tiers, field="tier_idx")
    gdf["tier"] = gdf["tier_idx"].map(tier_name)
    return gdf[["tier", "tier_idx", "geometry"]]
