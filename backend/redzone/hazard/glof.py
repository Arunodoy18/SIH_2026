"""Glacial Lake Outburst Flood (GLOF) hazard — Sikkim's signature multi-hazard.

Pipeline per lake:
  1. hazard potential  <- dam type + impounded volume + observed area growth (+ N-year projection)
  2. downstream path   <- snap lake to river network, follow the Teesta main stem to its outlet
  3. inundation field  <- taper intensity along a valley-floor corridor around that path

`build_glof()` returns the combined 0..1 grid plus per-lake records (potential, path, reach,
inundation polygon) for the map and the API.
"""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points, substring, unary_union

from redzone.config import CRS_GEO, CRS_METRIC, HazardParams
from redzone.hazard import grid as G

_DAM_FACTOR = {"moraine": 1.0, "ice": 0.8, "bedrock": 0.35}


@dataclass
class LakeHazard:
    lake_id: str
    name: str
    hazard_potential: float
    projected_area_ha: float
    reach_km: float
    corridor_halfwidth_km: float
    path: LineString
    inundation: object  # shapely Polygon (metric-buffered path), stored in EPSG:4326


def _potential(row, growth_years: int) -> tuple[float, float]:
    dam = _DAM_FACTOR.get(str(row["dam_type"]), 0.6)
    vol = min(1.0, float(row["volume_mcm"]) / 60.0)
    growth_ratio = max(1.0, float(row["growth_ratio"]))
    # compound observed area-growth forward N years (24 yr of record: 2000 -> 2024)
    proj_ratio = growth_ratio ** (1.0 + growth_years / 24.0)
    proj_area = float(row["area_2000_ha"]) * proj_ratio
    growth_f = np.clip((proj_ratio - 1.0) / 3.0, 0.0, 1.0)

    p = 0.45 * dam + 0.30 * vol + 0.25 * growth_f
    if bool(row.get("breached_2023", False)):
        p *= 0.55  # partially drained in 2023 — residual risk only
    return float(np.clip(p, 0.0, 1.0)), float(proj_area)


def _downstream_path(lake_pt: Point, rivers_m: gpd.GeoDataFrame,
                     main_stem_m: LineString) -> LineString:
    """Connector from the lake to the river network, then main stem to its outlet."""
    net = unary_union(rivers_m.geometry.values)
    snap = nearest_points(lake_pt, net)[1]
    # where does that snap point sit along the main stem?
    s_on_stem = main_stem_m.project(nearest_points(snap, main_stem_m)[1])
    tail = substring(main_stem_m, s_on_stem, main_stem_m.length)
    coords = [lake_pt.coords[0], snap.coords[0]] + list(tail.coords)
    # de-duplicate consecutive identical points
    clean = [coords[0]]
    for c in coords[1:]:
        if c != clean[-1]:
            clean.append(c)
    return LineString(clean) if len(clean) > 1 else LineString([lake_pt.coords[0], snap.coords[0]])


def build_glof(lakes: gpd.GeoDataFrame, rivers: gpd.GeoDataFrame,
               p: HazardParams) -> tuple[np.ndarray, list[LakeHazard]]:
    lakes_m = lakes.to_crs(CRS_METRIC).reset_index(drop=True)
    rivers_m = rivers.to_crs(CRS_METRIC)
    main_stem_m = rivers_m.loc[rivers_m["name"] == "Teesta (main stem)", "geometry"].iloc[0]

    field = np.zeros((G.GRID.ny, G.GRID.nx), dtype="float32")
    records: list[LakeHazard] = []

    for i, row in lakes_m.iterrows():
        potential, proj_area = _potential(row, p.glof_lake_growth_years)
        lake_pt = row.geometry.centroid
        path_m = _downstream_path(lake_pt, rivers_m, main_stem_m)

        vol = float(row["volume_mcm"])
        reach_km = 20.0 + 90.0 * np.sqrt(max(vol, 1.0) / 60.0)
        halfwidth_km = 0.6 + 0.30 * np.sqrt(max(vol, 1.0))
        inund_m = path_m.buffer(halfwidth_km * 1000.0, cap_style=2)

        path_geo = gpd.GeoSeries([path_m], crs=CRS_METRIC).to_crs(CRS_GEO).iloc[0]
        inund_geo = gpd.GeoSeries([inund_m], crs=CRS_METRIC).to_crs(CRS_GEO).iloc[0]

        # walk the downstream path, dropping a valued source cell every ~500 m with
        # intensity attenuating along-channel (scale = reach_km), then spread into a
        # valley-floor corridor of half-width `halfwidth_km`.
        src = np.zeros((G.GRID.ny, G.GRID.nx), dtype="float32")
        step_m = 500.0
        n_steps = int(path_m.length // step_m)
        for k in range(n_steps + 1):
            s_km = k * step_m / 1000.0
            val = potential * float(np.exp(-s_km / reach_km))
            if val < 0.05:
                break
            p_geo = gpd.GeoSeries([path_m.interpolate(k * step_m)], crs=CRS_METRIC).to_crs(CRS_GEO).iloc[0]
            r, c = G.rowcol(p_geo.x, p_geo.y)
            src[r, c] = max(src[r, c], val)
        field = np.maximum(field, G.spread_from_sources(src, halfwidth_km))

        records.append(LakeHazard(
            lake_id=str(row.get("lake_id", f"GL-{i+1:02d}")), name=str(row["name"]),
            hazard_potential=round(potential, 3), projected_area_ha=round(proj_area, 1),
            reach_km=round(reach_km, 1), corridor_halfwidth_km=round(halfwidth_km, 2),
            path=path_geo, inundation=inund_geo,
        ))

    return G.smooth(field, sigma_km=0.5), records
