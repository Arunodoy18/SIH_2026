import { useState } from "react";
import { Link } from "react-router-dom";
import { Nav } from "../Nav";
import { MapView, type LayerKey } from "../MapView";
import { ErrorBoundary } from "../ErrorBoundary";
import { useNirnay } from "../store";
import { crore, num } from "../api";

const LAYERS: { key: LayerKey; label: string; sw?: string }[] = [
  { key: "hazard_tiers", label: "Hazard tiers (red→green)" },
  { key: "habitations", label: "Habitations (choropleth)" },
  { key: "flows", label: "Relocation flows" },
  { key: "destination_sites", label: "Green destination sites", sw: "#3f8f56" },
  { key: "glacial_lakes", label: "GLOF downstream paths", sw: "#b7410e" },
  { key: "rivers", label: "Rivers", sw: "#2b5f63" },
  { key: "historical_losses", label: "Historical loss events", sw: "#8a5a7c" },
];

export function Overview() {
  const { summary, plan, data, visible, setVisible, colourBy, setColourBy, busy, retrying, dirty, err, runScenario, loadBaseline } = useNirnay();

  const [glofGrowth, setGlofGrowth] = useState(0);
  const [popGrowth, setPopGrowth] = useState(0);
  const [monsoon, setMonsoon] = useState(true);
  const [tourist, setTourist] = useState(1);
  const [maxDist, setMaxDist] = useState(60);
  const [horizon, setHorizon] = useState(25);

  const c = summary?.counts;
  const top = plan?.ranked.slice(0, 6) ?? [];

  return (
    <div className="shell">
      <Nav />
      <div className="page">
        <div className="page-inner">
          <div className="breadcrumb"><Link to="/">NIRNAY</Link> &nbsp;/&nbsp; <Link to="/districts">Districts</Link> &nbsp;/&nbsp; <span className="cur">Mangan DDMA</span></div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <h1 style={{ fontFamily: "Newsreader, Georgia, serif", fontSize: 26, fontWeight: 600, margin: 0 }}>
              Mangan DDMA &middot; Teesta corridor
            </h1>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <select value={colourBy} onChange={(e) => setColourBy(e.target.value as "priority" | "hazard")}
                style={{ background: "var(--panel-2)", color: "var(--ink)", border: "1px solid var(--line)", borderRadius: 4, padding: "7px 10px", fontFamily: "IBM Plex Mono", fontSize: 11.5 }}>
                <option value="priority">colour: priority tier</option>
                <option value="hazard">colour: hazard tier</option>
              </select>
              <span style={{ fontFamily: "IBM Plex Mono", fontSize: 11, color: "var(--ink-dim)" }}>
                {dirty ? "scenario view" : "baseline"} &middot; {summary?.generated_s ?? "…"}s
              </span>
            </div>
          </div>

          {c && (
            <div className="grid-cards cols-4" style={{ marginBottom: 20 }}>
              <div className="stat"><div className="k">Population</div><div className="v">{num(c.population)}</div></div>
              <div className="stat"><div className="k">Red / Orange</div><div className="v" style={{ color: "var(--red)" }}>{c.hazard_tiers.red} <small>/ {c.hazard_tiers.orange}</small></div></div>
              <div className="stat"><div className="k">Relocate now</div><div className="v" style={{ color: "var(--accent)" }}>{c.priority_tiers.relocate_now} <small>+{c.priority_tiers.plan} plan</small></div></div>
              <div className="stat"><div className="k">Portfolio BCR</div><div className="v" style={{ color: "var(--green)" }}>{summary?.relocation.portfolio_benefit_cost_ratio}&times;</div></div>
            </div>
          )}

          <div className="overview-body" style={{ marginBottom: 20 }}>
            <div className="overview-map">
              <ErrorBoundary label="Map">
                <MapView data={data} visible={visible} colourBy={colourBy} selected={null} onSelect={() => {}} />
              </ErrorBoundary>
              <div className="legend">
                <b>Priority</b>
                {["relocate_now", "plan", "monitor", "safe"].map((t) => (
                  <div key={t} style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    <span className={`pill ${t}`}>&nbsp;</span> {t.replace("_", " ")}
                  </div>
                ))}
              </div>
            </div>

            <div className="priority-list">
              <div style={{ fontWeight: 600, fontSize: 13.5, marginBottom: 4 }}>Top priority habitations</div>
              {top.map((r) => (
                <Link key={r.hab_id} to={`/districts/mangan/habitations/${r.hab_id}`} className="priority-row">
                  <div>
                    <div className="priority-name" style={{ fontWeight: 600, fontSize: 13.5 }}>{r.habitation}</div>
                    <div style={{ fontFamily: "IBM Plex Mono", fontSize: 10.5, color: r.priority_tier === "relocate_now" ? "var(--red)" : "var(--orange)", marginTop: 3 }}>
                      {r.priority_tier.replace("_", " ").toUpperCase()} &middot; score {r.priority_score?.toFixed(2)}
                    </div>
                  </div>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--ink-dim)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 6 15 12 9 18" /></svg>
                </Link>
              ))}
              <Link to="/districts/mangan/plan" style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 16, fontWeight: 600, fontSize: 12.5, color: "var(--accent)", textDecoration: "none" }}>
                View full relocation plan
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
              </Link>
            </div>
          </div>

          <div className="grid-cards cols-2">
            <div className="card">
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10 }}>Layers</div>
              {LAYERS.map((l) => (
                <label className="toggle" key={l.key} style={{ fontSize: 12.5 }}>
                  <input type="checkbox" checked={visible[l.key]} onChange={(e) => setVisible({ ...visible, [l.key]: e.target.checked })} />
                  {l.sw && <span className="swatch" style={{ background: l.sw }} />}
                  {l.label}
                </label>
              ))}
            </div>

            <div className="card">
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10 }}>Scenario</div>
              <div className="slider">
                <label><span>Glacial-lake growth projection</span><span>{glofGrowth} yr</span></label>
                <input type="range" min={0} max={40} step={5} value={glofGrowth} onChange={(e) => setGlofGrowth(+e.target.value)} />
              </div>
              <div className="slider">
                <label><span>Population growth</span><span>{popGrowth}%</span></label>
                <input type="range" min={0} max={50} step={2} value={popGrowth} onChange={(e) => setPopGrowth(+e.target.value)} />
              </div>
              <div className="slider">
                <label><span>Peak-tourist load</span><span>&times;{tourist.toFixed(1)}</span></label>
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
              <div style={{ display: "flex", gap: 8, marginTop: 14, alignItems: "center" }}>
                <button disabled={busy} onClick={() =>
                  runScenario({
                    glof_lake_growth_years: glofGrowth, population_growth_pct: popGrowth,
                    tourist_load_factor: tourist, monsoon, max_reloc_distance_km: maxDist, horizon_years: horizon,
                  })}>
                  {busy ? (retrying ? "Waking backend, retrying…" : "Computing…") : "Run scenario"}
                </button>
                <button className="ghost" disabled={busy || !dirty} onClick={loadBaseline}>Reset</button>
              </div>
              {busy && (
                <div style={{ fontSize: 11.5, color: "var(--ink-dim)", marginTop: 8 }}>
                  Re-running the full hazard + relocation pipeline{retrying ? " — first request woke a sleeping backend, this can take up to a minute" : " — usually ~30s on the hosted backend"}.
                </div>
              )}
              {err && !busy && (
                <div style={{
                  marginTop: 10, padding: "9px 12px", borderRadius: 5, fontSize: 12,
                  background: "color-mix(in srgb, var(--red) 10%, transparent)",
                  border: "1px solid color-mix(in srgb, var(--red) 35%, var(--line))", color: "var(--ink)",
                }}>
                  Scenario failed: {err}
                </div>
              )}
            </div>
          </div>

          {plan && (
            <div style={{ marginTop: 20, fontFamily: "IBM Plex Mono", fontSize: 11, color: "var(--ink-dim)" }}>
              Relocation portfolio: {num(plan.totals.persons_moved)} people &middot; {crore(plan.totals.total_relocation_capex_inr)} &middot;
              {" "}payback {plan.totals.portfolio_payback_years} yr
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
