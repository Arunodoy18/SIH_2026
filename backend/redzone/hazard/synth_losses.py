"""Fabricate historical-loss magnitudes from the hazard stack for the synthetic seed.

The seed fixes *where* and *what type* each past event was (that is "known history"); this
module fills in deaths / houses_damaged so that loss actually tracks the modelled hazard —
which is what makes the calibration in `calibrate.py` a meaningful demonstration rather than
a fit to noise.

loss_latent(event) = Σ_h  w_true[h] · hazard_h(location)            [w_true = LATENT_LOSS_WEIGHTS]
                     · type_boost   (the event's own hazard type counts double)
deaths, houses    = exposure · loss_latent · lognormal noise

Replace this entire module with a loader for real SDMA / DesInventar records when available.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np

from redzone.config import HAZARDS, LATENT_LOSS_WEIGHTS
from redzone.hazard import grid as G


def _window_mean(arr: np.ndarray, lon: float, lat: float, k: int = 1) -> float:
    c = int(np.clip((lon - G.GRID.min_lon) / G.GRID.res, 0, G.GRID.nx - 1))
    r = int(np.clip((G.GRID.max_lat - lat) / G.GRID.res, 0, G.GRID.ny - 1))
    r0, r1 = max(0, r - k), min(G.GRID.ny, r + k + 1)
    c0, c1 = max(0, c - k), min(G.GRID.nx, c + k + 1)
    return float(arr[r0:r1, c0:c1].mean())


def synthesize(stack: dict[str, np.ndarray], losses: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    rng = np.random.default_rng(2023)  # per-call: identical output regardless of call order
    out = losses.copy()
    w = LATENT_LOSS_WEIGHTS
    deaths, houses = [], []
    for _, ev in out.iterrows():
        lon, lat = ev.geometry.x, ev.geometry.y
        h_at = {h: _window_mean(stack[h], lon, lat) for h in HAZARDS}
        latent = sum(w[h] * h_at[h] for h in HAZARDS)
        et = str(ev["hazard_type"])
        if et in h_at:  # the event's own hazard type dominates its loss
            latent += 0.6 * w.get(et, 0.25) * h_at[et]
        latent = max(latent, 1e-3)

        noise_d = float(rng.lognormal(mean=0.0, sigma=0.35))
        noise_h = float(rng.lognormal(mean=0.0, sigma=0.30))
        deaths.append(int(round(np.clip(14.0 * latent * noise_d, 0, 60))))
        houses.append(int(round(np.clip(320.0 * latent * noise_h, 3, 900))))

    out["deaths"] = deaths
    out["houses_damaged"] = houses
    out["loss_latent"] = [
        round(sum(LATENT_LOSS_WEIGHTS[h] * _window_mean(stack[h], g.x, g.y) for h in HAZARDS), 4)
        for g in out.geometry
    ]
    return out
