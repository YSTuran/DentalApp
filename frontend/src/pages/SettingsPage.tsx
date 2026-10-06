import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { DemoBanner } from "../components/DemoBanner";
import { NotificationBell } from "../components/NotificationBell";
import { AccountSettingsSection } from "../components/settings/AccountSettingsSection";
import { AppearanceSettingsSection } from "../components/settings/AppearanceSettingsSection";
import { SecuritySettingsSection } from "../components/settings/SecuritySettingsSection";
import { SettingsNavigation } from "../components/settings/SettingsNavigation";
import type { SettingsSection } from "../types/settings";
import "../settings.css";

export function SettingsPage() {
  const { user, logout } = useAuth();
  const [activeSection, setActiveSection] = useState<SettingsSection>("account");

  if (user === null) return null;

  return (
    <div className="dashboard-shell">
      <DemoBanner />
      <header className="topbar">
        <Link className="brand-inline brand-link" to="/">
          <div className="brand-mark brand-mark-small" aria-hidden="true">D</div>
          <div><strong>DentalApp</strong><span>Hesap ayarları</span></div>
        </Link>
        <div className="topbar-actions">
          <NotificationBell />
          <Link className="text-link" to="/">Panele dön</Link>
          <button className="secondary-button" onClick={() => void logout()}>Çıkış yap</button>
        </div>
      </header>

      <main className="settings-content">
        <div className="page-heading settings-heading">
          <div>
            <p className="eyebrow">HESABIM</p>
            <h1>Ayarlar</h1>
            <p>Kişisel bilgiler, görünüm ve hesap güvenliği ayarlarınızı yönetin.</p>
          </div>
        </div>

        <div className="settings-workspace">
          <aside className="settings-sidebar">
            <SettingsNavigation
              activeSection={activeSection}
              onChange={setActiveSection}
            />
          </aside>

          <div className="settings-section-content">
            {activeSection === "account" && <AccountSettingsSection user={user} />}
            {activeSection === "appearance" && <AppearanceSettingsSection />}
            {activeSection === "security" && <SecuritySettingsSection />}
          </div>
        </div>
      </main>
    </div>
  );
}
