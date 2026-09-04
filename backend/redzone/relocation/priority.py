"""Composite relocation-priority score and action tier per habitation.

priority_raw = hazard^a  x  svi^b  x  (0.3 + deficit_factor)^c
    hazard         = haz_composite                                   (0..1)
    svi            = social vulnerability index                      (0..1)
    deficit_factor = ramp of carrying-capacity deficit ratio 0.7->2.5 mapped to 0..1

priority_score = min-max(priority_raw) over the district  (rank within this scenario run);
priority_index = priority_raw itself                      (absolute, comparable across runs)

Action tier from the score, then a HAZARD GATE: you do not "relocate now" out of a place
that is not hazardous, however overcrowded or vulnerable it is —
    relocate_now  requires haz_tier == red
    plan          requires haz_tier in {red, orange}
A gated-down habitation still surfaces (as monitor) with its overcrowding/vulnerability flag.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np

from redzone.config import PriorityParams

_TIER_ORDER = {"safe": 0, "monitor": 1, "plan": 2, "relocate_now": 3}
_ORDER_TIER = {v: k for k, v in _TIER_ORDER.items()}


def score_priority(habitations: gpd.GeoDataFrame, p: PriorityParams) -> gpd.GeoDataFrame:
    hab = habitations.copy()
    hazard = hab["haz_composite"].to_numpy(dtype=float).clip(1e-4, 1)
    svi = hab["svi"].to_numpy(dtype=float).clip(1e-4, 1)
    ratio = hab["cc_deficit_ratio"].to_numpy(dtype=float)
    deficit_factor = np.clip((ratio - 0.7) / (2.5 - 0.7), 0.0, 1.0)

    raw = (hazard ** p.hazard_exp) * (svi ** p.svi_exp) * ((0.3 + deficit_factor) ** p.deficit_exp)
    lo, hi = float(raw.min()), float(raw.max())
    score = (raw - lo) / (hi - lo) if hi - lo > 1e-9 else np.zeros_like(raw)
    hab["priority_index"] = np.round(raw, 4)
    hab["priority_score"] = np.round(score, 3)
    hab["priority_deficit_factor"] = np.round(deficit_factor, 3)

    b = p.tier_breaks

    def _ungated(s: float) -> str:
        if s >= b["relocate_now"]:
            return "relocate_now"
        if s >= b["plan"]:
            return "plan"
        if s >= b["monitor"]:
            return "monitor"
        return "safe"

    _cap_by_haz = {"red": "relocate_now", "orange": "plan", "yellow": "monitor", "green": "monitor"}
    tiers = []
    for s, ht in zip(score, hab["haz_tier"]):
        t = _ungated(s)
        cap = _cap_by_haz.get(ht, "monitor")
        if _TIER_ORDER[t] > _TIER_ORDER[cap]:
            t = cap
        tiers.append(t)
    hab["priority_tier"] = tiers
    hab["pop_to_move"] = [
        int(round(pop * p.move_fraction.get(t, 0.0)))
        for pop, t in zip(hab["population"].to_numpy(), hab["priority_tier"])
    ]
    hab["households_to_move"] = [
        int(round(hh * (m / pop))) if pop else 0
        for hh, pop, m in zip(hab["households"].to_numpy(), hab["population"].to_numpy(),
                              hab["pop_to_move"].to_numpy())
    ]
    return hab
