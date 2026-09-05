import math

from redzone.config import SeismicRenewalParams
from redzone.hazard.seismic_gr import (
    bpt_cdf,
    bpt_conditional_prob,
    gr_a_from_anchor,
    gr_annual_rate,
    poisson_exceedance_prob,
    seismic_outlook,
)


def test_gr_rate_matches_anchor():
    a = gr_a_from_anchor(b=0.9, m_ref=6.0, return_period_years=75.0)
    rate = gr_annual_rate(a, 0.9, 6.0)
    assert math.isclose(1.0 / rate, 75.0, rel_tol=1e-9)


def test_gr_rate_decreases_with_magnitude():
    a = gr_a_from_anchor(0.9, 6.0, 75.0)
    rates = [gr_annual_rate(a, 0.9, m) for m in (6.0, 6.5, 7.0, 7.5)]
    assert all(r1 > r2 for r1, r2 in zip(rates, rates[1:]))


def test_poisson_probability_increases_with_years():
    rate = 1.0 / 75.0
    probs = [poisson_exceedance_prob(rate, y) for y in (1, 10, 50, 200)]
    assert all(p1 < p2 for p1, p2 in zip(probs, probs[1:]))
    assert probs[-1] > 0.9  # 200 years >> 75-year recurrence: near-certain


def test_bpt_cdf_is_a_valid_cdf():
    Tr, alpha = 75.0, 0.5
    xs = [0, 1, 10, 25, 50, 75, 100, 150, 300, 1000]
    vals = [bpt_cdf(t, Tr, alpha) for t in xs]
    assert vals[0] == 0.0
    assert vals[-1] > 0.999
    assert all(v2 >= v1 - 1e-9 for v1, v2 in zip(vals, vals[1:])), "BPT CDF must be monotonic"
    assert all(0.0 <= v <= 1.0 for v in vals)


def test_elastic_rebound_suppresses_near_term_probability():
    """The actual physics being tested: shortly after a rupture (2011), renewal-model
    probability must be well below the memoryless Poisson equivalent — elastic rebound's
    signature. By the time elapsed time approaches the mean recurrence, they should converge.
    """
    Tr, alpha = 75.0, 0.5
    t_recent = 15.0  # ~ years since 2011 at time of writing
    poisson_10y = poisson_exceedance_prob(1.0 / Tr, 10)
    bpt_10y = bpt_conditional_prob(t_recent, 10, Tr, alpha)
    assert bpt_10y < poisson_10y * 0.5, "renewal probability should be clearly suppressed"

    t_near_due = 70.0  # approaching the mean recurrence interval
    poisson_10y_late = poisson_exceedance_prob(1.0 / Tr, 10)
    bpt_10y_late = bpt_conditional_prob(t_near_due, 10, Tr, alpha)
    assert bpt_10y_late > poisson_10y_late, "near the mean recurrence, renewal prob should exceed Poisson"


def test_seismic_outlook_shape_and_citation():
    out = seismic_outlook(SeismicRenewalParams(), as_of_year=2026)
    assert out["elastic_rebound"]["years_elapsed"] == 2026 - 2011
    assert len(out["gutenberg_richter"]["by_magnitude"]) == 3
    windows = out["elastic_rebound"]["windows"]
    assert len(windows) == 3
    assert windows[0]["renewal_vs_poisson"] == "suppressed"
    for w in windows:
        assert 0.0 <= w["poisson_probability"] <= 1.0
        assert 0.0 <= w["renewal_probability"] <= 1.0
