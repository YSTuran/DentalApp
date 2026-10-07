import { Navigate, Outlet } from "react-router-dom";

import { AuthUnavailableScreen } from "../components/AuthUnavailableScreen";
import { LoadingScreen } from "../components/LoadingScreen";
import { useAuth } from "./AuthContext";

export function ProtectedRoute() {
  const { logout, retrySession, status } = useAuth();

  if (status === "loading") {
    return <LoadingScreen />;
  }

  if (status === "unavailable") {
    return <AuthUnavailableScreen onRetry={retrySession} onLogout={logout} />;
  }

  return status === "authenticated" ? <Outlet /> : <Navigate to="/giris" replace />;
}

export function PublicOnlyRoute() {
  const { logout, retrySession, status } = useAuth();

  if (status === "loading") {
    return <LoadingScreen />;
  }

  if (status === "unavailable") {
    return <AuthUnavailableScreen onRetry={retrySession} onLogout={logout} />;
  }

  return status === "unauthenticated" ? <Outlet /> : <Navigate to="/" replace />;
}

export function SystemAdminRoute() {
  const { user } = useAuth();

  return user?.global_roles.includes("system_admin") ? (
    <Outlet />
  ) : (
    <Navigate to="/yetkisiz" replace />
  );
}

export function ManagementReadRoute() {
  const { user } = useAuth();
  const canReadManagement =
    user?.global_roles.includes("system_admin") === true ||
    user?.clinic_roles.some((assignment) => assignment.role === "clinic_manager") === true;

  return canReadManagement ? <Outlet /> : <Navigate to="/yetkisiz" replace />;
}
