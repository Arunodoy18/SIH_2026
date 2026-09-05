import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, PolarRadiusAxis } from "recharts";
import { Nav } from "../Nav";
import { api, crore } from "../api";

export function HabitationPage() {
  const { habId = "" } = useParams();
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setD(null); setErr(null);
    api.habitation(habId).then(setD).catch((e) => setErr(String(e)));
  }, [habId]);

  return (
    <div className="shell">
      <Nav />
      <div className="page">
        <div className="page-inner">
          <div className="breadcrumb">
            <Link to="/">NIRNAY</Link> &nbsp;/&nbsp; <Link to="/districts">Districts</Link> &nbsp;/&nbsp;
            <Link to="/districts/mangan"> Mangan DDMA</Link> &nbsp;/&nbsp; <span className="cur">{d?.name ?? habId}</span>
          </div>

          {err && <div className="err">{err}</div>}
          {!d && !err && <div className="spin">loading…</div>}

          {d && (() => {
            const b = d.breakdown;
            const radar = [
              { k: "landslide", v: b.hazard.landslide ?? 0 },
              { k: "GLOF", v: b.hazard.glof ?? 0 },
              { k: "seismic", v: b.hazard.seismic ?? 0 },
              { k: "flood", v: b.hazard.flood ?? 0 },
              { k: "vuln.", v: b.svi ?? 0 },
              { k: "deficit", v: Math.min(1, (b.carrying_capacity.deficit_ratio ?? 0) / 2) },
            ];
            const cc = b.carrying_capacity;
            return (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 4 }}>
                  <h1 style={{ fontFamily: "Newsreader, Georgia, serif", fontSize: 28, fontWeight: 600, margin: 0 }}>{d.name}</h1>
                  <span className={`pill ${b.priority.tier}`}>{b.priority.tier?.replace("_", " ")}</span>
                </div>
                <div style={{ fontFamily: "IBM Plex Mono", fontSize: 12, color: "var(--ink-dim)", marginBottom: 26 }}>
                  {d.block} block &middot; {d.district} district &middot; pop {d.population?.toLocaleString("en-IN")} &middot; {d.households} households
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20, alignItems: "start" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <div className="card" style={{ borderLeft: "3px solid var(--red)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                        <b>Hazard</b>
                        <span style={{ fontFamily: "IBM Plex Mono", fontWeight: 600 }}>{b.hazard_composite} &middot; {b.hazard_tier}</span>
                      </div>
                      {Object.entries(b.hazard).map(([k, v]) => (
                        <div key={k} style={{ marginBottom: 10 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, marginBottom: 4 }}>
                            <span style={{ textTransform: "capitalize" }}>{k}</span><span style={{ fontFamily: "IBM Plex Mono" }}>{v as any}</span>
                          </div>
                          <div className="bar-track"><div className="bar-fill" style={{ width: `${(v as number) * 100}%`, background: "var(--accent)" }} /></div>
                        </div>
                      ))}
                    </div>

                    <div className="card" style={{ borderLeft: "3px solid var(--geo)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                        <b>Social vulnerability</b>
                        <span style={{ fontFamily: "IBM Plex Mono", fontWeight: 600, color: "var(--geo)" }}>{b.svi}</span>
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                        {Object.entries(b.svi_components).map(([k, v]) => (
                          <span key={k} style={{ fontFamily: "IBM Plex Mono", fontSize: 11, padding: "5px 10px", borderRadius: 999, background: "var(--panel-2)" }}>
                            {k} &middot; {v as any}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="card" style={{ borderLeft: "3px solid var(--yellow)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                        <b>Carrying capacity</b>
                        <span style={{ fontFamily: "IBM Plex Mono", fontWeight: 600 }}>{cc.deficit_ratio} &middot; {cc.status}</span>
                      </div>
                      <div style={{ fontSize: 12.5, color: "var(--ink-dim)", marginBottom: 10 }}>
                        Limiting factor &mdash; <b style={{ color: "var(--ink)" }}>{cc.limiting_factor}</b>
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, fontFamily: "IBM Plex Mono", fontSize: 12 }}>
                        <div><div style={{ color: "var(--ink-dim)", fontSize: 10 }}>WATER</div>{cc.water_pop?.toLocaleString("en-IN")}</div>
                        <div><div style={{ color: "var(--ink-dim)", fontSize: 10 }}>LAND</div>{cc.land_pop?.toLocaleString("en-IN")}</div>
                        <div><div style={{ color: "var(--ink-dim)", fontSize: 10 }}>EVAC</div>{cc.evacuation_pop?.toLocaleString("en-IN")}</div>
                        <div><div style={{ color: "var(--ink-dim)", fontSize: 10 }}>SERVICES</div>{cc.services_pop?.toLocaleString("en-IN")}</div>
                      </div>
                    </div>
                  </div>

                  <div className="card" style={{ border: "1px solid color-mix(in srgb, var(--accent) 35%, var(--line))" }}>
                    <div className="eyebrow" style={{ marginBottom: 12 }}>Recommended action</div>
                    <div style={{ height: 160, marginBottom: 6 }}>
                      <ResponsiveContainer>
                        <RadarChart data={radar} outerRadius={58}>
                          <PolarGrid stroke="#ddd6c4" />
                          <PolarAngleAxis dataKey="k" tick={{ fill: "#6b6353", fontSize: 10 }} />
                          <PolarRadiusAxis domain={[0, 1]} tick={false} axisLine={false} />
                          <Radar dataKey="v" stroke="#b7410e" fill="#b7410e" fillOpacity={0.28} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="kv"><span className="k">Persons relocated</span><span>{b.relocation.persons_relocated?.toLocaleString("en-IN") ?? "—"}</span></div>
                    <div className="kv"><span className="k">Expected annual loss</span><span>{crore(b.relocation.eal_inr)}/yr</span></div>
                    <div className="kv"><span className="k">Relocation capex</span><span>{crore(b.relocation.relocation_capex_inr)}</span></div>
                    <div className="kv"><span className="k">Benefit–cost ratio</span><span style={{ color: (b.relocation.benefit_cost_ratio ?? 0) >= 1 ? "var(--green)" : "var(--ink)" }}>{b.relocation.benefit_cost_ratio ?? "—"}</span></div>
                    <div className="kv"><span className="k">Payback</span><span>{b.relocation.payback_years ?? "—"} yr</span></div>
                    <Link to="/districts/mangan/plan" className="btn-primary" style={{ marginTop: 16, justifyContent: "center", width: "100%" }}>
                      View in relocation plan
                    </Link>
                  </div>
                </div>
              </>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
