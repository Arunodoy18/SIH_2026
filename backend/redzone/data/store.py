"""Data-access layer.

Everything the pipeline and API read/write goes through here so the physical store
(GeoParquet / GeoJSON / COG files today) can be swapped for PostGIS later without touching
callers. Keep this module free of analytics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np

from redzone.config import CRS_GEO, INTERIM_DIR, PROCESSED_DIR

# ---- interim (seed / ingested source layers) ----------------------------------------

_INTERIM = (
    "habitations", "glacial_lakes", "rivers", "faults", "destination_sites",
    "historical_losses",
)


def load_interim(name: str) -> gpd.GeoDataFrame:
    if name not in _INTERIM:
        raise KeyError(f"unknown interim layer {name!r}; expected one of {_INTERIM}")
    path = INTERIM_DIR / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing — run `python -m redzone.seed.generate_sikkim` first"
        )
    return gpd.read_parquet(path)


def interim_ready() -> bool:
    return all((INTERIM_DIR / f"{n}.parquet").exists() for n in _INTERIM)


# ---- processed (pipeline outputs) --------------------------------------------------

def save_processed_gdf(gdf: gpd.GeoDataFrame, name: str) -> Path:
    path = PROCESSED_DIR / f"{name}.parquet"
    gdf.to_parquet(path)
    return path


def load_processed_gdf(name: str) -> gpd.GeoDataFrame:
    path = PROCESSED_DIR / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `python -m redzone.pipeline` first")
    return gpd.read_parquet(path)


def save_json(obj: Any, name: str) -> Path:
    path = PROCESSED_DIR / f"{name}.json"
    path.write_text(json.dumps(obj, indent=2, default=_json_default))
    return path


def load_json(name: str) -> Any:
    path = PROCESSED_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `python -m redzone.pipeline` first")
    return json.loads(path.read_text())


def save_geojson(gdf: gpd.GeoDataFrame, name: str) -> Path:
    path = PROCESSED_DIR / f"{name}.geojson"
    gdf.to_crs(CRS_GEO).to_file(path, driver="GeoJSON")
    return path


def processed_ready() -> bool:
    return (PROCESSED_DIR / "habitations.parquet").exists() and (
        PROCESSED_DIR / "summary.json"
    ).exists()


def _json_default(o: Any):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON-serialisable: {type(o)}")


def gdf_to_featurecollection(gdf: gpd.GeoDataFrame, keep: list[str] | None = None) -> dict:
    """Compact GeoJSON dict for API responses (avoids a file round-trip)."""
    g = gdf.to_crs(CRS_GEO)
    if keep is not None:
        cols = [c for c in keep if c in g.columns]
        g = g[cols + ["geometry"]]
    return json.loads(g.to_json())
