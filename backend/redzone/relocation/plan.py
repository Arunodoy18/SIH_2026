"""Assemble the phased relocation plan the DDMA dashboard consumes.

One ranked row per habitation (destinations aggregated when a habitation is split across
sites); one flow line per origin->site leg so splits are visible on the map.
"""

from __future__ import annotations

import math

import geopandas as gpd
from shapely.geometry import LineString

_PHASE_OF_TIER = {"relocate_now": 1, "plan": 2}
_PHASE_LABEL = {1: "Phase 1 — relocate now", 2: "Phase 2 — plan & stage"}


def _num(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def build_plan(habitations: gpd.GeoDataFrame, opt_result, cb_summary: dict,
               dest_sites: gpd.GeoDataFrame) -> dict:
    hab = habitations.set_index("hab_id")
    site_pt = {r["site_id"]: (r["lon"], r["lat"]) for _, r in dest_sites.iterrows()}
    site_name = dict(zip(dest_sites["site_id"], dest_sites["name"]))

    legs: dict = {}       # hab_id -> [Assignment, ...]
    for a in opt_result.assignments:
        legs.setdefault(a.hab_id, []).append(a)
    unmet_by_hab = {u["hab_id"]: u for u in opt_result.unmet}

    flows = []
    for a in opt_result.assignments:
        h = hab.loc[a.hab_id]
        ox, oy = h["lon"], h["lat"]
        dx, dy = site_pt.get(a.site_id, (ox, oy))
        flows.append({
            "type": "Feature",
            "geometry": LineString([(ox, oy), (dx, dy)]).__geo_interface__,
            "properties": {
                "hab_id": a.hab_id, "habitation": a.name,
                "site_id": a.site_id, "site": a.site_name or site_name.get(a.site_id, a.site_id),
                "persons": a.persons, "households": a.households, "distance_km": a.distance_km,
                "phase": _PHASE_OF_TIER.get(h["priority_tier"], 2),
                "priority_tier": h["priority_tier"],
            },
        })

    rows = []
    for hid, h in hab.iterrows():
        tier = h["priority_tier"]
        want = int(h.get("pop_to_move", 0) or 0)
        if want <= 0:
            continue
        mine = legs.get(hid, [])
        placed = sum(a.persons for a in mine)
        unmet = unmet_by_hab.get(hid, {}).get("persons", max(want - placed, 0))
        dests = sorted(mine, key=lambda a: -a.persons)
        dest_str = " + ".join(
            f"{a.site_name or site_name.get(a.site_id, a.site_id)} ({a.persons:,})" for a in dests
        ) or None
        rows.append({
            "hab_id": hid, "habitation": h["name"], "block": h.get("block"),
            "priority_tier": tier, "phase": _PHASE_OF_TIER.get(tier, 2),
            "priority_score": _num(h["priority_score"]),
            "haz_tier": h["haz_tier"], "haz_composite": _num(h["haz_composite"]),
            "svi": _num(h["svi"]), "cc_deficit_ratio": _num(h["cc_deficit_ratio"]),
            "cc_limiting_factor": h.get("cc_limiting_factor"),
            "persons_to_move": want, "persons_placed": placed, "persons_unmet": int(unmet),
            "households": int(h.get("households_to_move", 0) or 0),
            "destination": dest_str, "split": len(dests) > 1,
            "nearest_distance_km": min((a.distance_km for a in dests), default=None),
            "relocation_capex_inr": _num(h["relocation_capex_inr"]),
            "eal_inr": _num(h["eal_inr"]),
            "pv_benefit_inr": _num(h["pv_benefit_inr"]),
            "benefit_cost_ratio": _num(h["benefit_cost_ratio"]),
            "payback_years": _num(h["payback_years"]),
        })

    rows.sort(key=lambda r: (r["phase"], -(r["benefit_cost_ratio"] or 0), -r["priority_score"]))

    phases = []
    for ph in (1, 2):
        pr = [r for r in rows if r["phase"] == ph]
        if not pr:
            continue
        phases.append({
            "phase": ph, "label": _PHASE_LABEL[ph], "habitations": len(pr),
            "persons_to_move": sum(r["persons_to_move"] for r in pr),
            "persons_unmet": sum(r["persons_unmet"] for r in pr),
            "households": sum(r["households"] for r in pr),
            "capex_inr": sum(r["relocation_capex_inr"] or 0 for r in pr),
            "pv_benefit_inr": sum(r["pv_benefit_inr"] or 0 for r in pr),
        })

    return {
        "phases": phases,
        "ranked": rows,
        "assignments": [a.__dict__ for a in opt_result.assignments],
        "unmet": opt_result.unmet,
        "site_utilisation": opt_result.site_utilisation,
        "solver": opt_result.solver,
        "solver_status": opt_result.status,
        "split_habitations": opt_result.split_habitations,
        "totals": {
            "persons_moved": opt_result.persons_moved,
            "persons_unmet": opt_result.persons_unmet,
            "transport_cost_inr": opt_result.total_transport_cost_inr,
            **cb_summary,
        },
        "flows": {"type": "FeatureCollection", "features": flows},
    }
