"""Seismic temporal outlook: Gutenberg–Richter frequency + elastic-rebound renewal probability.

The spatial seismic field (`fields.seismic_field`) says WHERE shaking is worse (BIS zone,
fault proximity, valley-fill amplification). It has no time dimension — a static zone map
can't say whether a damaging earthquake is due next year or in fifty. This module adds that:

  Gutenberg–Richter law           log10 N(>=M) = a - b*M
      the long-run ANNUAL RATE of earthquakes at or above a magnitude, region-wide.
      Converted to a Poisson exceedance probability P = 1 - exp(-rate * years).

  Elastic rebound (Reid, 1910) -> Brownian Passage Time renewal model
      strain resets near zero right after a rupture and rebuilds toward the next one, so
      recurrence is NOT memoryless like Poisson. BPT models that with a mean recurrence
      interval and an elapsed-time-dependent conditional probability. Closed-form CDF from
      Matthews, Ellsworth & Reasenberg (2002), "A Brownian Model for Recurrent Earthquakes",
      BSSA 92(6) — the standard USGS/WGCEP renewal-model reference.

Both are anchored to the SAME mean recurrence interval (the G-R return period at the
reference magnitude), so they tell one coherent story: G-R sets the long-run average rate;
BPT reshapes *when* within that average the next event is likely, given the real 2011 M6.9
Sikkim earthquake reset the clock. District-level only — decomposing this to individual
fault segments needs seismotectonic data at a finer resolution than is publicly available
for this area; treat it as a planning input alongside the spatial map, not a per-habitation
forecast.
"""

from __future__ import annotations

import math

from redzone.config import SeismicRenewalParams

_SQRT2 = math.sqrt(2.0)


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via erf — avoids a scipy dependency for one function."""
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def gr_a_from_anchor(b: float, m_ref: float, return_period_years: float) -> float:
    """Solve Gutenberg–Richter's `a` so the model reproduces a known return period at m_ref."""
    rate_at_ref = 1.0 / return_period_years
    return math.log10(rate_at_ref) + b * m_ref


def gr_annual_rate(a: float, b: float, magnitude: float) -> float:
    """Annual rate (events/yr) of earthquakes >= `magnitude`, per Gutenberg–Richter."""
    return 10.0 ** (a - b * magnitude)


def poisson_exceedance_prob(annual_rate: float, years: float) -> float:
    """Memoryless probability of >=1 event in `years`, given a constant annual rate."""
    return 1.0 - math.exp(-annual_rate * years)


def bpt_cdf(t: float, mean_recurrence: float, aperiodicity: float) -> float:
    """Brownian Passage Time CDF: P(next rupture has occurred by elapsed time t).

    Closed form (Matthews, Ellsworth & Reasenberg 2002, eq. 12-13). `t` and `mean_recurrence`
    in the same units (years here); `aperiodicity` is the distribution's coefficient of
    variation (typical range 0.3-0.7).
    """
    if t <= 0:
        return 0.0
    tp = t / mean_recurrence  # normalised time
    alpha = aperiodicity
    term1 = _norm_cdf((tp - 1.0) / (alpha * math.sqrt(tp)))
    term2 = math.exp(2.0 / alpha**2) * _norm_cdf(-(tp + 1.0) / (alpha * math.sqrt(tp)))
    return min(1.0, term1 + term2)


def bpt_conditional_prob(t_elapsed: float, window_years: float,
                         mean_recurrence: float, aperiodicity: float) -> float:
    """P(rupture within [t, t+window] | no rupture yet at t) — the renewal-model analogue
    of the Poisson probability, but time-dependent: this is what elastic rebound changes.
    """
    f_t = bpt_cdf(t_elapsed, mean_recurrence, aperiodicity)
    f_t_plus = bpt_cdf(t_elapsed + window_years, mean_recurrence, aperiodicity)
    survival = max(1.0 - f_t, 1e-9)
    return max(0.0, min(1.0, (f_t_plus - f_t) / survival))


def seismic_outlook(p: SeismicRenewalParams, as_of_year: int) -> dict:
    """Full district-level seismic temporal outlook: G-R return periods + rates for the
    reference magnitudes, and a BPT-vs-Poisson comparison over each outlook window — the
    number that shows elastic rebound actually doing something (currently *suppressed*
    relative to the memoryless assumption, because 2011 reset the clock).
    """
    a = gr_a_from_anchor(p.gr_b, p.gr_m_ref, p.gr_return_period_years_at_m_ref)
    t_elapsed = max(0.0, as_of_year - p.last_major_event_year)
    mean_recurrence = p.gr_return_period_years_at_m_ref  # anchor magnitude ties the two models

    by_magnitude = []
    for m in p.reference_magnitudes:
        rate = gr_annual_rate(a, p.gr_b, m)
        by_magnitude.append({
            "magnitude": m,
            "annual_rate": round(rate, 5),
            "return_period_years": round(1.0 / rate, 1) if rate > 0 else None,
        })

    windows = []
    for w in p.outlook_windows_years:
        poisson_p = poisson_exceedance_prob(1.0 / mean_recurrence, w)
        bpt_p = bpt_conditional_prob(t_elapsed, w, mean_recurrence, p.bpt_aperiodicity)
        windows.append({
            "window_years": w,
            "poisson_probability": round(poisson_p, 3),
            "renewal_probability": round(bpt_p, 3),
            "renewal_vs_poisson": "suppressed" if bpt_p < poisson_p * 0.97 else
                                  ("elevated" if bpt_p > poisson_p * 1.03 else "comparable"),
        })

    return {
        "method": "Gutenberg-Richter frequency + Brownian Passage Time renewal "
                  "(elastic rebound), anchored to the 2011 M6.9 Sikkim earthquake",
        "gutenberg_richter": {"a": round(a, 3), "b": p.gr_b, "by_magnitude": by_magnitude},
        "elastic_rebound": {
            "last_major_event": p.last_major_event_year,
            "years_elapsed": t_elapsed,
            "mean_recurrence_years": mean_recurrence,
            "aperiodicity": p.bpt_aperiodicity,
            "windows": windows,
        },
        "note": "District-level and literature-anchored, not fit to a project-specific "
                "seismicity catalog or decomposed to individual fault segments — a planning "
                "input alongside the spatial hazard map, not a per-habitation forecast.",
    }
