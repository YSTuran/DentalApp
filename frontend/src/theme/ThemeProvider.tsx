import {
  type PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useAuth } from "../auth/AuthContext";
import { updateThemePreferences } from "../lib/preferences-api";
import type {
  ThemeMode,
  ThemePreferences,
  ThemePreferenceUpdate,
} from "../types/theme";
import { ThemeContext } from "./ThemeContext";
import { COLOR_PALETTE_VALUES, THEME_MODE_VALUES } from "./options";

const MODE_STORAGE_KEY = "dentalapp.theme_mode";
const PALETTE_STORAGE_KEY = "dentalapp.color_palette";
const DEFAULT_PREFERENCES: ThemePreferences = {
  theme_mode: "system",
  color_palette: "default",
  updated_at: null,
};

function isThemeMode(value: string | null): value is ThemeMode {
  return value !== null && THEME_MODE_VALUES.some((mode) => mode === value);
}

function isColorPalette(
  value: string | null,
): value is ThemePreferences["color_palette"] {
  return value !== null && COLOR_PALETTE_VALUES.some((palette) => palette === value);
}

function readStoredPreferences(): ThemePreferences {
  try {
    const storedMode = window.localStorage.getItem(MODE_STORAGE_KEY);
    const storedPalette = window.localStorage.getItem(PALETTE_STORAGE_KEY);
    return {
      theme_mode: isThemeMode(storedMode) ? storedMode : DEFAULT_PREFERENCES.theme_mode,
      color_palette: isColorPalette(storedPalette)
        ? storedPalette
        : DEFAULT_PREFERENCES.color_palette,
      updated_at: null,
    };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

function storePreferences(preferences: ThemePreferences): void {
  try {
    window.localStorage.setItem(MODE_STORAGE_KEY, preferences.theme_mode);
    window.localStorage.setItem(PALETTE_STORAGE_KEY, preferences.color_palette);
  } catch {
    // The active page still keeps the selected theme when storage is unavailable.
  }
}

function systemUsesDarkMode(): boolean {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

export function ThemeProvider({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const [preferences, setPreferences] = useState(readStoredPreferences);
  const [systemDark, setSystemDark] = useState(systemUsesDarkMode);
  const accountUserId = user?.id;
  const accountThemeMode = user?.preferences.theme_mode;
  const accountColorPalette = user?.preferences.color_palette;
  const accountPreferencesUpdatedAt = user?.preferences.updated_at ?? null;

  const resolvedMode =
    preferences.theme_mode === "system"
      ? systemDark
        ? "dark"
        : "light"
      : preferences.theme_mode;

  useEffect(() => {
    if (
      accountUserId === undefined ||
      accountThemeMode === undefined ||
      accountColorPalette === undefined
    ) {
      return;
    }
    const accountPreferences: ThemePreferences = {
      theme_mode: accountThemeMode,
      color_palette: accountColorPalette,
      updated_at: accountPreferencesUpdatedAt,
    };
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      setPreferences(accountPreferences);
      storePreferences(accountPreferences);
    });
    return () => {
      active = false;
    };
  }, [
    accountColorPalette,
    accountPreferencesUpdatedAt,
    accountThemeMode,
    accountUserId,
  ]);

  useEffect(() => {
    const mediaQuery = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (mediaQuery === undefined) return;

    const updateSystemMode = (event: MediaQueryListEvent) => setSystemDark(event.matches);
    mediaQuery.addEventListener?.("change", updateSystemMode);
    return () => mediaQuery.removeEventListener?.("change", updateSystemMode);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.mode = resolvedMode;
    root.dataset.themeMode = preferences.theme_mode;
    root.dataset.palette = preferences.color_palette;
    root.style.colorScheme = resolvedMode;
    storePreferences(preferences);

    const themeColor = getComputedStyle(root).getPropertyValue("--page-bg").trim()
      || (resolvedMode === "dark" ? "#101716" : "#eff7f5");
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", themeColor);
  }, [preferences, resolvedMode]);

  const updatePreferences = useCallback(
    async (update: ThemePreferenceUpdate) => {
      const previous = preferences;
      const optimistic = { ...previous, ...update };
      setPreferences(optimistic);
      storePreferences(optimistic);

      if (user === null) return;

      try {
        const saved = await updateThemePreferences(update);
        setPreferences(saved);
        storePreferences(saved);
      } catch (error) {
        setPreferences(previous);
        storePreferences(previous);
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
