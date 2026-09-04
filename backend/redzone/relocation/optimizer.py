"""Capacitated assignment of vulnerable habitations to green destination sites.

Min-cost flow with a community-split penalty (solved as a MILP with scipy.optimize.milp /
HiGHS — no external solver binary):

    minimise  Σ_ij  x_ij · cost_pp_ij                     (person-km + servicing proxy)
            + Σ_ij  z_ij · split_penalty                   (₹-equiv per extra site used)
            + Σ_i   u_i  · UNMET_PENALTY                   (persons with nowhere safe to go)

    s.t.  Σ_j x_ij + u_i = demand_i          every at-risk habitation fully accounted for
          Σ_i x_ij       ≤ capacity_j        destination spare capacity
          x_ij ≤ demand_i · z_ij             a site is "opened" for a habitation before use
          x_ij only where distance_ij ≤ max_reloc_distance_km
          x_ij ≥ 0 ,  z_ij ∈ {0,1} ,  u_i ≥ 0

`unmet` demand is a headline finding, not an error: it means Phase 1 needs new safe land
identified. Greedy nearest-feasible assignment is the fallback if HiGHS is unavailable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import geopandas as gpd
import numpy as np

from redzone.config import OptimizerParams

TRANSPORT_INR_PER_PERSON_KM = 1500.0   # one-time move logistics, reporting only
_UNMET_PENALTY = 1e6
_SPLIT_PENALTY_SCALE = 1000.0          # multiplies OptimizerParams.w_community_split


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


@dataclass
class Assignment:
    hab_id: str
    name: str
    site_id: str
    site_name: str
    persons: int
    households: int
    distance_km: float
    transport_cost_inr: float


@dataclass
class OptimizerResult:
    assignments: list = field(default_factory=list)
    unmet: list = field(default_factory=list)
    site_utilisation: list = field(default_factory=list)
    solver: str = "none"
    status: str = "empty"
    total_transport_cost_inr: float = 0.0
    persons_moved: int = 0
    persons_unmet: int = 0
    split_habitations: int = 0


def solve_assignment(origins: gpd.GeoDataFrame, dests: gpd.GeoDataFrame,
                     p: OptimizerParams | None = None) -> OptimizerResult:
    p = p or OptimizerParams()
    O = origins[origins["pop_to_move"] > 0].copy()
    if len(O) == 0 or len(dests) == 0:
        return OptimizerResult(status="nothing_to_place")

    o_ids = O["hab_id"].tolist()
    demand = {i: int(v) for i, v in zip(o_ids, O["pop_to_move"])}
    hh = {i: int(v) for i, v in zip(o_ids, O.get("households_to_move", O["pop_to_move"]))}
    o_name = dict(zip(o_ids, O["name"]))
    o_lat = dict(zip(o_ids, O["lat"])); o_lon = dict(zip(o_ids, O["lon"]))

    d_ids = dests["site_id"].tolist()
    cap = {j: int(v) for j, v in zip(d_ids, dests["spare_capacity"])}
    d_name = dict(zip(d_ids, dests["name"]))
    d_lat = dict(zip(d_ids, dests["lat"])); d_lon = dict(zip(d_ids, dests["lon"]))
    d_scost = dict(zip(d_ids, dests["servicing_cost_per_person"]))

    dist = {(i, j): _haversine_km(o_lat[i], o_lon[i], d_lat[j], d_lon[j])
            for i in o_ids for j in d_ids}
    pairs = [(i, j) for (i, j), dkm in dist.items() if dkm <= p.max_reloc_distance_km]
    cpp = {(i, j): p.w_distance * dist[(i, j)] + p.w_servicing * d_scost[j] / 1e5 for (i, j) in pairs}

    res = (_solve_milp(o_ids, d_ids, pairs, demand, cap, cpp, dist, p)
           or _solve_greedy(o_ids, d_ids, demand, cap, dist, cpp, p))

    used = {j: 0 for j in d_ids}
    for a in res.assignments:
        a.name = o_name[a.hab_id]
        a.site_name = d_name[a.site_id]
        a.households = int(round(hh[a.hab_id] * a.persons / max(demand[a.hab_id], 1)))
        used[a.site_id] += a.persons
    for u in res.unmet:
        u["name"] = o_name[u["hab_id"]]

    res.site_utilisation = [
        {"site_id": j, "name": d_name[j], "used": used[j], "capacity": cap[j],
         "pct": round(100 * used[j] / cap[j], 1) if cap[j] else 0.0}
        for j in d_ids
    ]
    res.persons_moved = sum(a.persons for a in res.assignments)
    res.persons_unmet = sum(u["persons"] for u in res.unmet)
    res.total_transport_cost_inr = round(sum(a.transport_cost_inr for a in res.assignments), 0)
    res.split_habitations = sum(
        1 for i in o_ids if sum(1 for a in res.assignments if a.hab_id == i) > 1
    )
    return res


def _solve_milp(o_ids, d_ids, pairs, demand, cap, cpp, dist, p: OptimizerParams):
    try:
        from scipy.optimize import Bounds, LinearConstraint, milp
    except ImportError:
        return None

    npair = len(pairs)
    no = len(o_ids)
    nd = len(d_ids)
    xi = {pr: k for k, pr in enumerate(pairs)}          # x_ij  -> col k
    zi = {pr: npair + k for k, pr in enumerate(pairs)}  # z_ij  -> col npair+k
    ui = {i: 2 * npair + k for k, i in enumerate(o_ids)}  # u_i  -> col 2*npair+k
    ncol = 2 * npair + no

    split_pen = max(p.w_community_split, 0.0) * _SPLIT_PENALTY_SCALE
    c = np.zeros(ncol)
    for pr, k in xi.items():
        c[k] = cpp[pr]
        c[zi[pr]] = split_pen
    for i in o_ids:
        c[ui[i]] = _UNMET_PENALTY

    # equality: Σ_j x_ij + u_i = demand_i
    A_dem = np.zeros((no, ncol))
    for n, i in enumerate(o_ids):
        for j in d_ids:
            if (i, j) in xi:
                A_dem[n, xi[(i, j)]] = 1.0
        A_dem[n, ui[i]] = 1.0
    dem_vec = np.array([demand[i] for i in o_ids], float)

    # capacity: Σ_i x_ij ≤ cap_j
    A_cap = np.zeros((nd, ncol))
    for m, j in enumerate(d_ids):
        for i in o_ids:
            if (i, j) in xi:
                A_cap[m, xi[(i, j)]] = 1.0
    cap_vec = np.array([cap[j] for j in d_ids], float)

    # linking: x_ij - demand_i · z_ij ≤ 0
    A_lnk = np.zeros((npair, ncol))
    for pr, k in xi.items():
        A_lnk[k, k] = 1.0
        A_lnk[k, zi[pr]] = -demand[pr[0]]

    cons = [
        LinearConstraint(A_dem, dem_vec, dem_vec),
        LinearConstraint(A_cap, -np.inf, cap_vec),
        LinearConstraint(A_lnk, -np.inf, 0.0),
    ]
    integrality = np.zeros(ncol)
    for pr in pairs:
        integrality[zi[pr]] = 1
    lb = np.zeros(ncol)
    ub = np.full(ncol, np.inf)
    for pr, k in xi.items():
        ub[k] = demand[pr[0]]
    for pr in pairs:
        ub[zi[pr]] = 1
    for i in o_ids:
        ub[ui[i]] = demand[i]

    r = milp(c, integrality=integrality, bounds=Bounds(lb, ub), constraints=cons,
             options={"time_limit": p.solver_time_limit_s})
    if not r.success or r.x is None:
        return None

    x = r.x
    out = OptimizerResult(solver="scipy-milp-highs", status="optimal")
    for (i, j), k in xi.items():
        persons = int(round(x[k]))
        if persons > 0:
            out.assignments.append(Assignment(
                hab_id=i, name="", site_id=j, site_name="", persons=persons, households=0,
                distance_km=round(dist[(i, j)], 2),
                transport_cost_inr=round(persons * dist[(i, j)] * TRANSPORT_INR_PER_PERSON_KM, 0),
            ))
    for i in o_ids:
        rem = int(round(x[ui[i]]))
        if rem > 0:
            out.unmet.append({"hab_id": i, "name": "", "persons": rem,
                              "reason": "no safe capacity within range"})
    return out if (out.assignments or out.unmet) else None


def _solve_greedy(o_ids, d_ids, demand, cap, dist, cpp, p: OptimizerParams):
    out = OptimizerResult(solver="greedy", status="heuristic")
    remaining = dict(cap)
    for i in sorted(o_ids, key=lambda i: -demand[i]):
        need = demand[i]
        for j in sorted(d_ids, key=lambda j: cpp.get((i, j), 9e9)):
            if need <= 0:
                break
            if dist[(i, j)] > p.max_reloc_distance_km or remaining[j] <= 0:
                continue
            take = min(need, remaining[j])
            remaining[j] -= take
            need -= take
            out.assignments.append(Assignment(
                hab_id=i, name="", site_id=j, site_name="", persons=take, households=0,
                distance_km=round(dist[(i, j)], 2),
                transport_cost_inr=round(take * dist[(i, j)] * TRANSPORT_INR_PER_PERSON_KM, 0),
            ))
        if need > 0:
            out.unmet.append({"hab_id": i, "name": "", "persons": need,
                              "reason": "no safe capacity within range"})
    return out
