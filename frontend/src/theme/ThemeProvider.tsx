import {
  type PropsWithChildren,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
} from "react";

import { useAuth } from "../auth/AuthContext";
import { updateThemePreferences } from "../lib/preferences-api";
import type {
  ThemePreferences,
  ThemePreferenceUpdate,
} from "../types/theme";
import { ThemeContext } from "./ThemeContext";

const DEFAULT_PREFERENCES: ThemePreferences = {
  theme_mode: "light",
  color_palette: "default",
  updated_at: null,
};

function systemUsesDarkMode(): boolean {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

interface UserThemeState {
  userId: string;
  preferences: ThemePreferences;
}

export function ThemeProvider({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const [userTheme, setUserTheme] = useState<UserThemeState | null>(null);
  const [systemDark, setSystemDark] = useState(systemUsesDarkMode);

  const preferences = user === null
    ? DEFAULT_PREFERENCES
    : userTheme?.userId === user.id
      ? userTheme.preferences
      : user.preferences;

  const resolvedMode =
    preferences.theme_mode === "system"
      ? systemDark
        ? "dark"
        : "light"
      : preferences.theme_mode;

  useEffect(() => {
    const mediaQuery = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (mediaQuery === undefined) return;

    const updateSystemMode = (event: MediaQueryListEvent) => setSystemDark(event.matches);
    mediaQuery.addEventListener?.("change", updateSystemMode);
    return () => mediaQuery.removeEventListener?.("change", updateSystemMode);
  }, []);

  useLayoutEffect(() => {
    const root = document.documentElement;
    root.dataset.mode = resolvedMode;
    root.dataset.themeMode = preferences.theme_mode;
    root.dataset.palette = preferences.color_palette;
    root.style.colorScheme = resolvedMode;

    const themeColor = getComputedStyle(root).getPropertyValue("--page-bg").trim()
      || (resolvedMode === "dark" ? "#101716" : "#eff7f5");
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", themeColor);
  }, [preferences, resolvedMode]);

  const updatePreferences = useCallback(
    async (update: ThemePreferenceUpdate) => {
      if (user === null) {
        throw new Error("Tema tercihini değiştirmek için oturum açmalısınız.");
      }

      const previous = preferences;
      const optimistic = { ...previous, ...update };
      setUserTheme({ userId: user.id, preferences: optimistic });

      try {
        const saved = await updateThemePreferences(update);
        setUserTheme({ userId: user.id, preferences: saved });
      } catch (error) {
        setUserTheme({ userId: user.id, preferences: previous });
        throw error;
      }
    },
    [preferences, user],
  );

  const value = useMemo(
    () => ({ preferences, resolvedMode, updatePreferences }),
    [preferences, resolvedMode, updatePreferences],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
