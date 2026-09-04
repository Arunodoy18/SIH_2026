"""End-to-end + invariant checks. Assumes the seed has been generated."""

import math

import pytest

from redzone.config import Settings
from redzone.data import store
from redzone.pipeline import run_pipeline


@pytest.fixture(scope="module")
def result():
    if not store.interim_ready():
        from redzone.seed.generate_sikkim import main as seed
        seed()
    return run_pipeline(Settings(), persist=False)


def test_every_habitation_scored(result):
    h = result.habitations
    for col in ("haz_composite", "haz_tier", "svi", "cc_deficit_ratio",
                "priority_score", "priority_tier"):
        assert col in h.columns
        assert h[col].notna().all(), col


def test_scores_in_range(result):
    h = result.habitations
    assert h["haz_composite"].between(0, 1).all()
    assert h["svi"].between(0, 1).all()
    assert h["priority_score"].between(0, 1).all()
    assert (h["cc_deficit_ratio"] > 0).all()


def test_hazard_weights_normalised(result):
    w = result.summary["hazard"]["weights"]
    assert math.isclose(sum(w.values()), 1.0, abs_tol=1e-2)
    assert w["glof"] > w["flood"]  # calibrated: 2023 pushes GLOF above flash flood


def test_calibration_beats_random(result):
    m = result.summary["hazard"]["calibration"]
    assert m["ranking_auc"] > 0.7          # event sites score well above random cells
    assert m["composite_spearman"] > 0.3


def test_relocation_conserves_people(result):
    plan = result.plan
    for row in plan["ranked"]:
        assert row["persons_placed"] + row["persons_unmet"] == row["persons_to_move"]


def test_no_site_over_capacity(result):
    for s in result.plan["site_utilisation"]:
        assert s["used"] <= s["capacity"] + 1e-6


def test_hazard_gate_on_priority(result):
    """A green/yellow-hazard habitation is never 'relocate_now' or 'plan'."""
    h = result.habitations
    gated = h[h["haz_tier"].isin(["green", "yellow"])]
    assert set(gated["priority_tier"]) <= {"monitor", "safe"}


def test_relocate_now_all_red(result):
    h = result.habitations
    assert (h[h["priority_tier"] == "relocate_now"]["haz_tier"] == "red").all()


def test_costbenefit_present_for_moved(result):
    h = result.habitations
    moved = h[h["persons_relocated"] > 0]
    assert (moved["relocation_capex_inr"] > 0).all()
    assert (moved["eal_inr"] > 0).all()
