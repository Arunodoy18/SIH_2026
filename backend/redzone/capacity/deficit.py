"""Carrying-capacity deficit per habitation  [Deliverable 2 — working stub].

sustainable_pop = combine( water, land, evacuation, services )   # 'limiting' => the binding one
effective_pop   = current_pop x (1 + growth%) x tourist_load
deficit_ratio   = effective_pop / sustainable_pop                 # > 1 => over carrying capacity
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np

from redzone.config import CAPACITY_NORMS, CapacityNorms

_CATCHMENT_YIELD = 0.15     # STUB: usable fraction of local rainfall-runoff
_SETTLEMENT_AREA_CAP_SQKM = 12.0   # a settlement uses a bounded footprint, not its whole GPU
_REFERRAL_BASE = 1800      # STUB: service headroom via the nearest town (scaled by accessibility)


def _northness(lat: np.ndarray) -> np.ndarray:
    return np.clip((lat - 27.15) / (28.10 - 27.15), 0.0, 1.0)


def _eff_area_m2(h: gpd.GeoDataFrame) -> np.ndarray:
    return np.minimum(h["area_sqkm"].to_numpy(), _SETTLEMENT_AREA_CAP_SQKM) * 1e6


def _water_pop(h: gpd.GeoDataFrame, n: CapacityNorms) -> np.ndarray:
    rain_m = h["annual_rainfall_mm"].to_numpy() / 1000.0
    runoff_m3_yr = rain_m * _eff_area_m2(h) * n.runoff_coefficient * _CATCHMENT_YIELD
    spring_m3_yr = h["spring_discharge_lpm"].to_numpy() * 60 * 24 * 365 / 1000.0
    demand_m3_per_person_yr = n.water_lpcd / 1000.0 * 365
    return (runoff_m3_yr + spring_m3_yr) / demand_m3_per_person_yr


def _land_pop(h: gpd.GeoDataFrame, n: CapacityNorms) -> np.ndarray:
    habitable_frac = np.clip(0.30 - 0.26 * _northness(h["lat"].to_numpy()), 0.03, 0.30)
    buildable_m2 = (
        _eff_area_m2(h)
        * (1 - h["forest_pct"].to_numpy() / 100.0)
        * (1 - h["slope_gt30_pct"].to_numpy() / 100.0)
        * habitable_frac
    )
    return buildable_m2 / n.built_area_per_capita_m2


def _evac_pop(h: gpd.GeoDataFrame, n: CapacityNorms) -> np.ndarray:
    return h["lifeline_road_count"].to_numpy() * n.road_lane_capacity_pph * n.evac_warning_window_h


def _services_pop(h: gpd.GeoDataFrame, n: CapacityNorms) -> np.ndarray:
    # own facility capacity + referral headroom from the nearest town, harder when isolated
    referral = _REFERRAL_BASE * np.clip(1.2 - h["isolation_index"].to_numpy(), 0.2, 1.2)
    beds_pop = h["hospital_beds"].to_numpy() / (n.hospital_beds_per_1000 / 1000.0) + referral
    seats_pop = h["school_seats"].to_numpy() / (n.school_seats_per_1000 / 1000.0) + referral
    return np.minimum(beds_pop, seats_pop)


def _combine(parts: dict[str, np.ndarray], how: str, p: float = -3.0) -> np.ndarray:
    stack = np.clip(np.vstack(list(parts.values())), 1.0, None)
    if how == "limiting":
        return stack.min(axis=0)
    if how == "harmonic":
        return stack.shape[0] / np.sum(1.0 / stack, axis=0)
    if how == "power":
        return np.mean(stack ** p, axis=0) ** (1.0 / p)
    return stack.mean(axis=0)


def assess_capacity(habitations: gpd.GeoDataFrame, norms: CapacityNorms | None = None,
                    population_growth_pct: float = 0.0,
                    tourist_load_factor: float = 1.0) -> gpd.GeoDataFrame:
    n = norms or CAPACITY_NORMS
    hab = habitations.copy()

    parts = {
        "water": _water_pop(hab, n),
        "land": _land_pop(hab, n),
        "evacuation": _evac_pop(hab, n),
        "services": _services_pop(hab, n),
    }
    for k, v in parts.items():
        hab[f"cc_{k}_pop"] = np.round(v).astype("int64")

    sustainable = _combine(parts, n.combine, getattr(n, "combine_p", -3.0))
    effective = hab["population"].to_numpy() * (1 + population_growth_pct / 100.0) * tourist_load_factor
    ratio = effective / np.clip(sustainable, 1.0, None)

    limiting = np.array(list(parts))[np.argmin(np.vstack(list(parts.values())), axis=0)]

    def _status(r):
        if r < 0.8:
            return "surplus"
        if r < 1.0:
            return "balanced"
        if r < 1.5:
            return "stressed"
        return "overshoot"

    hab["cc_sustainable_pop"] = np.round(sustainable).astype("int64")
    hab["cc_effective_pop"] = np.round(effective).astype("int64")
    hab["cc_deficit_ratio"] = np.round(ratio, 2)
    hab["cc_limiting_factor"] = limiting
    hab["cc_status"] = [_status(r) for r in ratio]
    return hab
