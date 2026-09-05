import { Link } from "react-router-dom";
import { Nav } from "../Nav";
import { useNirnay } from "../store";

export function Landing() {
  const { summary } = useNirnay();
  const w = summary?.hazard.weights;
  const before = 0.24; // AHP prior for GLOF, for the "moved from -> to" proof stat

  return (
    <div className="shell">
      <Nav />
      <div className="page">
        <div className="page-inner">
          <div className="hero">
            <div>
              <div className="eyebrow">Pre-disaster decision support &middot; District Disaster Management</div>
              <h1 className="h-display">From hazard data<br />to a decision.</h1>
              <p className="lede">
                NIRNAY turns a district&rsquo;s scattered hazard maps and census sheets into one
                ranked, capacity-checked, costed relocation plan &mdash; which habitations move
                first, where their people go, and whether it pays for itself.
              </p>
              <div className="btn-row">
                <Link className="btn-primary" to="/districts/mangan">
                  Open Mangan workspace
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
                </Link>
                <Link className="btn-secondary" to="/districts">Select a district</Link>
              </div>
            </div>

            <div style={{ position: "relative", border: "1px solid var(--line)", borderRadius: 6, background: "var(--panel)", overflow: "hidden", height: 340 }}>
              <svg width="100%" height="340" viewBox="0 0 560 340" preserveAspectRatio="xMidYMid slice" style={{ display: "block" }}>
                <path d="M0,120 L0,340 L560,340 L560,90 C480,120 430,70 380,105 C330,140 300,80 250,115 C200,150 160,90 100,120 C60,140 30,125 0,120 Z" fill="color-mix(in oklch, var(--geo) 12%, var(--panel))" />
                <path d="M0,180 L0,340 L560,340 L560,155 C500,190 460,140 410,175 C360,210 320,150 270,185 C220,220 180,165 130,190 C80,212 40,198 0,180 Z" fill="color-mix(in oklch, var(--accent) 12%, var(--panel))" />
                <path d="M120,15 C160,70 100,120 150,175 C200,230 140,280 190,320" fill="none" stroke="var(--geo)" strokeWidth="3" strokeLinecap="round" />
                <circle cx="150" cy="175" r="7" fill="var(--red)" stroke="var(--panel)" strokeWidth="2.5" />
                <circle cx="190" cy="316" r="5" fill="var(--green)" stroke="var(--panel)" strokeWidth="2" />
              </svg>
              <div style={{ position: "absolute", left: 158, top: 160, background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 3, padding: "3px 8px", fontFamily: "IBM Plex Mono", fontSize: 11, whiteSpace: "nowrap" }}>
                Chungthang &middot; relocate now
              </div>
              <div style={{ position: "absolute", right: 12, bottom: 10, fontFamily: "IBM Plex Mono", fontSize: 10.5, color: "var(--ink-dim)" }}>27.60&deg;N &middot; 88.64&deg;E</div>
              <div style={{ position: "absolute", left: 12, bottom: 10, fontFamily: "IBM Plex Mono", fontSize: 10.5, color: "var(--ink-dim)" }}>Teesta corridor, Mangan DDMA</div>
            </div>
          </div>

          <div className="proof-band">
            <div>
              <div className="proof-num">{summary?.counts.habitations ?? "28"}</div>
              <div className="proof-cap">habitations assessed &mdash; Mangan DDMA, Teesta corridor</div>
            </div>
            <div>
              <div className="proof-num">{before.toFixed(2)} &rarr; {w ? w.glof.toFixed(2) : "0.49"}</div>
              <div className="proof-cap">GLOF hazard weight, recalibrated against loss history since Oct 2023</div>
            </div>
            <div>
              <div className="proof-num">{summary?.relocation.portfolio_benefit_cost_ratio ?? "1.23"}&times;</div>
              <div className="proof-cap">portfolio benefit&ndash;cost ratio on the current relocation plan</div>
            </div>
          </div>

          <div className="eyebrow" style={{ marginTop: 40 }}>How it works</div>
          <h2 style={{ fontFamily: "Newsreader, Georgia, serif", fontSize: 26, fontWeight: 600, color: "var(--ink)", border: "none", margin: "0 0 8px", padding: 0, textTransform: "none", letterSpacing: 0 }}>
            Four phases, one pipeline.
          </h2>
          <div className="phase-strip">
            <div className="phase-step">
              <div className="phase-num">1</div>
              <div className="phase-title">Identify red zones</div>
              <div className="phase-desc">Composite hazard from landslide, GLOF, seismic and flood layers &mdash; calibrated against the district&rsquo;s own loss history.</div>
            </div>
            <div className="phase-connector" />
            <div className="phase-step">
              <div className="phase-num">2</div>
              <div className="phase-title">Assess carrying capacity</div>
              <div className="phase-desc">Water, land, evacuation roads and services vs. current and projected population.</div>
            </div>
            <div className="phase-connector" />
            <div className="phase-step">
              <div className="phase-num">3</div>
              <div className="phase-title">Prioritise &amp; match</div>
              <div className="phase-desc">Hazard &times; vulnerability &times; deficit ranks every habitation, then an optimiser matches it to a safe site.</div>
            </div>
            <div className="phase-connector" />
            <div className="phase-step">
              <div className="phase-num accent">4</div>
              <div className="phase-title">Relocate &amp; report</div>
              <div className="phase-desc">A phased, costed plan with payback and benefit&ndash;cost ratio &mdash; exportable in the DDMA funding format.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
