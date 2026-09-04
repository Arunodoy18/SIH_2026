"""Calibrate hazard weights against historical disaster-loss records.

This is the USP of Deliverable 1: the composite is *fitted* to where losses actually
occurred, not hand-assigned. AHP weights (config.AHP_WEIGHTS) are only a stabilising prior
for the small-sample regime typical of a single district.

Method: non-negative least squares of standardised loss ~ per-hazard susceptibility at each
event location, blended with the AHP prior. Reported diagnostics: in-sample R^2,
leave-one-out R^2, Spearman rank correlation, and a ranking AUC (do event sites score higher
on the composite than random non-event sites?).
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from scipy.optimize import nnls
from scipy.stats import spearmanr

from redzone.config import AHP_WEIGHTS, HAZARDS
from redzone.hazard import grid as G

_PRIOR_BLEND = 0.45   # shrinkage toward the AHP prior (few events -> corner NNLS solutions)
_WEIGHT_FLOOR = 0.6   # every hazard keeps >= this fraction of its prior weight
_WEIGHT_CAP = 0.60    # no single hazard's *fitted* contribution exceeds this before blending


def _loss_target(losses: gpd.GeoDataFrame) -> np.ndarray:
    raw = np.log1p(losses["houses_damaged"].to_numpy(float)
                   + 20.0 * losses["deaths"].to_numpy(float))
    return (raw - raw.mean()) / (raw.std() + 1e-9)


def calibrate_weights(stack: dict[str, np.ndarray], losses: gpd.GeoDataFrame,
                      composite_of=None) -> dict:
    rng = np.random.default_rng(7)  # per-call determinism (independent of call order/count)
    lons = losses.geometry.x.to_numpy()
    lats = losses.geometry.y.to_numpy()
    X = np.column_stack([G.sample_points(stack[h], lons, lats) for h in HAZARDS])
    y = _loss_target(losses)

    w_raw, _ = nnls(X, y)
    if w_raw.sum() < 1e-9:
        w_raw = np.array([AHP_WEIGHTS[h] for h in HAZARDS], dtype=float)
    w_fit = w_raw / w_raw.sum()
    w_prior = np.array([AHP_WEIGHTS[h] for h in HAZARDS], dtype=float)

    # 1) cap the fitted vector so NNLS corner solutions can't dominate  2) blend with prior
    # 3) floor every hazard at a fraction of its prior  4) normalise once.
    w_capped = np.minimum(w_fit, _WEIGHT_CAP)
    w = (1 - _PRIOR_BLEND) * w_capped + _PRIOR_BLEND * w_prior
    w = np.maximum(w, _WEIGHT_FLOOR * w_prior)
    w = w / w.sum()

    # ---- validation of the FINAL composite against the loss record -----------------
    # (the headline numbers — "do our red zones sit where losses actually happened?")
    comp = composite_of(w) if composite_of is not None else _weighted(stack, w)
    pos = G.sample_points(comp, lons, lats)
    ss_tot = float(np.sum((y - y.mean()) ** 2)) + 1e-9

    z = (pos - pos.mean()) / (pos.std() + 1e-9)
    beta = float(np.dot(z, y) / np.dot(z, z))              # OLS slope, standardised
    comp_r2 = 1.0 - float(np.sum((y - beta * z) ** 2)) / ss_tot
    comp_rho = float(spearmanr(pos, y).statistic)

    ny, nx = comp.shape
    neg = comp[rng.integers(0, ny, 500), rng.integers(0, nx, 500)]
    auc = float(np.mean(pos[:, None] > neg[None, :]))

    # ---- 4-way NNLS decomposition diagnostics (secondary) --------------------------
    pred = X @ w_raw
    decomp_r2 = 1.0 - float(np.sum((y - pred) ** 2)) / ss_tot
    loo = np.empty_like(y)
    for i in range(len(y)):
        m = np.ones(len(y), bool)
        m[i] = False
        wi, _ = nnls(X[m], y[m])
        loo[i] = X[i] @ wi
    loo_r2 = 1.0 - float(np.sum((y - loo) ** 2)) / ss_tot

    return {
        "method": "NNLS on per-hazard susceptibility vs standardised loss, capped + AHP-prior blend",
        "prior_blend": _PRIOR_BLEND,
        "weights": {h: round(float(wi), 3) for h, wi in zip(HAZARDS, w)},
        "weights_ahp_prior": {h: round(float(wi), 3) for h, wi in zip(HAZARDS, w_prior)},
        "weights_fitted": {h: round(float(wi), 3) for h, wi in zip(HAZARDS, w_fit)},
        "metrics": {
            "n_events": len(y),
            "composite_r2": round(comp_r2, 3),
            "composite_spearman": round(comp_rho, 3),
            "ranking_auc": round(auc, 3),
            "decomposition_r2": round(decomp_r2, 3),
            "decomposition_loo_r2": round(loo_r2, 3),
        },
    }


def _weighted(stack: dict[str, np.ndarray], w) -> np.ndarray:
    w = np.asarray(w, dtype="float32")
    out = sum(w[i] * stack[h] for i, h in enumerate(HAZARDS))
    return (out / w.sum()).astype("float32")
