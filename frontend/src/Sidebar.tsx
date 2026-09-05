import { useState } from "react";
import type { LayerKey } from "./MapView";
import { HAZ_COLORS, PRIORITY_COLORS } from "./mapStyle";
import { crore, num } from "./api";
import type { ScenarioBody, Summary } from "./types";

const LAYERS: { key: LayerKey; label: string; sw?: string }[] = [
  { key: "hazard_tiers", label: "Hazard tiers (red→green)" },
  { key: "habitations", label: "Habitations (choropleth)" },
  { key: "flows", label: "Relocation flows" },
  { key: "destination_sites", label: "Green destination sites", sw: PRIORITY_COLORS.safe },
  { key: "glacial_lakes", label: "GLOF downstream paths", sw: "#8ad2ff" },
  { key: "rivers", label: "Rivers", sw: "#5bc8ff" },
  { key: "historical_losses", label: "Historical loss events", sw: "#b892ff" },
];

export function Sidebar({
  summary, visible, setVisible, colourBy, setColourBy, onApply, onReset, busy, dirty,
}: {
  summary: Summary | null;
  visible: Record<LayerKey, boolean>;
  setVisible: (v: Record<LayerKey, boolean>) => void;
  colourBy: "priority" | "hazard";
  setColourBy: (c: "priority" | "hazard") => void;
  onApply: (b: ScenarioBody) => void;
  onReset: () => void;
  busy: boolean;
  dirty: boolean;
}) {
  const [glofGrowth, setGlofGrowth] = useState(0);
  const [popGrowth, setPopGrowth] = useState(0);
  const [monsoon, setMonsoon] = useState(true);
  const [tourist, setTourist] = useState(1);
  const [maxDist, setMaxDist] = useState(60);
  const [horizon, setHorizon] = useState(25);

  const c = summary?.counts;
  const h = summary?.hazard;
  const r = summary?.relocation;
  const seismicWindow = summary?.seismic_outlook?.elastic_rebound?.windows?.[0];

  return (
    <div className="sidebar">
      <h1>RedZone · Mangan DDMA</h1>
      <div className="sub">{summary?.aoi ?? "loading…"}</div>

      {c && (
        <div className="stat-grid">
          <div className="stat"><div className="k">Habitations</div><div className="v">{c.habitations}</div></div>
          <div className="stat"><div className="k">Population</div><div className="v">{num(c.population)}</div></div>
          <div className="stat"><div className="k">Red / Orange</div><div className="v" style={{ color: HAZ_COLORS.red }}>{c.hazard_tiers.red}<small> / {c.hazard_tiers.orange}</small></div></div>
          <div className="stat"><div className="k">Relocate now</div><div className="v" style={{ color: PRIORITY_COLORS.relocate_now }}>{c.priority_tiers.relocate_now}<small> +{c.priority_tiers.plan} plan</small></div></div>
        </div>
      )}

      {r && (
        <>
          <h2>Relocation portfolio</h2>
          <div className="kv"><span className="k">People to move</span><span>{num(r.persons_moved)}{r.persons_unmet ? ` (+${num(r.persons_unmet)} unmet)` : ""}</span></div>
          <div className="kv"><span className="k">Relocation capex</span><span>{crore(r.total_relocation_capex_inr)}</span></div>
          <div className="kv"><span className="k">PV losses avoided</span><span>{crore(r.pv_losses_avoided_inr)}</span></div>
          <div className="kv"><span className="k">Benefit–cost ratio</span><span>{r.portfolio_benefit_cost_ratio ?? "—"}</span></div>
          <div className="kv"><span className="k">Payback</span><span>{r.portfolio_payback_years ?? "—"} yr</span></div>
        </>
      )}

      {h && (
        <>
          <h2>Hazard weights (calibrated)</h2>
          {Object.entries(h.weights).map(([k, v]) => (
            <div className="kv" key={k}><span className="k">{k}</span><span>{(v * 100).toFixed(0)}%</span></div>
          ))}
          <div className="kv"><span className="k">Composite R² vs loss</span><span>{h.calibration.composite_r2}</span></div>
          <div className="kv"><span className="k">Ranking AUC</span><span>{h.calibration.ranking_auc}</span></div>
          {h.landslide_method === "ml" && h.landslide_model && (
            <div className="kv">
              <span className="k">Landslide model (RF)</span>
              <span style={{ color: "var(--green)" }}>AUC {h.landslide_model.roc_auc_test.toFixed(2)}</span>
            </div>
          )}
        </>
      )}

      {seismicWindow && (
        <>
          <h2>Seismic outlook (elastic rebound)</h2>
          <div className="kv">
            <span className="k">{seismicWindow.window_years}-yr renewal vs Poisson</span>
            <span>
              {(seismicWindow.renewal_probability * 100).toFixed(1)}% vs{" "}
              {(seismicWindow.poisson_probability * 100).toFixed(1)}%
            </span>
          </div>
          <div className="kv">
            <span className="k">Signal</span>
            <span style={{ textTransform: "capitalize" }}>{seismicWindow.renewal_vs_poisson}</span>
          </div>
          <div className="kv">
            <span className="k">Since 2011 M6.9</span>
            <span>{summary?.seismic_outlook.elastic_rebound.years_elapsed} yr</span>
          </div>
        </>
      )}

      <h2>Layers</h2>
      <div className="row">
        <span className="k" style={{ color: "var(--ink-dim)" }}>Colour habitations by</span>
        <select value={colourBy} onChange={(e) => setColourBy(e.target.value as any)}
          style={{ background: "var(--panel-2)", color: "var(--ink)", border: "1px solid var(--line)", borderRadius: 6, padding: "3px 6px" }}>
          <option value="priority">priority tier</option>
          <option value="hazard">hazard tier</option>
        </select>
      </div>
      {LAYERS.map((l) => (
        <label className="toggle" key={l.key}>
          <input type="checkbox" checked={visible[l.key]}
            onChange={(e) => setVisible({ ...visible, [l.key]: e.target.checked })} />
          {l.sw && <span className="swatch" style={{ background: l.sw }} />}
          {l.label}
        </label>
      ))}

      <h2>Scenario</h2>
      <div className="slider">
        <label><span>Glacial-lake growth projection</span><span>{glofGrowth} yr</span></label>
        <input type="range" min={0} max={40} step={5} value={glofGrowth} onChange={(e) => setGlofGrowth(+e.target.value)} />
      </div>
      <div className="slider">
        <label><span>Population growth</span><span>{popGrowth}%</span></label>
        <input type="range" min={0} max={50} step={2} value={popGrowth} onChange={(e) => setPopGrowth(+e.target.value)} />
      </div>
      <div className="slider">
        <label><span>Peak-tourist load</span><span>×{tourist.toFixed(1)}</span></label>
        <input type="range" min={1} max={2.5} step={0.1} value={tourist} onChange={(e) => setTourist(+e.target.value)} />
      </div>
      <div className="slider">
        <label><span>Max relocation distance</span><span>{maxDist} km</span></label>
        <input type="range" min={15} max={120} step={5} value={maxDist} onChange={(e) => setMaxDist(+e.target.value)} />
      </div>
      <div className="slider">
        <label><span>Cost-benefit horizon</span><span>{horizon} yr</span></label>
        <input type="range" min={10} max={40} step={5} value={horizon} onChange={(e) => setHorizon(+e.target.value)} />
      </div>
      <label className="toggle">
        <input type="checkbox" checked={monsoon} onChange={(e) => setMonsoon(e.target.checked)} />
        Monsoon season
      </label>

      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <button disabled={busy} onClick={() =>
          onApply({
            glof_lake_growth_years: glofGrowth, population_growth_pct: popGrowth,
            tourist_load_factor: tourist, monsoon, max_reloc_distance_km: maxDist, horizon_years: horizon,
          })}>
          {busy ? "Running…" : "Run scenario"}
        </button>
        <button className="ghost" disabled={busy || !dirty} onClick={onReset}>Reset</button>
      </div>
    </div>
  );
}
