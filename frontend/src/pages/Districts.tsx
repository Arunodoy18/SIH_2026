import { Link } from "react-router-dom";
import { Nav } from "../Nav";
import { useNirnay } from "../store";
import { num } from "../api";

const COMING_SOON = [
  { name: "Wayanad", region: "Kerala &middot; landslide + flood" },
  { name: "Kendrapara", region: "Odisha &middot; cyclone + surge" },
  { name: "Dhemaji", region: "Assam &middot; flood + erosion" },
];

export function Districts() {
  const { summary } = useNirnay();

  return (
    <div className="shell">
      <Nav />
      <div className="page">
        <div className="page-inner">
          <div className="breadcrumb"><Link to="/">NIRNAY</Link> &nbsp;/&nbsp; <span className="cur">Districts</span></div>
          <h1 style={{ fontFamily: "Newsreader, Georgia, serif", fontSize: 30, fontWeight: 600, margin: "0 0 8px" }}>
            Select a district workspace
          </h1>
          <p style={{ color: "var(--ink-dim)", fontSize: 13.5, maxWidth: "60ch", margin: "0 0 32px" }}>
            One analysis pipeline, run per district. Live workspaces use the district&rsquo;s own hazard,
            census and destination-site data.
          </p>

          <div className="grid-cards cols-4">
            <Link to="/districts/mangan" className="district-card">
              <div className="district-thumb">
                <span className="district-status live">Live</span>
              </div>
              <div className="district-body">
                <div style={{ fontFamily: "Newsreader, Georgia, serif", fontSize: 18, fontWeight: 600 }}>Mangan DDMA</div>
                <div style={{ fontSize: 12, color: "var(--ink-dim)", marginTop: 2 }}>Sikkim &middot; Teesta corridor</div>
                <div style={{ fontFamily: "IBM Plex Mono", fontSize: 11.5, color: "var(--ink-dim)", marginTop: 12 }}>
                  {summary ? `${summary.counts.habitations} habitations · pop. ${num(summary.counts.population)}` : "loading…"}
                </div>
              </div>
            </Link>

            {COMING_SOON.map((d) => (
              <div key={d.name} className="district-card disabled">
                <div className="district-thumb">
                  <span className="district-status soon">Coming soon</span>
                </div>
                <div className="district-body">
                  <div style={{ fontFamily: "Newsreader, Georgia, serif", fontSize: 18, fontWeight: 600, color: "var(--ink-dim)" }}>{d.name}</div>
                  <div style={{ fontSize: 12, color: "var(--ink-dim)", marginTop: 2 }} dangerouslySetInnerHTML={{ __html: d.region }} />
                  <div style={{ fontFamily: "IBM Plex Mono", fontSize: 11.5, color: "var(--ink-dim)", marginTop: 12 }}>data pack in acquisition</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
