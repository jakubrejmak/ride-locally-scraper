const API_BASE = import.meta.env.VITE_API_URL ?? "";

export function apiUrl(path: string): string {
  const normalPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${normalPath}`;
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);

  const token = localStorage.getItem("access_token");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(apiUrl(path), {
    ...init,
    headers,
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  return res;
}
