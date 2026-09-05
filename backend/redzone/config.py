"""Central configuration: area of interest, CRS, grid, model weights, cost params, capacity norms.

Every number a planner might reasonably contest lives here (not buried in a module) and is
overridable at request time via POST /scenario -> ScenarioOverrides.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
SAMPLES_DIR = DATA_DIR / "samples"
MODELS_DIR = DATA_DIR / "models"

for _d in (RAW_DIR, INTERIM_DIR, PROCESSED_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------------------
# Coordinate reference systems
# --------------------------------------------------------------------------------------
CRS_GEO = "EPSG:4326"      # storage + web display
CRS_METRIC = "EPSG:32645"  # UTM 45N — metric ops over Sikkim (areas, distances, buffers)

# --------------------------------------------------------------------------------------
# Area of interest — Mangan DDMA / Teesta corridor, widened north to reach South Lhonak
# --------------------------------------------------------------------------------------
AOI_MIN_LON, AOI_MAX_LON = 88.15, 88.95
AOI_MIN_LAT, AOI_MAX_LAT = 27.15, 28.10
AOI_BBOX = (AOI_MIN_LON, AOI_MIN_LAT, AOI_MAX_LON, AOI_MAX_LAT)

# Hazard raster grid resolution in degrees (~0.0025 deg ≈ 250 m at this latitude)
GRID_RES_DEG = 0.0025


@dataclass(frozen=True)
class Grid:
    min_lon: float = AOI_MIN_LON
    min_lat: float = AOI_MIN_LAT
    max_lon: float = AOI_MAX_LON
    max_lat: float = AOI_MAX_LAT
    res: float = GRID_RES_DEG

    @property
    def nx(self) -> int:
        return int(round((self.max_lon - self.min_lon) / self.res))

    @property
    def ny(self) -> int:
        return int(round((self.max_lat - self.min_lat) / self.res))

    @property
    def transform(self):  # affine: (a, b, c, d, e, f) — north-up
        from rasterio.transform import from_origin

        return from_origin(self.min_lon, self.max_lat, self.res, self.res)


GRID = Grid()

# --------------------------------------------------------------------------------------
# Hazards
# --------------------------------------------------------------------------------------
HAZARDS = ("landslide", "glof", "seismic", "flood")

# Default AHP / expert-prior weights (used until calibrate.py fits weights on loss data).
# Sikkim rationale: landslide is the chronic, spatially pervasive killer; GLOF is
# catastrophic but valley-confined; seismic is state-wide (Zone IV); flash flood tracks rivers.
AHP_WEIGHTS = {"landslide": 0.34, "glof": 0.24, "seismic": 0.24, "flood": 0.18}

# Tier cut points on the 0..1 composite hazard score (quantile-anchored, see composite.py)
HAZARD_TIERS = ("green", "yellow", "orange", "red")
TIER_BREAKS = {"yellow": 0.35, "orange": 0.55, "red": 0.75}  # >= break => that tier or higher

# Synthetic "ground-truth" weights used only to fabricate the seed's historical-loss
# magnitudes (redzone/hazard/synth_losses.py). GLOF-heavy — the recent record is dominated
# by Oct 2023. Calibration should recover something close to this from the AHP prior.
# In a real deployment this vector does not exist: calibration fits against actual
# SDMA / DesInventar loss records.
LATENT_LOSS_WEIGHTS = {"landslide": 0.30, "glof": 0.36, "seismic": 0.14, "flood": 0.20}


# Relative zonation: tiers are cut at quantiles of the composite over the AOI grid
# (how GSI/BMTPC-style susceptibility maps are classed), unless tier_mode="absolute".
TIER_QUANTILES = {"yellow": 0.50, "orange": 0.78, "red": 0.92}


@dataclass
class HazardParams:
    # if set (via POST /scenario) these win over both calibrated and AHP weights
    weight_override: dict = None
    tier_mode: str = "quantile"  # "quantile" | "absolute"
    tier_quantiles: dict = field(default_factory=lambda: dict(TIER_QUANTILES))
    tier_breaks: dict = field(default_factory=lambda: dict(TIER_BREAKS))
    use_calibrated_weights: bool = True
    # scenario knobs
    monsoon: bool = True          # monsoon amplifies landslide + flood
    rain_multiplier: float = 1.0  # extra rainfall stress (climate scenario)
    glof_lake_growth_years: int = 0  # project glacial-lake area N years forward
    # "heuristic" = fields.landslide_field (slope/rain/incident proxy);
    # "ml" = a RandomForest trained on a landslide inventory (redzone/ml/) — falls back to
    # "heuristic" automatically if no trained model is on disk (see ml/landslide_ml.py).
    landslide_method: str = "ml"


# --------------------------------------------------------------------------------------
# Social vulnerability
# --------------------------------------------------------------------------------------
# Census / SECC indicators -> 0..1, higher = more vulnerable. "invert" flips (e.g. literacy).
SVI_INDICATORS = {
    "st_pct": {"weight": 1.0, "invert": False},
    "sc_pct": {"weight": 0.6, "invert": False},
    "kutcha_pct": {"weight": 1.0, "invert": False},
    "elderly_pct": {"weight": 0.8, "invert": False},
    "children_pct": {"weight": 0.8, "invert": False},
    "bpl_pct": {"weight": 1.0, "invert": False},
    "literacy_pct": {"weight": 0.6, "invert": True},
    "isolation_index": {"weight": 0.8, "invert": False},  # single-lifeline-road remoteness
}
SVI_METHOD = "weighted"  # "weighted" | "pca"


# --------------------------------------------------------------------------------------
# Carrying capacity norms  (STUB values — flagged provisional, pending BIS/IPHS/IRC citation)
# --------------------------------------------------------------------------------------
@dataclass
class CapacityNorms:
    water_lpcd: float = 70.0            # litres/person/day (hill-rural; BIS urban norm is 135)
    runoff_coefficient: float = 0.35   # fraction of rainfall available as usable supply
    built_area_per_capita_m2: float = 150.0  # dwelling + lane + amenity share on hill terrain
    slope_buildable_max_deg: float = 30.0
    hospital_beds_per_1000: float = 1.0      # IPHS aspiration
    school_seats_per_1000: float = 180.0
    road_lane_capacity_pph: float = 800.0    # persons/hour, mountain road, mixed traffic
    evac_warning_window_h: float = 6.0
    # combine the four sub-capacities: "power" = generalised mean, exponent `combine_p`
    # (p=-inf -> min/limiting, p=-1 -> harmonic); binding constraint dominates, others matter.
    combine: str = "power"    # "power" | "limiting" | "harmonic" | "mean"
    combine_p: float = -3.0


CAPACITY_NORMS = CapacityNorms()


# --------------------------------------------------------------------------------------
# Cost–benefit
# --------------------------------------------------------------------------------------
@dataclass
class CostParams:
    unit_housing_cost_inr: float = 900_000.0     # per household, hill construction (PMAY-plus)
    infra_cost_per_capita_inr: float = 250_000.0 # roads/water/school/PHC share at destination
    land_cost_per_ha_inr: float = 2_500_000.0
    persons_per_ha: float = 250.0                # resettlement density on hill terraces
    per_capita_asset_value_inr: float = 900_000.0  # house + land + public-infra share at origin
    discount_rate: float = 0.06
    horizon_years: int = 25
    # EAL = annual_event_prob · loss_fraction(hazard, svi) · assets_at_risk
    #   annual_event_prob = eal_hazard_to_annual_prob · haz_composite²   (convex: worst spots
    #   see a damaging event every few years; moderate spots once a generation)
    eal_hazard_to_annual_prob: float = 0.30
    eal_max_loss_fraction: float = 0.9       # cap on fraction of assets lost in a severe event


COST_PARAMS = CostParams()


# --------------------------------------------------------------------------------------
# Relocation priority
# --------------------------------------------------------------------------------------
PRIORITY_TIERS = ("relocate_now", "plan", "monitor", "safe")

# priority_score = (hazard ** a) * (svi ** b) * (deficit_factor ** c), then tiered by breaks
@dataclass
class PriorityParams:
    hazard_exp: float = 1.0
    svi_exp: float = 0.7
    deficit_exp: float = 0.5
    # deficit_factor = clip(deficit_ratio, 0.5, 3.0) normalised to ~0..1
    tier_breaks: dict = field(default_factory=lambda: {"monitor": 0.30, "plan": 0.55, "relocate_now": 0.75})
    # fraction of a habitation's population actually moved, by tier
    move_fraction: dict = field(default_factory=lambda: {"relocate_now": 1.0, "plan": 0.4, "monitor": 0.0, "safe": 0.0})


PRIORITY_PARAMS = PriorityParams()


# --------------------------------------------------------------------------------------
# Relocation optimiser
# --------------------------------------------------------------------------------------
@dataclass
class OptimizerParams:
    w_distance: float = 1.0                 # cost weight on origin->dest travel distance (per person-km)
    w_servicing: float = 1.0               # cost weight on destination servicing cost
    w_community_split: float = 8.0         # penalty per extra site a habitation is split across
    max_reloc_distance_km: float = 60.0    # hard cap — beyond this a destination is infeasible
    solver_time_limit_s: int = 20


OPTIMIZER_PARAMS = OptimizerParams()


# --------------------------------------------------------------------------------------
# Seismic temporal outlook — Gutenberg–Richter frequency + elastic-rebound renewal
# probability (Brownian Passage Time). District-level, not yet per-fault-segment: public
# seismotectonic data isn't resolved finely enough for that at this scale. Parameters below
# are literature-typical for the Eastern Himalaya, anchored to the real 2011 M6.9 event —
# not fit to a project-specific catalog. Flagged the same way as the capacity norms.
# --------------------------------------------------------------------------------------
@dataclass
class SeismicRenewalParams:
    gr_b: float = 0.9                       # Gutenberg–Richter b-value (typical Himalaya: 0.8-1.0)
    gr_m_ref: float = 6.0                   # reference magnitude the return period below is anchored to
    gr_return_period_years_at_m_ref: float = 75.0  # regional M>=6.0 return period (informs G-R "a")
    reference_magnitudes: tuple = (6.0, 6.5, 7.0)
    last_major_event_year: int = 2011       # the Sikkim M6.9 earthquake, 18 Sep 2011
    # BPT renewal ("elastic rebound") uses the same mean recurrence as the G-R anchor above,
    # so the two models describe one coherent story: G-R sets the long-run average rate;
    # BPT reshapes *when* the next event is likely, given 2011 reset the clock.
    bpt_aperiodicity: float = 0.5           # coefficient of variation; USGS WGCEP practice: 0.3-0.7
    outlook_windows_years: tuple = (10, 25, 50)


SEISMIC_RENEWAL = SeismicRenewalParams()


# --------------------------------------------------------------------------------------
# Bundle passed through the pipeline; POST /scenario patches a copy of this.
# --------------------------------------------------------------------------------------
@dataclass
class Settings:
    hazard: HazardParams = field(default_factory=HazardParams)
    capacity: CapacityNorms = field(default_factory=lambda: CapacityNorms())
    cost: CostParams = field(default_factory=lambda: CostParams())
    priority: PriorityParams = field(default_factory=PriorityParams)
    optimizer: OptimizerParams = field(default_factory=OptimizerParams)
    seismic: SeismicRenewalParams = field(default_factory=SeismicRenewalParams)
    population_growth_pct: float = 0.0     # apply to current population before scoring (2011->horizon)
    tourist_load_factor: float = 1.0      # multiply effective population (peak-season scenario)

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_SETTINGS = Settings()
