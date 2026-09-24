import { Navigate, Outlet } from "react-router-dom";

import { LoadingScreen } from "../components/LoadingScreen";
import { useAuth } from "./AuthContext";

export function ProtectedRoute() {
  const { status } = useAuth();

  if (status === "loading") {
    return <LoadingScreen />;
  }

  return status === "authenticated" ? <Outlet /> : <Navigate to="/giris" replace />;
}

export function PublicOnlyRoute() {
  const { status } = useAuth();

  if (status === "loading") {
    return <LoadingScreen />;
  }

  return status === "unauthenticated" ? <Outlet /> : <Navigate to="/" replace />;
}
