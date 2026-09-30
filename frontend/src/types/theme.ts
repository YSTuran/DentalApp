export type ThemeMode = "light" | "dark" | "system";
export type ColorPalette =
  | "default"
  | "ocean"
  | "violet"
  | "arctic"
  | "sage"
  | "graphite"
  | "amber"
  | "burgundy"
  | "coral"
  | "sepia"
  | "high_contrast";

export interface ThemePreferences {
  theme_mode: ThemeMode;
  color_palette: ColorPalette;
  updated_at: string | null;
}

export type ThemePreferenceUpdate = Partial<
  Pick<ThemePreferences, "theme_mode" | "color_palette">
>;
