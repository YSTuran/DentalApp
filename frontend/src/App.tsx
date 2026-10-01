import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./auth/AuthProvider";
import {
  ManagementReadRoute,
  ProtectedRoute,
  PublicOnlyRoute,
  SystemAdminRoute,
} from "./auth/RouteGuards";
import { AccessDeniedPage } from "./pages/AccessDeniedPage";
import { AuditLogPage } from "./pages/AuditLogPage";
import { ClinicsPage } from "./pages/ClinicsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ThemeProvider } from "./theme/ThemeProvider";
import { UsersPage } from "./pages/UsersPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ThemeProvider>
          <Routes>
            <Route element={<PublicOnlyRoute />}>
              <Route path="/giris" element={<LoginPage />} />
            </Route>
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/ayarlar" element={<SettingsPage />} />
              <Route path="/yetkisiz" element={<AccessDeniedPage />} />
              <Route element={<ManagementReadRoute />}>
                <Route path="/yonetim/klinikler" element={<ClinicsPage />} />
                <Route path="/yonetim/kullanicilar" element={<UsersPage />} />
              </Route>
              <Route element={<SystemAdminRoute />}>
                <Route path="/yonetim/audit-kayitlari" element={<AuditLogPage />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ThemeProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
