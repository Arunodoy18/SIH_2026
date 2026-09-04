"""Per-hazard susceptibility fields on the common grid, each rescaled to 0..1.

These are transparent, parameterised proxies calibrated to *look* like the real layers
(GSI landslide susceptibility, BIS seismic zonation, Bhuvan flood hazard). Swap each for the
real raster via redzone/data/adapters/ — the composite/calibration code downstream is agnostic.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np

from redzone.config import CRS_METRIC, HazardParams
from redzone.hazard import grid as G


def _centroids_lonlat(gdf: gpd.GeoDataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Polygon centroids as lon/lat, computed in a projected CRS (no geographic warning)."""
    c = gdf.to_crs(CRS_METRIC).geometry.centroid
    c = gpd.GeoSeries(c, crs=CRS_METRIC).to_crs("EPSG:4326")
    return c.x.to_numpy(), c.y.to_numpy()


def seismic_field(faults: gpd.GeoDataFrame, rivers: gpd.GeoDataFrame) -> np.ndarray:
    """BIS Zone IV baseline (~0.66), lifted near active lineaments and on soft valley fill.

    Site amplification: unconsolidated sediment on the valley floor shakes harder than
    bedrock ridges, so proximity to the trunk river adds to the score — this is the spatial
    structure that lets seismic loss vary across a district that is uniformly Zone IV.
    """
    base = np.full((G.GRID.ny, G.GRID.nx), 0.66, dtype="float32")
    near_fault = G.decay(G.distance_km(G.burn(faults)), scale_km=6.0)
    valley_amp = G.decay(G.distance_km(G.burn(rivers)), scale_km=1.5)
    field = base + 0.24 * near_fault + 0.16 * valley_amp
    return G.smooth(np.clip(field, 0, 1), sigma_km=1.2)


def landslide_field(habitations: gpd.GeoDataFrame, rivers: gpd.GeoDataFrame,
                    p: HazardParams) -> np.ndarray:
    """Slope proxy + antecedent rainfall + chronic-incident hotspots + valley-wall steepness."""
    lon, lat = G.lonlat_mesh()

    # slope proxy: interpolate habitation slope_gt30_pct onto the grid via IDW, then
    # add a north-rising alpine trend (terrain gets steeper up-valley).
    slope = _idw(habitations, "slope_gt30_pct", lon, lat) / 100.0
    northness = (lat - G.GRID.min_lat) / (G.GRID.max_lat - G.GRID.min_lat)
    slope = np.clip(0.6 * slope + 0.4 * northness, 0, 1)

    rain = _idw(habitations, "annual_rainfall_mm", lon, lat)
    rain = G.norm01(rain) * p.rain_multiplier * (1.15 if p.monsoon else 0.8)

    # chronic landslide points — habitation centroids weighted by recorded incidents
    cx, cy = _centroids_lonlat(habitations)
    inc = habitations["landslide_incidents"].to_numpy(float)
    hot_field = np.zeros((G.GRID.ny, G.GRID.nx), dtype="float32")
    for xi, yi, ni in zip(cx, cy, inc):
        if ni <= 0:
            continue
        pt = gpd.GeoDataFrame(geometry=gpd.points_from_xy([xi], [yi]), crs="EPSG:4326")
        hot_field = np.maximum(hot_field, ni / 5.0 * G.decay(G.distance_km(G.burn(pt)), 3.0))

    # steep valley walls: a band a short way back from the river lines
    dr = G.distance_km(G.burn(rivers))
    valley_wall = G.decay(np.abs(dr - 0.6), 0.8) * slope

    field = 0.42 * slope + 0.24 * np.clip(rain, 0, 1) + 0.24 * hot_field + 0.10 * valley_wall
    return G.norm01(G.smooth(field, sigma_km=0.9))


def flood_field(rivers: gpd.GeoDataFrame, habitations: gpd.GeoDataFrame,
                p: HazardParams) -> np.ndarray:
    """Flash-flood / riverine: proximity to channel + downstream accumulation + rainfall."""
    lon, lat = G.lonlat_mesh()
    dr = G.distance_km(G.burn(rivers))
    near_channel = G.decay(dr, scale_km=1.2)

    # crude flow accumulation: cells lower in the basin (further south along the main stem)
    # inherit more contributing area -> wetter.
    southness = 1.0 - (lat - G.GRID.min_lat) / (G.GRID.max_lat - G.GRID.min_lat)
    accumulation = near_channel * (0.4 + 0.6 * southness)

    rain = G.norm01(_idw(habitations, "annual_rainfall_mm", lon, lat))
    rain = rain * p.rain_multiplier * (1.2 if p.monsoon else 0.7)

    field = 0.55 * near_channel + 0.30 * accumulation + 0.15 * np.clip(rain, 0, 1)
    return G.norm01(G.smooth(field, sigma_km=0.7))


def _idw(gdf: gpd.GeoDataFrame, col: str, lon: np.ndarray, lat: np.ndarray,
         power: float = 2.0) -> np.ndarray:
    """Inverse-distance-weighted interpolation of a habitation attribute onto the grid."""
    px, py = _centroids_lonlat(gdf)
    v = gdf[col].to_numpy(dtype="float32")
    out = np.zeros_like(lon, dtype="float32")
    wsum = np.zeros_like(lon, dtype="float32")
    for xi, yi, vi in zip(px, py, v):
        d2 = (lon - xi) ** 2 + (lat - yi) ** 2 + 1e-9
        w = 1.0 / d2 ** (power / 2.0)
        out += w * vi
        wsum += w
    return (out / wsum).astype("float32")
