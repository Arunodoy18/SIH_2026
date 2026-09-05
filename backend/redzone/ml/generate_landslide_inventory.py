"""Synthetic landslide inventory for training the susceptibility model.

Presence points are drawn from a latent occurrence probability that uses the SAME physical
drivers as the heuristic field (`hazard/fields.py`) — slope, rainfall, forest cover, river
and fault proximity — but combines them differently: a logistic model with a slope-rainfall
interaction term, not the heuristic's plain weighted sum. So fitting a classifier to these
points is a genuine learning exercise — the RF has to recover a decision surface it wasn't
handed — not a relabelled reproduction of the existing formula.

Pseudo-absence points are sampled uniformly at random, the standard practice in landslide
susceptibility mapping (LSM) when only occurrence, not confirmed-stable, locations exist.

Replace this generator with a real GSI/Bhukosh landslide inventory when available —
`train_landslide_model.py` and `landslide_ml.py` are unaffected by the swap.

Run:  python -m redzone.ml.generate_landslide_inventory
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

from redzone.config import CRS_GEO, INTERIM_DIR
from redzone.data import store
from redzone.hazard import grid as G
from redzone.ml.features import FEATURE_NAMES, grid_features

N_PRESENCE = 550
N_ABSENCE = 900
_WEIGHTED_FRACTION = 0.85  # rest of the "presence" draw is uniform noise, not purely latent-driven
_SHARPEN_POWER = 5  # landslides occur where susceptibility crosses a threshold, not smoothly
                    # proportional to it — sampling weight = latent**power concentrates presence
                    # points in the genuinely high-susceptibility tail instead of the broad middle
RNG = np.random.default_rng(31)  # independent stream from the seed / historical-loss generators


def _latent_probability(feat: dict[str, np.ndarray]) -> np.ndarray:
    """A logistic, interaction-bearing function of the same physical drivers the heuristic
    field uses — deliberately a different functional form so there is something real to learn.
    """
    river_prox = G.decay(feat["river_dist_km"], 1.4)
    fault_prox = G.decay(feat["fault_dist_km"], 9.0)
    logit = (
        2.1 * feat["slope"]
        + 1.0 * feat["rainfall_norm"]
        - 1.3 * feat["forest_norm"]
        + 1.5 * river_prox
        + 1.1 * fault_prox
        + 1.1 * feat["slope"] * feat["rainfall_norm"]   # saturated slopes under heavy rain
        - 1.6
    )
    return 1.0 / (1.0 + np.exp(-logit))


def _sample_points(prob: np.ndarray, n: int, mode: str) -> tuple[np.ndarray, np.ndarray]:
    """mode: 'weighted' (85% latent-probability-weighted / 15% uniform) or 'uniform'."""
    ny, nx = prob.shape
    idx_all = np.arange(prob.size)
    if mode == "weighted":
        n_w = round(n * _WEIGHTED_FRACTION)
        n_u = n - n_w
        w = prob.ravel().astype("float64") ** _SHARPEN_POWER
        w = w / w.sum()
        idx = np.concatenate([
            RNG.choice(idx_all, size=n_w, replace=True, p=w),
            RNG.choice(idx_all, size=n_u, replace=True),
        ])
    else:
        idx = RNG.choice(idx_all, size=n, replace=True)

    rows, cols = np.unravel_index(idx, (ny, nx))
    lon0, lat0 = G.lonlat_mesh()
    jitter_lon = (RNG.random(len(idx)) - 0.5) * G.GRID.res
    jitter_lat = (RNG.random(len(idx)) - 0.5) * G.GRID.res
    lons = (lon0[rows, cols] + jitter_lon).astype("float32")
    lats = (lat0[rows, cols] + jitter_lat).astype("float32")
    return lons, lats


def main() -> None:
    habitations = store.load_interim("habitations")
    rivers = store.load_interim("rivers")
    faults = store.load_interim("faults")

    feat = grid_features(habitations, rivers, faults)
    latent = _latent_probability(feat)

    pres_lon, pres_lat = _sample_points(latent, N_PRESENCE, "weighted")
    abs_lon, abs_lat = _sample_points(latent, N_ABSENCE, "uniform")

    lons = np.concatenate([pres_lon, abs_lon])
    lats = np.concatenate([pres_lat, abs_lat])
    labels = np.concatenate([np.ones(len(pres_lon), int), np.zeros(len(abs_lon), int)])

    rows: dict = {"label": labels}
    for name in FEATURE_NAMES:
        rows[name] = G.sample_points(feat[name], lons, lats)

    gdf = gpd.GeoDataFrame(
        rows, geometry=[Point(x, y) for x, y in zip(lons, lats)], crs=CRS_GEO,
    )
    gdf = gdf.sample(frac=1.0, random_state=7).reset_index(drop=True)  # shuffle presence/absence

    path = INTERIM_DIR / "landslide_inventory.parquet"
    gdf.to_parquet(path)
    print(f"wrote {path}  ({int(labels.sum())} presence, {int((labels == 0).sum())} pseudo-absence)")


if __name__ == "__main__":
    main()
