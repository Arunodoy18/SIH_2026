import type { RelocationPlan, ScenarioBody, Summary } from "./types";

export interface Narrative {
  mode: "ai" | "template";
  provider: "groq" | "anthropic" | null;
  model: string | null;
  text: string;
}

// Local dev: unset -> "/api", proxied to http://127.0.0.1:8000 by vite.config.ts.
// Production (Netlify): set VITE_API_BASE_URL to the deployed backend's URL (no trailing
// slash), e.g. https://nirnay-backend.onrender.com — the static build has no dev proxy.
const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

// Render's free tier sleeps the backend after ~15min idle; waking it up plus re-running
// the full pipeline for a scenario can take well over the ~31s it takes once warm. A bare
// fetch() never times out on its own, so a dead connection just hangs forever with no
// feedback — give every call a generous, explicit ceiling and a message that explains
// *why* it's slow instead of a cryptic "Failed to fetch".
const TIMEOUT_MS = 100_000;

async function withTimeout<T>(path: string, run: (signal: AbortSignal) => Promise<T>): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    return await run(ctrl.signal);
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new Error(
        `${path} timed out after ${TIMEOUT_MS / 1000}s — the free hosting tier can be slow ` +
        `to wake from idle; wait a moment and try again`
      );
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

async function get<T>(path: string): Promise<T> {
  return withTimeout(path, async (signal) => {
    const r = await fetch(BASE + path, { signal });
    if (!r.ok) throw new Error(`${path} -> ${r.status}`);
    return r.json() as Promise<T>;
  });
}

export const api = {
  health: () => get<{ status: string; processed_ready: boolean }>("/health"),
  summary: () => get<Summary>("/summary"),
  habitations: () => get<GeoJSON.FeatureCollection>("/habitations"),
  habitation: (id: string) => get<any>(`/habitations/${id}`),
  layer: (name: string) => get<GeoJSON.FeatureCollection>(`/layers/${name}`),
  plan: () => get<RelocationPlan>("/relocation/plan"),
  narrative: () => get<Narrative>("/report/narrative"),
  scenario: (body: ScenarioBody) =>
    withTimeout("/scenario", async (signal) => {
      const r = await fetch(BASE + "/scenario", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal,
      });
      if (!r.ok) throw new Error(`/scenario -> ${r.status}`);
      return r.json() as Promise<{
        summary: Summary;
        habitations: GeoJSON.FeatureCollection;
        hazard_tiers: GeoJSON.FeatureCollection;
        glacial_lakes: GeoJSON.FeatureCollection;
        relocation_plan: RelocationPlan;
      }>;
    }),
};

export const crore = (inr: number | null | undefined) =>
  inr == null ? "—" : `₹${(inr / 1e7).toLocaleString("en-IN", { maximumFractionDigits: 1 })} cr`;
export const num = (n: number | null | undefined, d = 0) =>
  n == null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: d });
