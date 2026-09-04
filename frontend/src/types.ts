export type HazTier = "green" | "yellow" | "orange" | "red";
export type PriorityTier = "safe" | "monitor" | "plan" | "relocate_now";

export interface Summary {
  aoi: string;
  generated_s: number;
  counts: {
    habitations: number;
    population: number;
    hazard_tiers: Record<HazTier, number>;
    priority_tiers: Record<PriorityTier, number>;
    capacity_status: Record<string, number>;
  };
  hazard: {
    weights: Record<string, number>;
    tier_breaks: Record<string, number>;
    calibration: {
      n_events: number;
      composite_r2: number;
      composite_spearman: number;
      ranking_auc: number;
      decomposition_r2: number;
      decomposition_loo_r2: number;
    };
  };
  relocation: {
    phases: PlanPhase[];
    persons_moved: number;
    persons_unmet: number;
    total_relocation_capex_inr: number;
    pv_losses_avoided_inr: number;
    portfolio_benefit_cost_ratio: number | null;
    portfolio_payback_years: number | null;
    solver: string;
  };
}

export interface PlanPhase {
  phase: number;
  label: string;
  habitations: number;
  persons_to_move: number;
  persons_unmet: number;
  households: number;
  capex_inr: number;
  pv_benefit_inr: number;
}

export interface RankedRow {
  hab_id: string;
  habitation: string;
  block: string;
  priority_tier: PriorityTier;
  phase: number;
  priority_score: number;
  haz_tier: HazTier;
  haz_composite: number;
  svi: number;
  cc_deficit_ratio: number;
  cc_limiting_factor: string;
  persons_to_move: number;
  persons_placed: number;
  persons_unmet: number;
  households: number;
  destination: string | null;
  split: boolean;
  nearest_distance_km: number | null;
  relocation_capex_inr: number | null;
  eal_inr: number | null;
  pv_benefit_inr: number | null;
  benefit_cost_ratio: number | null;
  payback_years: number | null;
}

export interface RelocationPlan {
  phases: PlanPhase[];
  ranked: RankedRow[];
  unmet: { hab_id: string; name: string; persons: number; reason?: string }[];
  site_utilisation: { site_id: string; name: string; used: number; capacity: number; pct: number }[];
  solver: string;
  split_habitations: number;
  totals: Record<string, number>;
  flows: GeoJSON.FeatureCollection;
}

export interface ScenarioBody {
  hazard_weights?: Record<string, number>;
  monsoon?: boolean;
  rain_multiplier?: number;
  glof_lake_growth_years?: number;
  use_calibrated_weights?: boolean;
  population_growth_pct?: number;
  tourist_load_factor?: number;
  max_reloc_distance_km?: number;
  discount_rate?: number;
  horizon_years?: number;
}
