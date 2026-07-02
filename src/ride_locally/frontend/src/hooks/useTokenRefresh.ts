import { useEffect } from "react"
import { apiUrl } from "../api/client";
import type { TokenResponse } from "../api/auth";

export function useTokenRefresh() {
  useEffect(() => {
    const tick = async () => {
      const expiresAt = localStorage.getItem("access_token_expires");
      if (!expiresAt) return;
      const msLeft = new Date(expiresAt).getTime() - Date.now();
      if (msLeft <= 5 * 60_000 && msLeft > 0) {
        // refresh when less than 5 minutes left till token expiry
        const res = await fetch(apiUrl("/auth/refresh"), {method: "POST"});
        if (!res.ok) {
          return;
        }
        const data: TokenResponse = await res.json();
        localStorage.setItem("access_token", data?.token);
      }
    };

    const id = setInterval(tick, 60_000);
    return () => clearInterval(id);
  }, []);
}
