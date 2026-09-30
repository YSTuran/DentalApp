import type { ColorPalette, ThemeMode } from "../types/theme";

interface ThemeOption<T> {
  value: T;
  label: string;
  description: string;
}

export const THEME_MODE_OPTIONS: ReadonlyArray<ThemeOption<ThemeMode>> = [
  { value: "light", label: "Açık", description: "Aydınlık ve ferah görünüm" },
  { value: "dark", label: "Karanlık", description: "Düşük ışık için koyu görünüm" },
  { value: "system", label: "Sistem", description: "Cihaz ayarını otomatik kullanır" },
];

export const COLOR_PALETTE_OPTIONS: ReadonlyArray<ThemeOption<ColorPalette>> = [
  { value: "default", label: "Dental yeşili", description: "Varsayılan klinik paleti" },
  { value: "ocean", label: "Okyanus mavisi", description: "Dengeli mavi tonlar" },
  { value: "violet", label: "Menekşe", description: "Yumuşak mor tonlar" },
  { value: "arctic", label: "Arktik laboratuvar", description: "Temiz ve teknik turkuaz" },
  { value: "sage", label: "Adaçayı", description: "Sakin ve doğal yeşiller" },
  { value: "graphite", label: "Grafit", description: "Ciddi ve nötr görünüm" },
  { value: "amber", label: "Kehribar", description: "Sıcak ve enerjik tonlar" },
  { value: "burgundy", label: "Bordo", description: "Güçlü ve kurumsal palet" },
  { value: "coral", label: "Mercan", description: "Samimi ve modern tonlar" },
  { value: "sepia", label: "Kum ve sepya", description: "Göz dostu sıcak görünüm" },
  {
    value: "high_contrast",
    label: "Yüksek kontrast",
    description: "Belirgin sınırlar ve güçlü kontrast",
  },
];

export const THEME_MODE_VALUES = THEME_MODE_OPTIONS.map(({ value }) => value);
export const COLOR_PALETTE_VALUES = COLOR_PALETTE_OPTIONS.map(({ value }) => value);
