import React, { useCallback, useEffect, useState } from 'react';
import { ThemeContext } from './useTheme';

const getInitialDarkMode = (): boolean => {
	// Check if we're in a browser environment
	if (typeof window === 'undefined') {
		return false;
	}

	// Check localStorage first
	const stored = localStorage.getItem('darkMode');
	if (stored !== null) {
		return stored === 'true';
	}

	// Fall back to system preference
	return window.matchMedia('(prefers-color-scheme: dark)').matches;
};

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
	const [darkMode, setDarkMode] = useState<boolean>(getInitialDarkMode);

	useEffect(() => {
		if (typeof window !== 'undefined') {
			const root = window.document.documentElement;
			if (darkMode) {
				root.classList.add('dark');
			} else {
				root.classList.remove('dark');
			}
		}
	}, [darkMode]);

	const toggleDarkMode = useCallback(() => {
		setDarkMode((prev) => {
			const newValue = !prev;
			if (typeof window !== 'undefined') {
				localStorage.setItem('darkMode', String(newValue));
			}
			return newValue;
		});
	}, []);

	// ... rest of the code remains unchanged ...
	const value = React.useMemo(
		() => ({
			darkMode,
			toggleDarkMode,
		}),
		[darkMode, toggleDarkMode]
	);

	return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};
