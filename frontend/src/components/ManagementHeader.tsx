import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function ManagementHeader() {
  const { logout, user } = useAuth();
  const isSystemAdmin = user?.global_roles.includes("system_admin") === true;

  return (
    <header className="topbar management-topbar">
      <Link className="brand-inline brand-link" to="/">
        <div className="brand-mark brand-mark-small" aria-hidden="true">D</div>
        <div><strong>DentalApp</strong><span>{isSystemAdmin ? "Sistem yönetimi" : "Klinik görünümü"}</span></div>
      </Link>
      <nav
        className="management-nav"
        aria-label={isSystemAdmin ? "Sistem yönetimi navigasyonu" : "Klinik görünümü navigasyonu"}
      >
        <NavLink to="/yonetim/klinikler">Klinikler</NavLink>
        <NavLink to="/yonetim/kullanicilar">Kullanıcılar</NavLink>
        {isSystemAdmin && <NavLink to="/yonetim/audit-kayitlari">Audit kayıtları</NavLink>}
      </nav>
      <div className="topbar-actions">
        <Link className="text-link" to="/">Panel</Link>
        <Link className="text-link" to="/ayarlar">Ayarlar</Link>
        <button className="secondary-button" onClick={() => void logout()}>Çıkış yap</button>
      </div>
    </header>
  );
}
