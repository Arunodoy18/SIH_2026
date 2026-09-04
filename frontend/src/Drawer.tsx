import { useEffect, useState } from "react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, PolarRadiusAxis } from "recharts";
import { api, crore } from "./api";

export function Drawer({ habId, onClose }: { habId: string; onClose: () => void }) {
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setD(null); setErr(null);
    api.habitation(habId).then(setD).catch((e) => setErr(String(e)));
  }, [habId]);

  if (err) return <div className="drawer"><button className="close" onClick={onClose}>×</button><div className="err">{err}</div></div>;
  if (!d) return <div className="drawer"><button className="close" onClick={onClose}>×</button><div className="spin">loading…</div></div>;

  const b = d.breakdown;
  const radar = [
    { k: "landslide", v: b.hazard.landslide ?? 0 },
    { k: "GLOF", v: b.hazard.glof ?? 0 },
    { k: "seismic", v: b.hazard.seismic ?? 0 },
    { k: "flood", v: b.hazard.flood ?? 0 },
    { k: "vuln.", v: b.svi ?? 0 },
    { k: "deficit", v: Math.min(1, (b.carrying_capacity.deficit_ratio ?? 0) / 2) },
  ];

  return (
    <div className="drawer">
      <button className="close" onClick={onClose}>×</button>
      <h1>{d.name}</h1>
      <div className="sub">{d.block} block · {d.district} district · pop {d.population?.toLocaleString("en-IN")} · {d.households} hh</div>

      <div style={{ height: 170, margin: "6px 0" }}>
        <ResponsiveContainer>
          <RadarChart data={radar} outerRadius={62}>
            <PolarGrid stroke="#313d4f" />
            <PolarAngleAxis dataKey="k" tick={{ fill: "#9fb0c3", fontSize: 10 }} />
            <PolarRadiusAxis domain={[0, 1]} tick={false} axisLine={false} />
            <Radar dataKey="v" stroke="#4aa3ff" fill="#4aa3ff" fillOpacity={0.35} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="kv"><span className="k">Priority tier</span><span className={`pill ${b.priority.tier}`}>{b.priority.tier?.replace("_", " ")}</span></div>
      <div className="kv"><span className="k">Priority score</span><span>{b.priority.score}</span></div>

      <h2>Hazard</h2>
      <div className="kv"><span className="k">Composite / tier</span><span>{b.hazard_composite} · {b.hazard_tier}</span></div>
      {Object.entries(b.hazard).map(([k, v]) => (
        <div className="kv" key={k}><span className="k">{k}</span><span>{v as any}</span></div>
      ))}

      <h2>Social vulnerability</h2>
      <div className="kv"><span className="k">SVI</span><span>{b.svi}</span></div>
      {Object.entries(b.svi_components).map(([k, v]) => (
        <div className="kv" key={k}><span className="k">{k}</span><span>{v as any}</span></div>
      ))}

      <h2>Carrying capacity</h2>
      <div className="kv"><span className="k">Sustainable / effective pop</span><span>{b.carrying_capacity.sustainable_pop?.toLocaleString("en-IN")} / {b.carrying_capacity.effective_pop?.toLocaleString("en-IN")}</span></div>
      <div className="kv"><span className="k">Deficit ratio</span><span>{b.carrying_capacity.deficit_ratio} ({b.carrying_capacity.status})</span></div>
      <div className="kv"><span className="k">Limiting factor</span><span>{b.carrying_capacity.limiting_factor}</span></div>
      <div className="kv"><span className="k">water / land / evac / services</span><span style={{ fontSize: 11 }}>
        {[b.carrying_capacity.water_pop, b.carrying_capacity.land_pop, b.carrying_capacity.evacuation_pop, b.carrying_capacity.services_pop].map((n) => n?.toLocaleString("en-IN")).join(" / ")}
      </span></div>

      <h2>Relocation & cost–benefit</h2>
      <div className="kv"><span className="k">Persons relocated</span><span>{b.relocation.persons_relocated?.toLocaleString("en-IN") ?? "—"}</span></div>
      <div className="kv"><span className="k">Expected annual loss</span><span>{crore(b.relocation.eal_inr)}/yr</span></div>
      <div className="kv"><span className="k">Relocation capex</span><span>{crore(b.relocation.relocation_capex_inr)}</span></div>
      <div className="kv"><span className="k">Benefit–cost ratio</span><span>{b.relocation.benefit_cost_ratio ?? "—"}</span></div>
      <div className="kv"><span className="k">Payback</span><span>{b.relocation.payback_years ?? "—"} yr</span></div>
    </div>
  );
}
