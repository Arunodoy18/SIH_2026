import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Nav } from "../Nav";
import { ReportModal } from "../ReportModal";
import { useNirnay } from "../store";
import { crore, num } from "../api";

export function PlanPage() {
  const { plan, summary, narrative, narrativeBusy, narrativeError, generateReport } = useNirnay();
  const [reportOpen, setReportOpen] = useState(false);
  const navigate = useNavigate();

  if (!plan) {
    return (
      <div className="shell"><Nav /><div className="page"><div className="page-inner spin">loading plan…</div></div></div>
    );
  }

  const t = plan.totals;

  return (
    <div className="shell">
      <Nav />
      <div className="page">
        <div className="page-inner">
          <div className="breadcrumb">
            <Link to="/">NIRNAY</Link> &nbsp;/&nbsp; <Link to="/districts">Districts</Link> &nbsp;/&nbsp;
            <Link to="/districts/mangan"> Mangan DDMA</Link> &nbsp;/&nbsp; <span className="cur">Relocation plan</span>
          </div>

          <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 22 }}>
            <div>
              <h1 style={{ fontFamily: "Newsreader, Georgia, serif", fontSize: 28, fontWeight: 600, margin: 0 }}>Relocation plan</h1>
              <div style={{ fontFamily: "IBM Plex Mono", fontSize: 12, color: "var(--ink-dim)", marginTop: 6 }}>
                {summary?.aoi} &middot; solver {plan.solver} &middot; {plan.split_habitations} split across sites
              </div>
            </div>
            <button onClick={() => { setReportOpen(true); generateReport(); }} disabled={narrativeBusy}>
              {narrativeBusy ? "Drafting…" : "Generate DDMA report"}
            </button>
          </div>

          <div className="grid-cards cols-4" style={{ marginBottom: 24 }}>
            <div className="card"><div className="k" style={{ fontFamily: "IBM Plex Mono", fontSize: 10.5, color: "var(--ink-dim)", textTransform: "uppercase" }}>People to move</div><div style={{ fontFamily: "IBM Plex Mono", fontSize: 26, fontWeight: 600, marginTop: 8 }}>{num(t.persons_moved)}</div></div>
            <div className="card"><div className="k" style={{ fontFamily: "IBM Plex Mono", fontSize: 10.5, color: "var(--ink-dim)", textTransform: "uppercase" }}>Relocation capex</div><div style={{ fontFamily: "IBM Plex Mono", fontSize: 26, fontWeight: 600, marginTop: 8 }}>{crore(t.total_relocation_capex_inr)}</div></div>
            <div className="card"><div className="k" style={{ fontFamily: "IBM Plex Mono", fontSize: 10.5, color: "var(--ink-dim)", textTransform: "uppercase" }}>Portfolio BCR</div><div style={{ fontFamily: "IBM Plex Mono", fontSize: 26, fontWeight: 600, marginTop: 8, color: "var(--green)" }}>{t.portfolio_benefit_cost_ratio}&times;</div></div>
            <div className="card"><div className="k" style={{ fontFamily: "IBM Plex Mono", fontSize: 10.5, color: "var(--ink-dim)", textTransform: "uppercase" }}>Payback</div><div style={{ fontFamily: "IBM Plex Mono", fontSize: 26, fontWeight: 600, marginTop: 8 }}>{t.portfolio_payback_years} yr</div></div>
          </div>

          <div style={{ display: "flex", gap: 24, alignItems: "baseline", marginBottom: 10, fontSize: 13 }}>
            {plan.phases.map((p) => (
              <span key={p.phase} style={{ color: "var(--ink-dim)" }}>
                <b style={{ color: "var(--ink)" }}>{p.label}</b>: {p.habitations} habitations &middot; {num(p.persons_to_move)} people &middot; {crore(p.capex_inr)}
                {p.persons_unmet ? ` · ${num(p.persons_unmet)} unmet` : ""}
              </span>
            ))}
          </div>

          <div className="tablewrap" style={{ overflowX: "auto", border: "1px solid var(--line)", borderRadius: 6 }}>
            <table>
              <thead>
                <tr>
                  <th>Habitation</th><th>Tier</th><th>Ph</th><th>Score</th><th>Haz</th><th>SVI</th>
                  <th>Deficit</th><th>People</th><th>Destination</th><th>km</th><th>Capex</th>
                  <th>EAL/yr</th><th>BCR</th><th>Payback</th>
                </tr>
              </thead>
              <tbody>
                {plan.ranked.map((r) => (
                  <tr key={r.hab_id} onClick={() => navigate(`/districts/mangan/habitations/${r.hab_id}`)}>
                    <td>{r.habitation}</td>
                    <td><span className={`pill ${r.priority_tier}`}>{r.priority_tier.replace("_", " ")}</span></td>
                    <td>{r.phase}</td>
                    <td>{r.priority_score?.toFixed(2)}</td>
                    <td>{r.haz_composite?.toFixed(2)}</td>
                    <td>{r.svi?.toFixed(2)}</td>
                    <td>{r.cc_deficit_ratio?.toFixed(2)}</td>
                    <td>{num(r.persons_to_move)}{r.persons_unmet ? ` (−${num(r.persons_unmet)})` : ""}</td>
                    <td style={{ textAlign: "left", maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis" }}>{r.destination ?? "—"}</td>
                    <td>{r.nearest_distance_km ?? "—"}</td>
                    <td>{crore(r.relocation_capex_inr)}</td>
                    <td>{crore(r.eal_inr)}</td>
                    <td style={{ color: (r.benefit_cost_ratio ?? 0) >= 1 ? "var(--green)" : "var(--ink-dim)" }}>{r.benefit_cost_ratio ?? "—"}</td>
                    <td>{r.payback_years ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {reportOpen && (
        <ReportModal data={narrative} busy={narrativeBusy} error={narrativeError} onClose={() => setReportOpen(false)} />
      )}
    </div>
  );
}
