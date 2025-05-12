// App.tsx
import type React from "react";
import { Route, BrowserRouter as Router, Routes } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary";
import { AuthProvider, ThemeProvider } from "./contexts";
import { SocketProvider } from "./contexts/socket";
import AuthenticatedLayout from "./layouts/AuthenticatedLayout";
import ChatPage from "./pages/ChatPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

// Define types for our context and props
export interface User {
	id: string;
	username: string;
	profilePicture?: string;
}

export interface UserStatusIntf {
	user_id: string;
	status: "online" | "away" | "offline";
	last_changed: string;
}

const App: React.FC = () => {
	return (
		<ErrorBoundary>
			<ThemeProvider>
				<AuthProvider>
					<SocketProvider>
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
					</SocketProvider>
				</AuthProvider>
			</ThemeProvider>
		</ErrorBoundary>
	);
};

export default App;
