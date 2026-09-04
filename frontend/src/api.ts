import type { RelocationPlan, ScenarioBody, Summary } from "./types";

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(BASE + path);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}

export const api = {
  health: () => get<{ status: string; processed_ready: boolean }>("/health"),
  summary: () => get<Summary>("/summary"),
  habitations: () => get<GeoJSON.FeatureCollection>("/habitations"),
  habitation: (id: string) => get<any>(`/habitations/${id}`),
  layer: (name: string) => get<GeoJSON.FeatureCollection>(`/layers/${name}`),
  plan: () => get<RelocationPlan>("/relocation/plan"),
  scenario: async (body: ScenarioBody) => {
    const r = await fetch(BASE + "/scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`/scenario -> ${r.status}`);
    return r.json() as Promise<{
      summary: Summary;
      habitations: GeoJSON.FeatureCollection;
      hazard_tiers: GeoJSON.FeatureCollection;
      glacial_lakes: GeoJSON.FeatureCollection;
      relocation_plan: RelocationPlan;
    }>;
  },
};

export const crore = (inr: number | null | undefined) =>
  inr == null ? "—" : `₹${(inr / 1e7).toLocaleString("en-IN", { maximumFractionDigits: 1 })} cr`;
export const num = (n: number | null | undefined, d = 0) =>
  n == null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: d });
