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
      <div className="flex min-h-screen items-center justify-center">
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 panel p-6 rounded-2xl">
          <input name="email" type="text" placeholder="you@example.com" className="text-input" />
          <input name="pass" type="password" placeholder="•••••" className="text-input" />
          <button type="submit" disabled={loading} className="btn-primary justify-center">{loading ? <Loader2 size={18} /> : "Log In"}</button>
        </form>
      </div>
    </>
  );
}
