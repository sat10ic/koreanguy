import { Component, type ErrorInfo, type ReactNode } from "react";

/*
  F-2: error boundary — one malformed field must degrade a PANEL, not blank
  a SCREEN. Pattern adopted from traderlog/ui/src/components/
  PanelErrorBoundary.jsx (same repo convention), upgraded to TypeScript and
  a diagnostic fallback: it names the panel, shows the error message, and
  offers a reload — this is a tool you debug yourself, so the fallback is a
  diagnostic, not an apology.
*/

interface Props {
  children: ReactNode;
  /** Human name of the guarded panel — shown in the fallback. */
  name: string;
}

interface State {
  error: Error | null;
}

export class PanelBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[unidesk] panel "${this.props.name}" failed:`, error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="rounded-card border border-danger-border bg-danger-bg px-3.5 py-3" role="alert" data-testid="panel-error-boundary">
          <div className="text-caption font-semibold text-danger">Panel unavailable: {this.props.name}</div>
          <div className="mt-1 break-words font-mono-num text-caption text-ink-secondary">
            {this.state.error.message || "rendering failed"}
          </div>
          <button
            onClick={() => this.setState({ error: null })}
            className="mt-2 rounded-chip border border-border px-2.5 py-1 text-caption font-medium text-ink-secondary hover:bg-surface-2"
          >
            Retry panel
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

/** Route-level wrapper: same boundary, screen-sized. */
export function RouteBoundary({ children }: { children: ReactNode }) {
  return (
    <PanelBoundary name="this screen">
      {children}
    </PanelBoundary>
  );
}
