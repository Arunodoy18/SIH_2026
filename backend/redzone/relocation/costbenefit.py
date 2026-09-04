"""Cost–benefit of relocating a habitation: one-time capex vs. discounted losses avoided.

Per habitation being moved:
    relocation_capex = households_moved · unit_housing_cost
                     + persons_moved   · infra_cost_per_capita
                     + land_component  (persons_moved / 150 persons-per-ha · land_cost_per_ha)
                     + persons_moved   · destination servicing_cost_per_person
                     + transport_cost  (from the optimiser)

    assets_at_risk   = current_population · per_capita_asset_value
    annual_event_prob = eal_hazard_to_annual_prob · haz_composite
    loss_fraction     = eal_max_loss_fraction · (0.3 + 0.7 · svi)
    EAL               = annual_event_prob · loss_fraction · assets_at_risk
    pv_losses_avoided = EAL · annuity_factor(discount_rate, horizon_years)

    benefit_cost_ratio = pv_losses_avoided / relocation_capex
    payback_years      = relocation_capex / EAL
"""

from __future__ import annotations

import geopandas as gpd

from redzone.config import COST_PARAMS, CostParams


def _annuity_factor(rate: float, years: int) -> float:
    return (1 - (1 + rate) ** -years) / rate if rate > 0 else float(years)


def evaluate(habitations: gpd.GeoDataFrame, assignments: list, site_scost: dict[str, float],
             cp: CostParams | None = None) -> tuple[gpd.GeoDataFrame, dict]:
    cp = cp or COST_PARAMS
    hab = habitations.copy()
    annuity = _annuity_factor(cp.discount_rate, cp.horizon_years)

    # a habitation may be split across sites -> aggregate its assignments
    moved_persons: dict = {}
    moved_transport: dict = {}
    moved_servicing: dict = {}       # persons-weighted servicing ₹
    primary_site: dict = {}
    _by_site_persons: dict = {}
    for a in assignments:
        moved_persons[a.hab_id] = moved_persons.get(a.hab_id, 0) + a.persons
        moved_transport[a.hab_id] = moved_transport.get(a.hab_id, 0.0) + a.transport_cost_inr
        moved_servicing[a.hab_id] = moved_servicing.get(a.hab_id, 0.0) + \
            a.persons * site_scost.get(a.site_id, 80_000.0)
        d = _by_site_persons.setdefault(a.hab_id, {})
        d[a.site_id] = d.get(a.site_id, 0) + a.persons
    for hid, d in _by_site_persons.items():
        primary_site[hid] = max(d, key=d.get)

    eal, capex, pv_ben, bcr, payback, dest_col = [], [], [], [], [], []
    for _, r in hab.iterrows():
        hid = r["hab_id"]
        persons = int(moved_persons.get(hid, 0))
        want = int(r.get("pop_to_move", 0) or 0)
        hh = int(round(int(r.get("households_to_move", 0) or 0) * persons / want)) if want else 0

        if persons <= 0:
            eal.append(0.0); capex.append(0.0); pv_ben.append(0.0)
            bcr.append(None); payback.append(None); dest_col.append(None)
            continue

        transport = moved_transport.get(hid, 0.0)
        avg_scost = moved_servicing.get(hid, 0.0) / max(persons, 1)
        land_component = persons / cp.persons_per_ha * cp.land_cost_per_ha_inr
        cx = (hh * cp.unit_housing_cost_inr
              + persons * cp.infra_cost_per_capita_inr
              + land_component
              + persons * avg_scost
              + transport)

        assets = float(r["population"]) * cp.per_capita_asset_value_inr
        p_event = cp.eal_hazard_to_annual_prob * float(r["haz_composite"]) ** 2
        loss_frac = cp.eal_max_loss_fraction * (0.3 + 0.7 * float(r["svi"]))
        e = p_event * loss_frac * assets
        pv = e * annuity

        eal.append(round(e, 0))
        capex.append(round(cx, 0))
        pv_ben.append(round(pv, 0))
        bcr.append(round(pv / cx, 2) if cx > 0 else None)
        payback.append(round(cx / e, 1) if e > 0 else None)
        dest_col.append(primary_site.get(hid))

    hab["persons_relocated"] = [int(moved_persons.get(h, 0)) for h in hab["hab_id"]]
    hab["eal_inr"] = eal
    hab["relocation_capex_inr"] = capex
    hab["pv_benefit_inr"] = pv_ben
    hab["benefit_cost_ratio"] = bcr
    hab["payback_years"] = payback
    hab["assigned_site_id"] = dest_col

    moved = hab[hab["persons_relocated"] > 0]
    tot_capex = float(moved["relocation_capex_inr"].sum())
    tot_eal = float(moved["eal_inr"].sum())
    tot_pv = float(moved["pv_benefit_inr"].sum())
    summary = {
        "horizon_years": cp.horizon_years,
        "discount_rate": cp.discount_rate,
        "households_moved": int(moved["households_to_move"].sum()),
        "persons_moved": int(moved["persons_relocated"].sum()),
        "total_relocation_capex_inr": round(tot_capex, 0),
        "annual_expected_loss_avoided_inr": round(tot_eal, 0),
        "pv_losses_avoided_inr": round(tot_pv, 0),
        "portfolio_benefit_cost_ratio": round(tot_pv / tot_capex, 2) if tot_capex else None,
        "portfolio_payback_years": round(tot_capex / tot_eal, 1) if tot_eal else None,
    }
    return hab, summary
