"""Request models for the API. Responses are plain GeoJSON / JSON dicts."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    """Partial overrides applied to DEFAULT_SETTINGS for an on-the-fly pipeline run."""

    # hazard
    hazard_weights: Optional[dict[str, float]] = Field(
        None, description="override composite weights, e.g. {'glof': 0.5, 'landslide': 0.2}"
    )
    monsoon: Optional[bool] = None
    rain_multiplier: Optional[float] = Field(None, ge=0.5, le=3.0)
    glof_lake_growth_years: Optional[int] = Field(None, ge=0, le=50)
    use_calibrated_weights: Optional[bool] = None

    # exposure
    population_growth_pct: Optional[float] = Field(None, ge=-20, le=100)
    tourist_load_factor: Optional[float] = Field(None, ge=1.0, le=3.0)

    # capacity
    water_lpcd: Optional[float] = Field(None, ge=40, le=200)
    evac_warning_window_h: Optional[float] = Field(None, ge=1, le=48)

    # priority / optimiser
    priority_breaks: Optional[dict[str, float]] = None
    max_reloc_distance_km: Optional[float] = Field(None, ge=5, le=200)
    discount_rate: Optional[float] = Field(None, ge=0.0, le=0.15)
    horizon_years: Optional[int] = Field(None, ge=5, le=60)

    def as_settings(self):
        from redzone.config import Settings

        s = Settings()
        if self.hazard_weights:
            s.hazard.weight_override = {**(s.hazard.weight_override or {}), **self.hazard_weights}
        if self.monsoon is not None:
            s.hazard.monsoon = self.monsoon
        if self.rain_multiplier is not None:
            s.hazard.rain_multiplier = self.rain_multiplier
        if self.glof_lake_growth_years is not None:
            s.hazard.glof_lake_growth_years = self.glof_lake_growth_years
        if self.use_calibrated_weights is not None:
            s.hazard.use_calibrated_weights = self.use_calibrated_weights
        if self.population_growth_pct is not None:
            s.population_growth_pct = self.population_growth_pct
        if self.tourist_load_factor is not None:
            s.tourist_load_factor = self.tourist_load_factor
        if self.water_lpcd is not None:
            s.capacity.water_lpcd = self.water_lpcd
        if self.evac_warning_window_h is not None:
            s.capacity.evac_warning_window_h = self.evac_warning_window_h
        if self.priority_breaks:
            s.priority.tier_breaks = {**s.priority.tier_breaks, **self.priority_breaks}
        if self.max_reloc_distance_km is not None:
            s.optimizer.max_reloc_distance_km = self.max_reloc_distance_km
        if self.discount_rate is not None:
            s.cost.discount_rate = self.discount_rate
        if self.horizon_years is not None:
            s.cost.horizon_years = self.horizon_years
        return s
