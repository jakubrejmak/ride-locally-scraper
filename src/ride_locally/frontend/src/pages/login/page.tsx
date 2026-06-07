import { useState, useContext } from "react";
import type { SubmitEvent } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../../api/auth";
import { Loader2 } from "lucide-react";
import { ToastContext } from "../../components/toast/ToastContext";

export default function Login() {
  const navigate = useNavigate();
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
      const { access_token } = await login({ email: user, password: pass });
      localStorage.setItem("access_token", access_token);
      toast.success("Logged in");
      navigate("/");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-100">
      {/* Background depth — minty glow orbs */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-24 top-10 h-72 w-72 rounded-full bg-emerald-500/35 blur-3xl" />
        <div className="absolute right-0 top-1/3 h-96 w-96 rounded-full bg-teal-400/30 blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-cyan-400/20 blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(167,243,208,0.12),transparent_45%)]" />
      </div>

      <div className="relative z-10 flex min-h-screen items-center justify-center px-4 py-12">
        {/* Glass card */}
        <div className="relative w-full max-w-md rounded-3xl border border-emerald-200/20 bg-emerald-50/5 p-8 shadow-[0_8px_40px_rgba(0,0,0,0.45)] backdrop-blur-2xl before:pointer-events-none before:absolute before:inset-x-8 before:top-0 before:h-px before:bg-gradient-to-r before:from-transparent before:via-emerald-200/40 before:to-transparent">
          <div className="mb-8 text-center">
            <p className="mb-2 text-xs font-medium uppercase tracking-[0.2em] text-emerald-300/80">
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
                className="text-sm font-medium text-emerald-50/80"
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
                className="w-full rounded-xl border border-emerald-200/15 bg-white/5 px-4 py-3 text-white placeholder:text-white/35 shadow-inner shadow-black/10 outline-none transition focus:border-emerald-300/50 focus:bg-emerald-50/5 focus:ring-2 focus:ring-emerald-400/25"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="pass"
                className="text-sm font-medium text-emerald-50/80"
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
                className="w-full rounded-xl border border-emerald-200/15 bg-white/5 px-4 py-3 text-white placeholder:text-white/35 shadow-inner shadow-black/10 outline-none transition focus:border-emerald-300/50 focus:bg-emerald-50/5 focus:ring-2 focus:ring-emerald-400/25"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="group relative mt-2 flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl border border-emerald-200/25 bg-gradient-to-r from-emerald-600/90 to-teal-500/90 px-4 py-3 text-sm font-semibold text-white shadow-[0_10px_30px_rgba(16,185,129,0.35)] transition hover:from-emerald-500 hover:to-teal-400 hover:shadow-[0_12px_35px_rgba(45,212,191,0.4)] disabled:cursor-not-allowed disabled:opacity-60"
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
