import { Navigate, Outlet, useLocation } from "react-router-dom";
import { logout } from "../../api/auth";

function isAuthenticated(): boolean {
  const token = localStorage.getItem("access_token");
  const expiresAt = localStorage.getItem("access_token_expires");

  if (!token || !expiresAt) return false;

  return Date.now() < new Date(expiresAt).getTime();
}

export default function ProtectedRoute() {
  const location = useLocation();

  if (!isAuthenticated()) {
    logout();
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
