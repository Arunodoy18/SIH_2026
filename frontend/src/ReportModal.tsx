import type { Narrative } from "./api";

export function ReportModal({
  data, busy, error, onClose,
}: {
  data: Narrative | null;
  busy: boolean;
  error: string | null;
  onClose: () => void;
}) {
  return (
    <div
      style={{
        position: "fixed", inset: 0, background: "rgba(6,9,13,.6)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 60,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 12,
          padding: 26, width: "min(640px, 92vw)", maxHeight: "82vh", overflowY: "auto",
          boxShadow: "0 24px 70px rgba(0,0,0,.55)", position: "relative",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button className="close" style={{ position: "absolute", top: 14, right: 16 }} onClick={onClose}>×</button>
        <h1 style={{ marginBottom: 4 }}>DDMA Report — Narrative</h1>

        {busy && <div className="spin">Drafting…</div>}
        {error && <div className="err">{error}</div>}

        {data && !busy && (
          <>
            <div
              className="sub"
              style={{ display: "flex", alignItems: "center", gap: 8, margin: "6px 0 18px" }}
            >
              {data.mode === "ai" ? (
                <>
                  <span
                    style={{
                      background: "rgba(63,143,86,.14)", color: "var(--green)",
                      border: "1px solid rgba(63,143,86,.35)", borderRadius: 999,
                      padding: "2px 10px", fontSize: 11, fontWeight: 700, letterSpacing: ".03em",
                    }}
                  >
                    AI-DRAFTED
                  </span>
                  <span>{data.provider} · {data.model}</span>
                </>
              ) : (
                <span
                  style={{
                    background: "var(--panel-2)", color: "var(--ink-dim)",
                    border: "1px solid var(--line)", borderRadius: 999,
                    padding: "2px 10px", fontSize: 11, fontWeight: 700, letterSpacing: ".03em",
                  }}
                >
                  TEMPLATE — no AI provider configured
                </span>
              )}
            </div>
            <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.7, fontSize: 13.5 }}>
              {data.text}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
