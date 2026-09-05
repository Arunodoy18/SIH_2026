import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type Narrative } from "./api";
import type { LayerKey } from "./MapView";
import type { RelocationPlan, ScenarioBody, Summary } from "./types";

const DEFAULT_VISIBLE: Record<LayerKey, boolean> = {
  hazard_tiers: true, habitations: true, flows: true, destination_sites: true,
  glacial_lakes: true, rivers: false, historical_losses: false,
};

interface Store {
  summary: Summary | null;
  plan: RelocationPlan | null;
  data: Record<string, GeoJSON.FeatureCollection>;
  visible: Record<LayerKey, boolean>;
  setVisible: (v: Record<LayerKey, boolean>) => void;
  colourBy: "priority" | "hazard";
  setColourBy: (c: "priority" | "hazard") => void;
  busy: boolean;
  retrying: boolean;
  dirty: boolean;
  err: string | null;
  loadBaseline: () => Promise<void>;
  runScenario: (body: ScenarioBody) => Promise<void>;
  narrative: Narrative | null;
  narrativeBusy: boolean;
  narrativeError: string | null;
  generateReport: () => Promise<void>;
}

const Ctx = createContext<Store | null>(null);

export function NirnayProvider({ children }: { children: ReactNode }) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [plan, setPlan] = useState<RelocationPlan | null>(null);
  const [data, setData] = useState<Record<string, GeoJSON.FeatureCollection>>({});
  const [visible, setVisible] = useState(DEFAULT_VISIBLE);
  const [colourBy, setColourBy] = useState<"priority" | "hazard">("priority");
  const [busy, setBusy] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [narrative, setNarrative] = useState<Narrative | null>(null);
  const [narrativeBusy, setNarrativeBusy] = useState(false);
  const [narrativeError, setNarrativeError] = useState<string | null>(null);

  async function loadBaseline() {
    try {
      const [s, hb, ht, gl, rv, ds, hl, pl] = await Promise.all([
        api.summary(), api.habitations(), api.layer("hazard_tiers"), api.layer("glacial_lakes"),
        api.layer("rivers"), api.layer("destination_sites"), api.layer("historical_losses"), api.plan(),
      ]);
      setSummary(s); setPlan(pl);
      setData({
        habitations: hb, hazard_tiers: ht, glacial_lakes: gl, rivers: rv,
        destination_sites: ds, historical_losses: hl, flows: pl.flows,
      });
      setDirty(false);
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => { loadBaseline(); }, []);

  async function runScenario(body: ScenarioBody) {
    setBusy(true); setErr(null); setRetrying(false);
    try {
      let r;
      try {
        r = await api.scenario(body);
      } catch (firstErr) {
        // The most common real-world failure here is a Render free-tier instance that
        // went to sleep: the first request wakes the container (can take well over a
        // minute) and dies before the pipeline even starts. By the time we retry, the
        // container is warm and the same call normally succeeds in ~30s. One silent
        // retry turns that cold-start hiccup into a longer wait instead of a hard error.
        setRetrying(true);
        r = await api.scenario(body);
      }
      setSummary(r.summary); setPlan(r.relocation_plan);
      setData((d) => ({
        ...d,
        habitations: r.habitations,
        hazard_tiers: r.hazard_tiers,
        glacial_lakes: r.glacial_lakes,
        flows: r.relocation_plan.flows,
      }));
      setDirty(true);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false); setRetrying(false);
    }
  }

  async function generateReport() {
    setNarrativeBusy(true); setNarrativeError(null);
    try {
      setNarrative(await api.narrative());
    } catch (e) {
      setNarrativeError(String(e));
    } finally {
      setNarrativeBusy(false);
    }
  }

  return (
    <Ctx.Provider value={{
      summary, plan, data, visible, setVisible, colourBy, setColourBy, busy, retrying, dirty, err,
      loadBaseline, runScenario, narrative, narrativeBusy, narrativeError, generateReport,
    }}>
      {children}
    </Ctx.Provider>
  );
}

export function useNirnay(): Store {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useNirnay must be used within <NirnayProvider>");
  return ctx;
}
