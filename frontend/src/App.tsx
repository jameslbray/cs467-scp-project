// App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import ChatPage from './pages/ChatPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AuthenticatedLayout from './layouts/AuthenticatedLayout';
import { ThemeProvider, AuthProvider } from './contexts';
import ErrorBoundary from './components/ErrorBoundary';

// Define types for our context and props
export interface User {
  id: string;
  username: string;
  profilePicture?: string;
}

export interface UserStatus {
  user_id: string;
  status: 'online' | 'away' | 'offline';
  last_changed: string;
}

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <Router>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />

              {/* Protected routes */}
              <Route element={<AuthenticatedLayout />}>
                <Route path="/chat" element={<ChatPage />} />
              </Route>
            </Routes>
          </Router>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;
