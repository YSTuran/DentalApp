import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./auth/AuthProvider";
import {
  ManagementReadRoute,
  ProtectedRoute,
  PublicOnlyRoute,
  ReportsRoute,
  SystemAdminRoute,
} from "./auth/RouteGuards";
import { LoadingScreen } from "./components/LoadingScreen";
import { ThemeProvider } from "./theme/ThemeProvider";

const AccessDeniedPage = lazy(() => import("./pages/AccessDeniedPage").then((module) => ({ default: module.AccessDeniedPage })));
const AuditLogPage = lazy(() => import("./pages/AuditLogPage").then((module) => ({ default: module.AuditLogPage })));
const ClinicsPage = lazy(() => import("./pages/ClinicsPage").then((module) => ({ default: module.ClinicsPage })));
const CaseDetailPage = lazy(() => import("./pages/CaseDetailPage").then((module) => ({ default: module.CaseDetailPage })));
const CasesPage = lazy(() => import("./pages/CasesPage").then((module) => ({ default: module.CasesPage })));
const DashboardPage = lazy(() => import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const LoginPage = lazy(() => import("./pages/LoginPage").then((module) => ({ default: module.LoginPage })));
const NewCasePage = lazy(() => import("./pages/NewCasePage").then((module) => ({ default: module.NewCasePage })));
const ReportsPage = lazy(() => import("./pages/ReportsPage").then((module) => ({ default: module.ReportsPage })));
const SettingsPage = lazy(() => import("./pages/SettingsPage").then((module) => ({ default: module.SettingsPage })));
const UsersPage = lazy(() => import("./pages/UsersPage").then((module) => ({ default: module.UsersPage })));

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ThemeProvider>
          <Suspense fallback={<LoadingScreen message="Sayfa yükleniyor…" />}>
            <Routes>
            <Route element={<PublicOnlyRoute />}>
              <Route path="/giris" element={<LoginPage />} />
            </Route>
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/ayarlar" element={<SettingsPage />} />
              <Route path="/vakalar" element={<CasesPage />} />
              <Route path="/vakalar/yeni" element={<NewCasePage />} />
              <Route path="/vakalar/:caseId" element={<CaseDetailPage />} />
              <Route element={<ReportsRoute />}>
                <Route path="/raporlar" element={<ReportsPage />} />
              </Route>
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
          </Suspense>
        </ThemeProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
