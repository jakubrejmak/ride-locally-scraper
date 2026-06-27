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
      toast?.success("Logged in");
      navigate(from, { replace: true });
    } catch (e) {
      const message = e instanceof Error ? e.message : "Login failed";
      toast?.error(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Background />
      <div className="flex min-h-screen items-stretch justify-center sm:items-center sm:px-6">
        <form onSubmit={handleSubmit} className="flex min-h-screen w-full flex-col justify-center gap-3 px-6 py-8 sm:min-h-0 sm:max-w-md sm:panel sm:rounded-2xl sm:p-6">
          <label htmlFor="email" className="text-white">Email</label>
          <input id="email" name="email" type="text" placeholder="you@example.com" className="text-input" />
          <label htmlFor="pass" className="text-white">Password</label>
          <input id="pass" name="pass" type="password" placeholder="••••••••" className="text-input" />
          <button type="submit" disabled={loading} className="btn-primary justify-center mt-3">{loading ? <Loader2 className="animate-spin" size={18} /> : "Log In"}</button>
        </form>
      </div>
    </>
  );
}
