"""Shared feature computation for the landslide-susceptibility ML model.

One implementation used both to build the synthetic training inventory (features sampled
at point locations) and at inference time (features computed on the full hazard grid) —
so training and inference are guaranteed consistent. Standard LSM (landslide susceptibility
mapping) feature set: slope, rainfall, land cover (forest), drainage proximity, structural
(fault) proximity, terrain position.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np

from redzone.hazard import grid as G

FEATURE_NAMES = (
    "slope", "rainfall_norm", "forest_norm", "river_dist_km", "fault_dist_km", "northness",
)


def grid_features(habitations: gpd.GeoDataFrame, rivers: gpd.GeoDataFrame,
                  faults: gpd.GeoDataFrame) -> dict[str, np.ndarray]:
    lon, lat = G.lonlat_mesh()
    northness = ((lat - G.GRID.min_lat) / (G.GRID.max_lat - G.GRID.min_lat)).astype("float32")

    slope = G.idw_interpolate(habitations, "slope_gt30_pct", lon, lat) / 100.0
    slope = np.clip(0.55 * slope + 0.45 * northness, 0, 1).astype("float32")

    rainfall_norm = G.norm01(G.idw_interpolate(habitations, "annual_rainfall_mm", lon, lat))
    forest_norm = G.norm01(G.idw_interpolate(habitations, "forest_pct", lon, lat))

    return {
        "slope": slope,
        "rainfall_norm": rainfall_norm.astype("float32"),
        "forest_norm": forest_norm.astype("float32"),
        "river_dist_km": G.distance_km(G.burn(rivers)).astype("float32"),
        "fault_dist_km": G.distance_km(G.burn(faults)).astype("float32"),
        "northness": northness,
    }


def stack_features(feat: dict[str, np.ndarray]) -> np.ndarray:
    """(n_cells, n_features) matrix, row-major flatten, columns ordered as FEATURE_NAMES."""
    return np.column_stack([feat[k].ravel() for k in FEATURE_NAMES])
