import React from "react";
import type { ReactNode, ErrorInfo } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  // Update state so the next render will show the fallback UI.
  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  // Log the error to an error reporting service
  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("ErrorBoundary caught an error", error, errorInfo);
  }

  render(): ReactNode {
		if (this.state.hasError) {
			// Render any custom fallback UI
			return (
				<h1>
					Something went wrong. Check the console logs for any errors
				</h1>
			);
		}
		// Render the children components
		return this.props.children;
  }
}

export default ErrorBoundary;
