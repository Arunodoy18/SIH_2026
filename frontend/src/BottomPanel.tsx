import { crore, num } from "./api";
import type { RelocationPlan } from "./types";

export function BottomPanel({
  plan, selected, onSelect,
}: {
  plan: RelocationPlan | null;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  if (!plan) return <div className="bottom spin">loading plan…</div>;

  return (
    <div className="bottom">
      <div style={{ display: "flex", gap: 24, alignItems: "baseline", marginBottom: 8 }}>
        <b>Ranked relocation plan</b>
        {plan.phases.map((p) => (
          <span key={p.phase} style={{ color: "var(--ink-dim)" }}>
            {p.label}: <b style={{ color: "var(--ink)" }}>{p.habitations}</b> habitations ·{" "}
            {num(p.persons_to_move)} people · {crore(p.capex_inr)}
            {p.persons_unmet ? ` · ${num(p.persons_unmet)} unmet` : ""}
          </span>
        ))}
        <span style={{ color: "var(--ink-dim)", marginLeft: "auto" }}>
          solver: {plan.solver} · {plan.split_habitations} split across sites
        </span>
      </div>

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
            <tr key={r.hab_id} className={selected === r.hab_id ? "sel" : ""} onClick={() => onSelect(r.hab_id)}>
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
  );
}
