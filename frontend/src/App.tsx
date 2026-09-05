import { useEffect, useState } from "react";
import { MapView, type LayerKey } from "./MapView";
import { Sidebar } from "./Sidebar";
import { Drawer } from "./Drawer";
import { BottomPanel } from "./BottomPanel";
import { ReportModal } from "./ReportModal";
import { ErrorBoundary } from "./ErrorBoundary";
import { api, type Narrative } from "./api";
import type { RelocationPlan, ScenarioBody, Summary } from "./types";

const DEFAULT_VISIBLE: Record<LayerKey, boolean> = {
  hazard_tiers: true, habitations: true, flows: true, destination_sites: true,
  glacial_lakes: true, rivers: false, historical_losses: false,
};

export function App() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [plan, setPlan] = useState<RelocationPlan | null>(null);
  const [data, setData] = useState<Record<string, GeoJSON.FeatureCollection>>({});
  const [visible, setVisible] = useState(DEFAULT_VISIBLE);
  const [colourBy, setColourBy] = useState<"priority" | "hazard">("priority");
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [reportOpen, setReportOpen] = useState(false);
  const [reportBusy, setReportBusy] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const [narrative, setNarrative] = useState<Narrative | null>(null);

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
    setBusy(true); setErr(null);
    try {
      const r = await api.scenario(body);
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
      setBusy(false);
    }
  }

  async function generateReport() {
    setReportOpen(true); setReportBusy(true); setReportError(null);
    try {
      setNarrative(await api.narrative());
    } catch (e) {
      setReportError(String(e));
    } finally {
      setReportBusy(false);
    }
  }

  return (
    <div className="app">
      <Sidebar
        summary={summary} visible={visible} setVisible={setVisible}
        colourBy={colourBy} setColourBy={setColourBy}
        onApply={runScenario} onReset={loadBaseline} busy={busy} dirty={dirty}
      />
      <div className="map-wrap">
        <ErrorBoundary label="Map">
          <MapView data={data} visible={visible} colourBy={colourBy} selected={selected} onSelect={setSelected} />
        </ErrorBoundary>
        <div className="badge">
          {dirty ? "scenario view" : "baseline"} · {summary?.generated_s ?? "…"}s
          {err ? ` · ${err}` : ""}
        </div>
        <div className="legend">
          <b>Priority</b>
          {["relocate_now", "plan", "monitor", "safe"].map((t) => (
            <div key={t} style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <span className={`pill ${t}`}>&nbsp;</span> {t.replace("_", " ")}
            </div>
          ))}
        </div>
        {selected && <Drawer habId={selected} onClose={() => setSelected(null)} />}
      </div>
      <BottomPanel
        plan={plan} selected={selected} onSelect={setSelected}
        onGenerateReport={generateReport} reportBusy={reportBusy}
      />
      {reportOpen && (
        <ReportModal
          data={narrative} busy={reportBusy} error={reportError}
          onClose={() => setReportOpen(false)}
        />
      )}
    </div>
  );
}
