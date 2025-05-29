import { createContext, useContext } from 'react';
import type { User } from '../../types/userType';

interface AuthContextType {
	user: User | null;
	token: string | null;
	isAuthenticated: boolean;
	isLoading: boolean;
	login: (username: string, password: string) => Promise<boolean>;
	logout: () => void;
	register: (
		username: string,
		password: string,
		email: string,
	) => Promise<boolean>;
}
const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
	const context = useContext(AuthContext);
	if (!context) {
		throw new Error('useAuth must be used within an AuthProvider');
	}
	return context;
};

export { AuthContext };
