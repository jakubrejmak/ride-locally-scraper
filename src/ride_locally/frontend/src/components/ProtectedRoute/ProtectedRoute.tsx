import { Navigate, Outlet, useLocation } from "react-router-dom";
import { logout } from "../../api/auth";
import { useTokenRefresh } from "../../hooks/useTokenRefresh";

function isAuthenticated(): boolean {
  const token = localStorage.getItem("access_token");
  const expiresAt = localStorage.getItem("access_token_expires");

  if (!token || !expiresAt) return false;

  const expired =  Date.now() < new Date(expiresAt).getTime();
  return expired;
}

export default function ProtectedRoute() {
  const location = useLocation();
  useTokenRefresh();

  if (!isAuthenticated()) {
    console.warn(`Authenticated: ${isAuthenticated()}`);
    logout();
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
