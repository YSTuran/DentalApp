import { createContext, useContext } from "react";

import type {
  ThemeMode,
  ThemePreferences,
  ThemePreferenceUpdate,
} from "../types/theme";

export interface ThemeContextValue {
  preferences: ThemePreferences;
  resolvedMode: Exclude<ThemeMode, "system">;
  updatePreferences: (update: ThemePreferenceUpdate) => Promise<void>;
}

export const ThemeContext = createContext<ThemeContextValue | null>(null);

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (context === null) {
    throw new Error("useTheme yalnızca ThemeProvider içinde kullanılabilir.");
  }
  return context;
}
