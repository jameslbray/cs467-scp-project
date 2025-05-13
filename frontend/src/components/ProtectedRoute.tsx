import type React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../contexts";

interface ProtectedRouteProps {
	redirectPath?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
	redirectPath = "/login",
}) => {
	const { isAuthenticated, isLoading } = useAuth();

	if (isLoading) {
		return (
			<div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
				<div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500" />
			</div>
		);
	}

	if (!isAuthenticated) {
		return <Navigate to={redirectPath} replace />;
	}

	return <Outlet />;
};

export default ProtectedRoute;
