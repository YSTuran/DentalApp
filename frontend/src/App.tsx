import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./auth/AuthProvider";
import { ProtectedRoute, PublicOnlyRoute, SystemAdminRoute } from "./auth/RouteGuards";
import { AccessDeniedPage } from "./pages/AccessDeniedPage";
import { ClinicsPage } from "./pages/ClinicsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<PublicOnlyRoute />}>
            <Route path="/giris" element={<LoginPage />} />
          </Route>
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/yetkisiz" element={<AccessDeniedPage />} />
            <Route element={<SystemAdminRoute />}>
              <Route path="/yonetim/klinikler" element={<ClinicsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
