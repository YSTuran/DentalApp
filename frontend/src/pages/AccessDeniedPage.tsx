import { Link } from "react-router-dom";

import { DemoBanner } from "../components/DemoBanner";

export function AccessDeniedPage() {
  return (
    <div className="dashboard-shell">
      <DemoBanner />
      <main className="state-page">
        <p className="eyebrow">403 · YETKİSİZ ERİŞİM</p>
        <h1>Bu sayfayı görüntüleme yetkiniz yok.</h1>
        <p>Hesabınıza atanmış roller bu yönetim alanına erişim sağlamıyor.</p>
        <Link className="primary-link" to="/">
          Kontrol paneline dön
        </Link>
      </main>
    </div>
  );
}
