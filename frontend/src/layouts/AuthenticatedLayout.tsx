import type React from "react";
import { Navigate, Outlet } from "react-router-dom";
import DarkModeToggle from "../components/DarkModeToggle";
import { useAuth } from "../contexts";

const AuthenticatedLayout: React.FC = () => {
  const { isAuthenticated, isLoading, logout } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              SycoLibre
            </h1>
            <div className="flex items-center space-x-4">
              <DarkModeToggle />
              {/* Add other header items here (profile, logout, etc.) */}
            </div>

            {/* Logout button */}
            <button
              type='button'
              onClick={logout}
              className='ml-4 px-3 py-1 text-sm text-white bg-red-600 hover:bg-red-700 rounded-md focus:outline-none'
            >
              Logout
            </button>

          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
};

export default AuthenticatedLayout;