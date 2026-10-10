import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { DemoBanner } from "../components/DemoBanner";
import { NotificationBell } from "../components/NotificationBell";
import { ActiveClinicSelector } from "../components/ActiveClinicSelector";
import { ManagerApprovalCard } from "../components/dashboard/ManagerApprovalCard";
import { userRoleLabels } from "../lib/role-format";

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

  const roles = userRoleLabels(user);
  const isSystemAdmin = user.global_roles.includes("system_admin");
  const isClinicManager = user.clinic_roles.some(
    (assignment) => assignment.role === "clinic_manager",
  );
  const isManagingDentist = user.clinic_roles.some(
    (assignment) => assignment.role === "managing_dentist",
  );
  const canReadReports = isSystemAdmin || isClinicManager || isManagingDentist;

  return (
    <div className="dashboard-shell">
      <DemoBanner />
      <header className="topbar">
        <div className="brand-inline">
          <div className="brand-mark brand-mark-small" aria-hidden="true">
            D
          </div>
          <div>
            <strong>DentFlow</strong>
            <span>Operasyon paneli</span>
          </div>
        </div>
        <div className="topbar-actions">
          <ActiveClinicSelector />
          <NotificationBell />
          <Link className="text-link" to="/ayarlar">Ayarlar</Link>
          <button className="secondary-button" onClick={handleLogout} disabled={loggingOut}>
            {loggingOut ? "Çıkış yapılıyor…" : "Çıkış yap"}
          </button>
        </div>
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
          <section className="info-card next-step-card">
            <p className="card-label">VAKA OPERASYONU</p>
            <h2>Aktif vakaları görüntüleyin</h2>
            <p>Rolünüze açık vaka kuyruğunu, STL sürümlerini ve işlem geçmişini tek yerden takip edin.</p>
            <div className="dashboard-management-links">
              <Link className="primary-link" to="/vakalar">Vakalara git</Link>
              {canReadReports && (
                <Link className="primary-link" to="/raporlar">Raporları aç</Link>
              )}
              {user.clinic_roles.some((assignment) => ["managing_dentist", "dentist", "clinic_staff"].includes(assignment.role)) && (
                <Link className="primary-link" to="/vakalar/yeni">Yeni vaka oluştur</Link>
              )}
            </div>
          </section>

          <section className="info-card dashboard-user-card">
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
                <dt>Yetki</dt>
                <dd>{roles.length > 0 ? roles.join(" · ") : "Aktif rol ataması bulunmuyor"}</dd>
              </div>
              <div>
                <dt>Kullanıcı ID</dt>
                <dd className="technical-value">{user.id}</dd>
              </div>
            </dl>
          </section>

          {(isSystemAdmin || isClinicManager) && (
            <section className="info-card next-step-card">
              <p className="card-label">{isSystemAdmin ? "SİSTEM YÖNETİMİ" : "KLİNİK YÖNETİMİ"}</p>
              <h2>{isSystemAdmin ? "Klinik, kullanıcı ve audit yönetimi" : "Klinik personeli görünümü"}</h2>
              <p>
                {isSystemAdmin
                  ? "Klinik kayıtlarını, personel hesaplarını ve değiştirilemez işlem geçmişini yönetin."
                  : "Yetkili olduğunuz klinikleri ve bu kliniklerdeki hekimleri görüntüleyin."}
              </p>
              <div className="dashboard-management-links">
                <Link className="primary-link" to="/yonetim/klinikler">Klinikler</Link>
                <Link className="primary-link" to="/yonetim/kullanicilar">Kullanıcılar</Link>
                {isSystemAdmin && <Link className="primary-link" to="/yonetim/audit-kayitlari">Audit kayıtları</Link>}
              </div>
            </section>
          )}
          {isManagingDentist && <ManagerApprovalCard />}
        </div>
      </main>
    </div>
  );
}
