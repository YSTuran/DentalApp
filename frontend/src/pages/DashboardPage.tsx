import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { DemoBanner } from "../components/DemoBanner";
import type { RoleCode } from "../types/auth";

const roleLabels: Record<RoleCode, string> = {
  system_admin: "Sistem yöneticisi",
  clinic_manager: "Klinik yöneticisi",
  managing_dentist: "Yönetici hekim",
  dentist: "Hekim",
  clinic_staff: "Klinik personeli",
  technician: "Laboratuvar teknisyeni",
};

export function DashboardPage() {
  const { user, logout } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user === null) {
    return null;
  }

  async function handleLogout() {
    setError(null);
    setLoggingOut(true);
    try {
      await logout();
    } catch {
      setError("Oturum kapatılamadı. FastAPI bağlantısını kontrol edip tekrar deneyin.");
      setLoggingOut(false);
    }
  }

  const roles = [
    ...user.global_roles.map((role) => roleLabels[role]),
    ...user.clinic_roles.map((assignment) => roleLabels[assignment.role]),
  ];

  return (
    <div className="dashboard-shell">
      <DemoBanner />
      <header className="topbar">
        <div className="brand-inline">
          <div className="brand-mark brand-mark-small" aria-hidden="true">
            D
          </div>
          <div>
            <strong>DentalApp</strong>
            <span>Operasyon paneli</span>
          </div>
        </div>
        <button className="secondary-button" onClick={handleLogout} disabled={loggingOut}>
          {loggingOut ? "Çıkış yapılıyor…" : "Çıkış yap"}
        </button>
      </header>

      <main className="dashboard-content">
        <section className="welcome-card">
          <div>
            <p className="eyebrow">OTURUM AÇILDI</p>
            <h1>Hoş geldiniz, {user.full_name}</h1>
            <p>Firebase kimliği ve FastAPI oturumu başarıyla doğrulandı.</p>
          </div>
          <span className="status-pill">
            <i aria-hidden="true" /> Aktif
          </span>
        </section>

        {error !== null && (
          <div className="form-error dashboard-error" role="alert">
            {error}
          </div>
        )}

        <div className="dashboard-grid">
          <section className="info-card">
            <p className="card-label">KULLANICI</p>
            <dl>
              <div>
                <dt>Ad soyad</dt>
                <dd>{user.full_name}</dd>
              </div>
              <div>
                <dt>E-posta</dt>
                <dd>{user.email}</dd>
              </div>
              <div>
                <dt>Kullanıcı ID</dt>
                <dd className="technical-value">{user.id}</dd>
              </div>
            </dl>
          </section>

          <section className="info-card">
            <p className="card-label">YETKİLER</p>
            <div className="role-list">
              {roles.length > 0 ? (
                roles.map((role) => <span key={role}>{role}</span>)
              ) : (
                <p>Aktif rol ataması bulunmuyor.</p>
              )}
            </div>
            <p className="scope-note">
              {user.global_roles.includes("system_admin")
                ? "Tüm klinikler üzerinde sistem yöneticisi erişimi bulunuyor."
                : `${user.clinic_roles.length} klinik rolü atanmış.`}
            </p>
          </section>

          <section className="info-card next-step-card">
            <p className="card-label">SONRAKİ MODÜL</p>
            <h2>Klinik yönetimi</h2>
            <p>
              Klinik kayıtlarını oluşturun, bilgilerini güncelleyin ve şube durumlarını yönetin.
            </p>
            {user.global_roles.includes("system_admin") && (
              <Link className="primary-link inline-link" to="/yonetim/klinikler">Klinikleri yönet</Link>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
