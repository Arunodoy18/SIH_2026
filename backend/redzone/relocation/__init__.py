"""Deliverable 3 — immediate relocation needs for vulnerable habitations.

build_relocation(scored_habitations, settings) ->
    habitations  (+ priority_score, priority_tier, pop_to_move, eal_inr, relocation_capex_inr,
                  benefit_cost_ratio, payback_years, assigned_site_id)
    plan         phased plan dict (phases, ranked table, flows GeoJSON, site utilisation,
                 unmet demand, cost-benefit totals)
"""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd

from redzone.config import Settings
from redzone.data import store
from redzone.relocation import costbenefit
from redzone.relocation.optimizer import solve_assignment
from redzone.relocation.plan import build_plan
from redzone.relocation.priority import score_priority

_ALLOWED_DEST_TIERS = {"green", "yellow"}


@dataclass
class RelocationResult:
    habitations: gpd.GeoDataFrame
    plan: dict


def build_relocation(scored_habitations: gpd.GeoDataFrame,
                     settings: Settings | None = None) -> RelocationResult:
    settings = settings or Settings()

    hab = score_priority(scored_habitations, settings.priority)

    dests = store.load_interim("destination_sites")
    dests = dests[dests["hazard_tier"].isin(_ALLOWED_DEST_TIERS)].reset_index(drop=True)
    site_scost = dict(zip(dests["site_id"], dests["servicing_cost_per_person"]))

    opt = solve_assignment(hab, dests, settings.optimizer)
    hab, cb_summary = costbenefit.evaluate(hab, opt.assignments, site_scost, settings.cost)
    plan = build_plan(hab, opt, cb_summary, dests)

    return RelocationResult(habitations=hab, plan=plan)


__all__ = ["RelocationResult", "build_relocation"]
