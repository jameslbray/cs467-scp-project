import React, { useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth, useTheme } from '../contexts';

const LandingPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const { darkMode } = useTheme();
  const navigate = useNavigate();

  useEffect(() => {
    // Only redirect if user is already authenticated
    if (!isLoading && isAuthenticated) {
      navigate('/chat');
    }
  }, [isAuthenticated, isLoading, navigate]);

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-center min-h-screen py-12">
          <div className="text-center">
            <h1 className={`text-4xl font-extrabold tracking-tight sm:text-5xl md:text-6xl ${
              darkMode ? 'text-white' : 'text-gray-900'
            }`}>
              Welcome to SycoLibre Chat
            </h1>
            <p className={`mt-3 max-w-md mx-auto text-base sm:text-lg md:mt-5 md:text-xl ${
              darkMode ? 'text-gray-300' : 'text-gray-500'
            }`}>
              A secure, decentralized chat platform for the modern world.
            </p>
            <div className="mt-5 max-w-md mx-auto sm:flex sm:justify-center md:mt-8">
              <div className="rounded-md shadow">
                <Link
                  to="/login"
                  className={`w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 md:py-4 md:text-lg md:px-10`}
                >
                  Sign In
                </Link>
              </div>
              <div className="mt-3 rounded-md shadow sm:mt-0 sm:ml-3">
                <Link
                  to="/register"
                  className={`w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md ${
                    darkMode 
                      ? 'text-primary-600 bg-gray-800 hover:bg-gray-700' 
                      : 'text-primary-600 bg-white hover:bg-gray-50'
                  } md:py-4 md:text-lg md:px-10`}
                >
                  Create Account
                </Link>
              </div>
            </div>
          </div>

          {/* Features Section */}
          <div id="features" className="mt-32">
            <h2 className={`text-3xl font-extrabold text-center ${
              darkMode ? 'text-white' : 'text-gray-900'
            }`}>
              Features
            </h2>
            <div className="mt-12 grid gap-8 grid-cols-1 md:grid-cols-3">
              {[
                {
                  title: 'Secure Communication',
                  description: 'End-to-end encryption for all your messages'
                },
                {
                  title: 'Real-time Updates',
                  description: 'Instant message delivery and status updates'
                },
                {
                  title: 'User Status',
                  description: 'See when your friends are online and available'
                }
              ].map((feature, index) => (
                <div
                  key={index}
                  className={`p-6 rounded-lg ${
                    darkMode ? 'bg-gray-800' : 'bg-white'
                  } shadow-lg`}
                >
                  <h3 className={`text-xl font-semibold ${
                    darkMode ? 'text-white' : 'text-gray-900'
                  }`}>
                    {feature.title}
                  </h3>
                  <p className={`mt-2 ${
                    darkMode ? 'text-gray-300' : 'text-gray-500'
                  }`}>
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingPage; 