import { Component, type ErrorInfo, type ReactNode } from "react";

/** Keeps one failing panel (e.g. the WebGL map) from blanking the whole dashboard. */
export class ErrorBoundary extends Component<
  { children: ReactNode; label: string },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[${this.props.label}]`, error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", padding: 24 }}>
          <div style={{ maxWidth: 420, textAlign: "center", color: "var(--ink-dim)" }}>
            <div style={{ fontWeight: 700, color: "var(--ink)", marginBottom: 6 }}>
              {this.props.label} unavailable
            </div>
            <div style={{ fontSize: 12 }}>{String(this.state.error.message || this.state.error)}</div>
            <div style={{ fontSize: 12, marginTop: 8 }}>
              The rest of the dashboard still works — tables and the habitation drawer are unaffected.
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
