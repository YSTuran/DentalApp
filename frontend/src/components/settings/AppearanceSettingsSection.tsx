import { useState } from "react";

import { useTheme } from "../../theme/ThemeContext";
import { COLOR_PALETTE_OPTIONS, THEME_MODE_OPTIONS } from "../../theme/options";
import type { ThemePreferenceUpdate } from "../../types/theme";

const SPECIAL_PALETTES = new Set(["sepia", "high_contrast"]);

export function AppearanceSettingsSection() {
  const { preferences, resolvedMode, updatePreferences } = useTheme();
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">(
    "idle",
  );
  const standardPalettes = COLOR_PALETTE_OPTIONS.filter(
    ({ value }) => !SPECIAL_PALETTES.has(value),
  );
  const specialPalettes = COLOR_PALETTE_OPTIONS.filter(({ value }) =>
    SPECIAL_PALETTES.has(value),
  );

  async function changeAppearance(update: ThemePreferenceUpdate) {
    setSaveState("saving");
    try {
      await updatePreferences(update);
      setSaveState("saved");
    } catch {
      setSaveState("error");
    }
  }

  const saveMessage = {
    idle: "Değişiklikler hesabınızla eşitlenir.",
    saving: "Kaydediliyor…",
    saved: "Kaydedildi",
    error: "Kaydedilemedi; önceki seçim geri yüklendi.",
  }[saveState];

  return (
    <section className="settings-panel" aria-labelledby="appearance-settings-title">
      <header className="settings-section-heading appearance-heading">
        <div>
          <p className="card-label">GÖRÜNÜM</p>
          <h2 id="appearance-settings-title">Tema tercihi</h2>
          <p>Mod ve renk değişiklikleri cihazda hemen uygulanır.</p>
        </div>
        <div className="appearance-status">
          <span className="resolved-theme-badge">
            Şu anda {resolvedMode === "dark" ? "karanlık" : "açık"}
          </span>
          <span
            className={saveState === "error" ? "appearance-save-state error" : "appearance-save-state"}
            role={saveState === "error" ? "alert" : "status"}
          >
            {saveMessage}
          </span>
        </div>
      </header>

      <fieldset className="theme-options" disabled={saveState === "saving"}>
        <legend>Görünüm modu</legend>
        <div className="mode-segmented-control">
          {THEME_MODE_OPTIONS.map((option) => (
            <label key={option.value}>
              <input
                type="radio"
                name="theme-mode"
                value={option.value}
                checked={preferences.theme_mode === option.value}
                onChange={() => void changeAppearance({ theme_mode: option.value })}
              />
              <strong>{option.label}</strong>
              <small>{option.description}</small>
            </label>
          ))}
        </div>
      </fieldset>

      <PaletteGroup
        legend="Renk paletleri"
        description="Arayüzün ana rengini ve yüzey tonlarını belirler."
        options={standardPalettes}
        selected={preferences.color_palette}
        disabled={saveState === "saving"}
        onChange={(color_palette) => void changeAppearance({ color_palette })}
      />

      <PaletteGroup
        legend="Özel görünümler"
        description="Okuma rahatlığı veya daha güçlü görsel ayrım için hazırlanmıştır."
        options={specialPalettes}
        selected={preferences.color_palette}
        disabled={saveState === "saving"}
        onChange={(color_palette) => void changeAppearance({ color_palette })}
        compact
      />

      <footer className="appearance-footer">
        <span>Sistem seçeneği, cihazın açık veya karanlık ayarını takip eder.</span>
        <button
          type="button"
          className="secondary-button compact-button"
          disabled={saveState === "saving"}
          onClick={() => void changeAppearance({
            theme_mode: "light",
            color_palette: "default",
          })}
        >
          Varsayılanı geri yükle
        </button>
      </footer>
    </section>
  );
}

type PaletteOption = (typeof COLOR_PALETTE_OPTIONS)[number];

interface PaletteGroupProps {
  legend: string;
  description: string;
  options: ReadonlyArray<PaletteOption>;
  selected: PaletteOption["value"];
  disabled: boolean;
  compact?: boolean;
  onChange: (palette: PaletteOption["value"]) => void;
}

function PaletteGroup({
  legend,
  description,
  options,
  selected,
  disabled,
  compact = false,
  onChange,
}: PaletteGroupProps) {
  return (
    <fieldset className="theme-options palette-fieldset" disabled={disabled}>
      <legend>{legend}</legend>
      <p>{description}</p>
      <div className={compact ? "settings-palette-grid compact" : "settings-palette-grid"}>
        {options.map((option) => (
          <label className="theme-choice palette-choice" key={option.value}>
            <input
              type="radio"
              name="color-palette"
              value={option.value}
              checked={selected === option.value}
              onChange={() => onChange(option.value)}
            />
            <span className={`palette-swatch palette-swatch-${option.value}`} aria-hidden="true">
              <i /><i /><i />
            </span>
            <span className="theme-choice-check" aria-hidden="true">✓</span>
            <strong>{option.label}</strong>
            <small>{option.description}</small>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
