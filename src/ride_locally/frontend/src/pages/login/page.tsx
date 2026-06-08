import { useState, useContext } from "react";
import type { SubmitEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { login } from "../../api/auth";
import { Loader2 } from "lucide-react";
import { ToastContext } from "../../components/Toast/ToastContext";
import Background from "../../components/Background/Background";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = location?.state?.from?.pathname ?? "/";
  const toast = useContext(ToastContext);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);

    const form = e.currentTarget;
    const data = new FormData(form);

    const user = String(data.get("email") ?? "");
    const pass = String(data.get("pass") ?? "");

    try {
      const { access_token, expires_at } = await login({
        email: user,
        password: pass,
      });
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("access_token_expires", expires_at);
      toast.success("Logged in");
      navigate(from, { replace: true });
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-surface text-surface-text">
      <Background />

      <div className="relative z-10 flex min-h-screen items-center justify-center px-4 py-12">
        <div className="glass-panel relative w-full max-w-md rounded-3xl p-8 before:pointer-events-none before:absolute before:inset-x-8 before:top-0 before:h-px before:bg-gradient-to-r before:from-transparent before:via-accent-light/40 before:to-transparent">
          <div className="mb-8 text-center">
            <p className="mb-2 text-xs font-medium uppercase tracking-[0.2em] text-accent-light/80">
              Ride Locally Scraper Interface
            </p>
            <h1 className="text-3xl font-semibold tracking-tight text-white">
              Welcome back
            </h1>
            <p className="mt-2 text-sm text-white/60">Sign in to continue</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label
                htmlFor="email"
                className="text-sm font-medium text-accent-light/80"
              >
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                autoComplete="email"
                placeholder="you@example.com"
                className="glass-inset w-full rounded-xl px-4 py-3 text-white placeholder:text-white/35 outline-none transition focus:border-accent-light/40 focus:ring-2 focus:ring-accent/20"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="pass"
                className="text-sm font-medium text-accent-light/80"
              >
                Password
              </label>
              <input
                id="pass"
                name="pass"
                type="password"
                required
                autoComplete="current-password"
                placeholder="•••••••"
                className="glass-inset w-full rounded-xl px-4 py-3 text-white placeholder:text-white/35 outline-none transition focus:border-accent-light/40 focus:ring-2 focus:ring-accent/20"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="group relative mt-2 flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl border border-accent-light/25 bg-gradient-to-r from-accent-dark/90 to-accent/90 px-4 py-3 text-sm font-semibold text-white shadow-[0_10px_30px_rgba(249,115,22,0.35)] transition hover:from-accent hover:to-accent-light hover:shadow-[0_12px_35px_rgba(251,146,60,0.4)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <span className="absolute inset-0 bg-white/10 opacity-0 transition group-hover:opacity-100" />
              {loading ? (
                <>
                  <Loader2 className="relative animate-spin" size={18} />
                  <span className="relative">Signing in…</span>
                </>
              ) : (
                <span className="relative">Sign in</span>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
