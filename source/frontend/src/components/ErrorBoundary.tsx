import { Component, type ErrorInfo, type ReactNode } from "react";
import Button from "./Button";

type Props = { children: ReactNode };
type State = { error: Error | null };

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("UI error:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error-boundary panel" role="alert">
          <h1>Something went wrong</h1>
          <p>{this.state.error.message || "An unexpected error occurred."}</p>
          <Button variant="primary" onClick={() => window.location.reload()}>
            Reload page
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
