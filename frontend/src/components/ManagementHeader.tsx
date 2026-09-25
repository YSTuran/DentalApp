import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function ManagementHeader() {
  const { logout } = useAuth();

  return (
    <header className="topbar management-topbar">
      <Link className="brand-inline brand-link" to="/">
        <div className="brand-mark brand-mark-small" aria-hidden="true">D</div>
        <div><strong>DentalApp</strong><span>Sistem yönetimi</span></div>
      </Link>
      <nav className="management-nav" aria-label="Sistem yönetimi navigasyonu">
        <NavLink to="/yonetim/klinikler">Klinikler</NavLink>
        <NavLink to="/yonetim/kullanicilar">Kullanıcılar</NavLink>
        <NavLink to="/yonetim/audit-kayitlari">Audit kayıtları</NavLink>
      </nav>
      <div className="topbar-actions">
        <Link className="text-link" to="/">Panel</Link>
        <Link className="text-link" to="/ayarlar">Ayarlar</Link>
        <button className="secondary-button" onClick={() => void logout()}>Çıkış yap</button>
      </div>
    </header>
  );
}
