import { csrfRequest } from "./api";
import type { ThemePreferences, ThemePreferenceUpdate } from "../types/theme";

export function updateThemePreferences(
  preferences: ThemePreferenceUpdate,
): Promise<ThemePreferences> {
  return csrfRequest<ThemePreferences>("/api/account/preferences", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(preferences),
  });
}
