import type React from "react";
import { type ReactNode, useEffect, useState } from "react";
import type { User } from "../../App";
import { authApi } from "../../services/api";
import { AuthContext } from "./authContext";


interface AuthProviderProps {
	children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
	const [user, setUser] = useState<User | null>(null);
	const [token, setToken] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState<boolean>(true);


	// Check for existing token on mount
	useEffect(() => {
		const storedToken = localStorage.getItem("auth_token");
		if (storedToken) {
			setToken(storedToken);
			// Validate token and fetch user data
			validateToken(storedToken);
		} else {
			setIsLoading(false);
		}
	}, []);

	const validateToken = async (tokenToValidate: string) => {
		try {
			const userData = await authApi.validateToken(tokenToValidate);
			setUser(userData);
		} catch (error) {
			console.error("Error validating token:", error);
			localStorage.removeItem("auth_token");
			setToken(null);
		} finally {
			setIsLoading(false);
		}
	};

	const login = async (
		username: string,
		password: string,
	): Promise<boolean> => {
		setIsLoading(true);
		try {
			const data = await authApi.login(username, password);
			const newToken = data.access_token;
			setToken(newToken);
			localStorage.setItem("auth_token", newToken);

			// Get user data using the new token
			const userData = await authApi.validateToken(newToken);
			setUser(userData);

			return true;
		} catch (error) {
			console.error("Login error:", error);
			return false;
		} finally {
			setIsLoading(false);
		}
	};

	const register = async (
		username: string,
		password: string,
		email: string,
	): Promise<boolean> => {
		setIsLoading(true);
		try {
			const data = await authApi.register(username, password, email);
			setToken(data.token);
			setUser(data.user);
			localStorage.setItem("auth_token", data.token);
			return true;
		} catch (error) {
			console.error("Registration error:", error);
			return false;
		} finally {
			setIsLoading(false);
		}
	};

	const logout = async () => {
		// Revoke token on the server
		if (token) {
			try {
				await authApi.logout();
			} catch (error) {
				console.error("Error during logout:", error);
			}
		}

		// Clear local state
		localStorage.removeItem("auth_token");
		setToken(null);
		setUser(null);
	};

	const value = {
		user,
		token,
		isAuthenticated: !!token,
		isLoading,
		login,
		logout,
		register,
	};

	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
