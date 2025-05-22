import type { ErrorInfo, ReactElement, ReactNode } from 'react';
import React from 'react';

interface ErrorBoundaryProps {
	children: ReactElement;
	onError?: (error: Error) => void; // Optional to maintain backward compatibility
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
		// Call the onError prop if provided (for Lexical)
		if (this.props.onError) {
			this.props.onError(error);
		}

		// Always log to console for debugging
		console.error('ErrorBoundary caught an error:', error, errorInfo);
	}

	render(): ReactNode {
		if (this.state.hasError) {
			return (
				<div className='p-4 text-red-600 bg-red-50 rounded-md'>
					<h3 className='font-semibold'>Something went wrong</h3>
					<p className='text-sm mt-1'>Please try again or refresh the page</p>
				</div>
			);
		}
		// Render the children components
		return this.props.children;
	}
}

export default ErrorBoundary;
