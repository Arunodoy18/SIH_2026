"""Turn the structured plan into DDMA report prose.

Two modes, same call:
  "ai"        ANTHROPIC_API_KEY is set -> drafted by an LLM from the structured facts below.
  "template"  no key, or the call fails for any reason -> a deterministic, still-readable
              paragraph assembled from the same facts. The MVP is complete either way;
              the AI path is strictly an upgrade, never a hard dependency.

The model is never handed anything to embellish beyond the numbers already computed by the
pipeline — it drafts prose *from* the facts dict, it doesn't invent figures.
"""

from __future__ import annotations

import os

_DEFAULT_MODEL = os.environ.get("NIRNAY_NARRATIVE_MODEL", "claude-sonnet-5")
_MAX_TOKENS = 900

_SYSTEM_PROMPT = """You are drafting the narrative section of a pre-disaster relocation \
plan for a District Disaster Management Authority (DDMA) in India. You are given a JSON \
object of already-computed facts — hazard tiers, calibration diagnostics, carrying-capacity \
status, and a phased relocation plan with cost–benefit figures. Write four short paragraphs \
of plain, professional planning-document prose (no headings, no bullet points, no markdown):

1. Situation overview — district, population, how many habitations sit in each hazard tier.
2. Method — one sentence on how the hazard composite was built and calibrated, citing the
   given R²/AUC and, if present, the landslide model's AUC and the seismic renewal outlook.
3. The relocation plan — Phase 1 and Phase 2, naming the top few habitations by priority,
   their destinations, and why (composite of hazard, vulnerability, capacity deficit).
4. The economic case — total capex, portfolio benefit–cost ratio, payback period, and a one
   sentence recommendation to the DDMA.

Use ONLY the numbers given. Never invent a figure, a place name, or a date that is not in
the JSON. Keep the whole thing under 320 words. Write it as it would appear in an actual
submitted report, not as a description of the data."""


def _facts(summary: dict, plan: dict) -> dict:
    ranked = plan.get("ranked", [])
    top = [
        {
            "habitation": r["habitation"], "tier": r["priority_tier"],
            "destination": r.get("destination"), "persons": r["persons_to_move"],
            "benefit_cost_ratio": r.get("benefit_cost_ratio"),
            "payback_years": r.get("payback_years"),
        }
        for r in ranked[:6]
    ]
    seismic = summary.get("seismic_outlook", {})
    seismic_headline = None
    windows = seismic.get("elastic_rebound", {}).get("windows", [])
    if windows:
        w = windows[0]
        seismic_headline = (
            f"{w['window_years']}-year window: {w['renewal_probability']*100:.1f}% "
            f"(renewal model) vs {w['poisson_probability']*100:.1f}% (naive memoryless) "
            f"— {w['renewal_vs_poisson']}"
        )
    return {
        "aoi": summary.get("aoi"),
        "population": summary["counts"]["population"],
        "habitations": summary["counts"]["habitations"],
        "hazard_tiers": summary["counts"]["hazard_tiers"],
        "priority_tiers": summary["counts"]["priority_tiers"],
        "hazard_weights": summary["hazard"]["weights"],
        "hazard_calibration": summary["hazard"]["calibration"],
        "landslide_method": summary["hazard"].get("landslide_method"),
        "landslide_model_auc": (summary["hazard"].get("landslide_model") or {}).get("roc_auc_test"),
        "seismic_outlook_headline": seismic_headline,
        "relocation_phases": summary["relocation"]["phases"],
        "relocation_totals": {
            "persons_moved": summary["relocation"]["persons_moved"],
            "persons_unmet": summary["relocation"]["persons_unmet"],
            "capex_inr": summary["relocation"]["total_relocation_capex_inr"],
            "portfolio_bcr": summary["relocation"]["portfolio_benefit_cost_ratio"],
            "payback_years": summary["relocation"]["portfolio_payback_years"],
        },
        "top_habitations": top,
    }


def _template_narrative(f: dict) -> str:
    ht = f["hazard_tiers"]
    pt = f["priority_tiers"]
    top = f["top_habitations"]
    lead = top[0] if top else None
    phases = f["relocation_phases"]

    p1 = (
        f"{f['aoi']} comprises {f['habitations']} assessed habitations with a combined "
        f"population of {f['population']:,}. Of these, {ht.get('red', 0)} fall in the red "
        f"hazard tier and {ht.get('orange', 0)} in orange; {pt.get('relocate_now', 0)} "
        f"habitations are flagged for immediate relocation and {pt.get('plan', 0)} for staged "
        f"planning."
    )

    calib = f["hazard_calibration"]
    method_note = ""
    if f.get("landslide_method") == "ml" and f.get("landslide_model_auc"):
        method_note = (
            f" Landslide susceptibility is scored by a trained classifier "
            f"(held-out ROC-AUC {f['landslide_model_auc']:.2f})."
        )
    seismic_note = f" {f['seismic_outlook_headline']}." if f.get("seismic_outlook_headline") else ""
    p2 = (
        f"The composite hazard surface combines landslide, GLOF, seismic and flood layers "
        f"with weights calibrated against the district's historical loss record "
        f"(composite R² {calib.get('composite_r2')}, ranking AUC {calib.get('ranking_auc')})."
        f"{method_note} Seismic exposure additionally reflects a Gutenberg-Richter and "
        f"elastic-rebound renewal outlook rather than a static zone assumption.{seismic_note}"
    )

    p3_bits = []
    for ph in phases:
        p3_bits.append(
            f"{ph['label']} covers {ph['habitations']} habitations and "
            f"{ph['persons_to_move']:,} people (₹{ph['capex_inr']/1e7:.1f} cr)"
        )
    lead_bit = ""
    if lead:
        lead_bit = (
            f" {lead['habitation']} is the top priority, recommended for relocation to "
            f"{lead['destination']}."
        )
    p3 = "; ".join(p3_bits) + "." + lead_bit

    tot = f["relocation_totals"]
    p4 = (
        f"Total relocation capital cost is estimated at ₹{tot['capex_inr']/1e7:.1f} crore "
        f"against a portfolio benefit-cost ratio of {tot['portfolio_bcr']} and a payback "
        f"period of {tot['payback_years']} years"
        + (f", with {tot['persons_unmet']:,} people not yet matched to safe capacity"
           if tot["persons_unmet"] else "")
        + ". The DDMA is advised to prioritise Phase 1 for immediate funding and to identify "
          "additional safe destination capacity ahead of Phase 2."
    )

    return f"{p1}\n\n{p2}\n\n{p3}\n\n{p4}"


def _ai_narrative(f: dict) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import json

        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=_DEFAULT_MODEL,
            max_tokens=_MAX_TOKENS,
            temperature=0.3,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(f, indent=2)}],
        )
        text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
        return text.strip() or None
    except Exception:  # noqa: BLE001 - deliberately broad: any failure here must fall back, never 500
        return None


def generate_narrative(summary: dict, plan: dict) -> dict:
    facts = _facts(summary, plan)
    text = _ai_narrative(facts)
    if text:
        return {"mode": "ai", "model": _DEFAULT_MODEL, "text": text}
    return {"mode": "template", "model": None, "text": _template_narrative(facts)}
