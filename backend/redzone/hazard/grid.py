"""Raster grid helpers for the hazard model — coordinates, rasterisation, distance, smoothing."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize, shapes
from scipy import ndimage
from shapely.geometry import shape

from redzone.config import CRS_GEO, CRS_METRIC, GRID, PROCESSED_DIR

# mean ground size of one pixel at ~27.6 N, in km (lon shrinks by cos(lat))
_PX_LAT_KM = GRID.res * 111.32
_PX_LON_KM = GRID.res * 111.32 * np.cos(np.deg2rad(0.5 * (GRID.min_lat + GRID.max_lat)))
PIXEL_KM = float(np.sqrt(_PX_LAT_KM * _PX_LON_KM))


def lonlat_mesh() -> tuple[np.ndarray, np.ndarray]:
    """Cell-centre lon/lat arrays, shape (ny, nx), row 0 = north."""
    xs = GRID.min_lon + (np.arange(GRID.nx) + 0.5) * GRID.res
    ys = GRID.max_lat - (np.arange(GRID.ny) + 0.5) * GRID.res
    return np.meshgrid(xs, ys)


def burn(gdf: gpd.GeoDataFrame, value: float = 1.0, all_touched: bool = True) -> np.ndarray:
    """Rasterise geometries onto the grid (1 where covered, 0 elsewhere)."""
    shapes_iter = ((geom, value) for geom in gdf.to_crs(CRS_GEO).geometry if not geom.is_empty)
    return rasterize(
        shapes_iter, out_shape=(GRID.ny, GRID.nx), transform=GRID.transform,
        fill=0.0, all_touched=all_touched, dtype="float32",
    )


def distance_km(mask: np.ndarray) -> np.ndarray:
    """Euclidean distance (km) from every cell to the nearest True/non-zero cell of `mask`."""
    d_px = ndimage.distance_transform_edt(mask == 0)
    return d_px.astype("float32") * PIXEL_KM


def smooth(arr: np.ndarray, sigma_km: float) -> np.ndarray:
    return ndimage.gaussian_filter(arr.astype("float32"), sigma=max(0.1, sigma_km / PIXEL_KM))


def norm01(arr: np.ndarray, lo_pct: float = 1.0, hi_pct: float = 99.0) -> np.ndarray:
    """Percentile-clipped rescale to 0..1 (robust to a few extreme cells)."""
    lo, hi = np.nanpercentile(arr, [lo_pct, hi_pct])
    if hi - lo < 1e-9:
        return np.zeros_like(arr, dtype="float32")
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0).astype("float32")


def decay(dist_km: np.ndarray, scale_km: float) -> np.ndarray:
    """Exponential proximity kernel: 1 at distance 0, ~0.37 at `scale_km`."""
    return np.exp(-dist_km / max(1e-6, scale_km)).astype("float32")


def sample_points(arr: np.ndarray, lons, lats) -> np.ndarray:
    """Nearest-cell value of `arr` at each (lon, lat)."""
    lons = np.asarray(lons, dtype=float)
    lats = np.asarray(lats, dtype=float)
    cols = np.clip(((lons - GRID.min_lon) / GRID.res).astype(int), 0, GRID.nx - 1)
    rows = np.clip(((GRID.max_lat - lats) / GRID.res).astype(int), 0, GRID.ny - 1)
    return arr[rows, cols]


def centroids_lonlat(gdf: gpd.GeoDataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Polygon centroids as lon/lat, computed in a projected CRS (no geographic-CRS warning)."""
    c = gdf.to_crs(CRS_METRIC).geometry.centroid
    c = gpd.GeoSeries(c, crs=CRS_METRIC).to_crs(CRS_GEO)
    return c.x.to_numpy(), c.y.to_numpy()


def idw_interpolate(gdf: gpd.GeoDataFrame, col: str, lon: np.ndarray, lat: np.ndarray,
                    power: float = 2.0) -> np.ndarray:
    """Inverse-distance-weighted interpolation of a habitation attribute onto arbitrary
    lon/lat points (a full grid mesh, or a handful of sample points for ML training)."""
    px, py = centroids_lonlat(gdf)
    v = gdf[col].to_numpy(dtype="float32")
    lon = np.asarray(lon, dtype="float32")
    lat = np.asarray(lat, dtype="float32")
    out = np.zeros_like(lon, dtype="float32")
    wsum = np.zeros_like(lon, dtype="float32")
    for xi, yi, vi in zip(px, py, v):
        d2 = (lon - xi) ** 2 + (lat - yi) ** 2 + 1e-9
        w = 1.0 / d2 ** (power / 2.0)
        out += w * vi
        wsum += w
    return (out / wsum).astype("float32")


def rowcol(lon: float, lat: float) -> tuple[int, int]:
    r = int(np.clip((GRID.max_lat - lat) / GRID.res, 0, GRID.ny - 1))
    c = int(np.clip((lon - GRID.min_lon) / GRID.res, 0, GRID.nx - 1))
    return r, c


def spread_from_sources(source_value: np.ndarray, halfwidth_km: float,
                        hard_cutoff_mult: float = 3.0) -> np.ndarray:
    """Grow a set of valued source cells into a corridor.

    Every cell takes the value of its nearest non-zero source cell, attenuated by an
    exponential kernel in cross-distance (scale = halfwidth_km) and zeroed past
    hard_cutoff_mult * halfwidth_km. Used to turn along-channel GLOF samples into a
    valley-floor inundation band. One EDT — cheap.
    """
    mask = source_value > 0
    if not mask.any():
        return np.zeros_like(source_value, dtype="float32")
    d_px, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)
    nearest = source_value[iy, ix]
    d_km = d_px.astype("float32") * PIXEL_KM
    out = nearest * decay(d_km, halfwidth_km)
    out[d_km > hard_cutoff_mult * halfwidth_km] = 0.0
    return out.astype("float32")


def write_cog(name: str, bands: dict[str, np.ndarray]) -> str:
    """Write a multi-band GeoTIFF to data/processed/. Returns the path."""
    path = PROCESSED_DIR / f"{name}.tif"
    keys = list(bands)
    with rasterio.open(
        path, "w", driver="GTiff", height=GRID.ny, width=GRID.nx, count=len(keys),
        dtype="float32", crs=CRS_GEO, transform=GRID.transform, compress="deflate",
    ) as dst:
        for i, k in enumerate(keys, start=1):
            dst.write(bands[k].astype("float32"), i)
            dst.set_band_description(i, k)
    return str(path)


def polygonize(arr_uint8: np.ndarray, field: str = "value") -> gpd.GeoDataFrame:
    """Vectorise an integer raster into dissolved polygons (for map fill layers)."""
    geoms, vals = [], []
    for geom, val in shapes(arr_uint8.astype("uint8"), transform=GRID.transform):
        geoms.append(shape(geom))
        vals.append(int(val))
    gdf = gpd.GeoDataFrame({field: vals}, geometry=geoms, crs=CRS_GEO)
    return gdf.dissolve(by=field, as_index=False)
