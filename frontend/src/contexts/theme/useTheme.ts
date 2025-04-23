import { createContext, useContext } from 'react';

type ThemeContextType = {
  darkMode: boolean;
  toggleDarkMode: () => void;
};

const defaultContext: ThemeContextType = {
  darkMode: false,
  toggleDarkMode: () => {},
};

export const ThemeContext = createContext<ThemeContextType>(defaultContext);

export const useTheme = () => useContext(ThemeContext); 