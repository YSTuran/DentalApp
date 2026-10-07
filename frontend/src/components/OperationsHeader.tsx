import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { NotificationBell } from "./NotificationBell";
import { ActiveClinicSelector } from "./ActiveClinicSelector";

const createRoles = new Set(["managing_dentist", "dentist", "clinic_staff"]);

export function OperationsHeader() {
  const { logout, user } = useAuth();
  const canCreate = user?.clinic_roles.some((item) => createRoles.has(item.role)) === true;

  return (
    <header className="topbar management-topbar">
      <Link className="brand-inline brand-link" to="/">
        <div className="brand-mark brand-mark-small" aria-hidden="true">D</div>
        <div><strong>DentalApp</strong><span>Vaka operasyonu</span></div>
      </Link>
      <nav className="management-nav" aria-label="Vaka navigasyonu">
        <NavLink to="/vakalar" end>Vakalar</NavLink>
        {canCreate && <NavLink to="/vakalar/yeni">Yeni vaka</NavLink>}
        <NavLink to="/raporlar">Raporlar</NavLink>
      </nav>
      <div className="topbar-actions">
        <ActiveClinicSelector />
        <NotificationBell />
        <Link className="text-link" to="/">Panel</Link>
        <Link className="text-link" to="/ayarlar">Ayarlar</Link>
        <button className="secondary-button" onClick={() => void logout()}>Çıkış yap</button>
      </div>
    </header>
  );
}
