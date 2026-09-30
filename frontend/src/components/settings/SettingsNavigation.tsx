import type { SettingsSection } from "../../types/settings";

const SETTINGS_SECTIONS: ReadonlyArray<{
  value: SettingsSection;
  label: string;
  description: string;
}> = [
  { value: "account", label: "Hesap", description: "Kişisel bilgiler ve roller" },
  { value: "appearance", label: "Görünüm", description: "Tema modu ve renkler" },
  { value: "security", label: "Güvenlik", description: "Parola işlemleri" },
];

interface SettingsNavigationProps {
  activeSection: SettingsSection;
  onChange: (section: SettingsSection) => void;
}

export function SettingsNavigation({
  activeSection,
  onChange,
}: SettingsNavigationProps) {
  return (
    <nav className="settings-navigation" aria-label="Ayar bölümleri">
      {SETTINGS_SECTIONS.map((section) => (
        <button
          type="button"
          key={section.value}
          className={activeSection === section.value ? "active" : undefined}
          aria-current={activeSection === section.value ? "page" : undefined}
          onClick={() => onChange(section.value)}
        >
          <strong>{section.label}</strong>
          <small>{section.description}</small>
        </button>
      ))}
    </nav>
  );
}
