import { useState, type ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { logout } from "../../api/auth";
import {
  Home,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Target,
  Workflow,
  Zap,
} from "lucide-react";

const navItems = [
  { to: "/", label: "Home", icon: Home },
  { to: "/targets", label: "Targets", icon: Target },
  { to: "/scraper", label: "Scraper", icon: Zap },
  { to: "/processor", label: "Processor", icon: Workflow },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export default function Layout({
  children,
}: {
  children: ReactNode;
}): ReactNode {
  const [isOpen, setIsOpen] = useState(true);
  const navigate = useNavigate();

  return (
    <div className="relative flex min-h-screen overflow-hidden bg-surface text-surface-text">

      <nav
        className={`glass-panel relative z-20 flex h-screen shrink-0 flex-col overflow-hidden whitespace-nowrap transition-all duration-300 ${isOpen ? "w-64 items-start px-4" : "w-16 items-center px-2"}`}
      >
        <div
          className={`flex w-full items-center border-b border-accent-light/10 py-5 ${isOpen ? "justify-between" : "justify-center"}`}
        >
          {isOpen && (
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-accent-light/80">
                Ride Locally
              </p>
              <p className="text-sm font-semibold text-white">Scraper</p>
            </div>
          )}
          <button
            type="button"
            onClick={() => setIsOpen((v) => !v)}
            className="glass-inset rounded-lg p-2 text-accent-light/80 transition hover:border-accent-light/30 hover:text-white"
            aria-label={isOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            {isOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
          </button>
        </div>

        <div className="flex w-full flex-1 flex-col gap-1 py-4">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              title={label}
              className={({ isActive }) =>
                `${isActive ? "tab-active" : "tab-inactive"} ${isOpen ? "justify-start" : "justify-center"}`
              }
            >
              <Icon size={18} className="shrink-0" />
              {isOpen && <span>{label}</span>}
            </NavLink>
          ))}
        </div>

        <button
          type="button"
          onClick={() => {
            logout();
            navigate("/login", { replace: true });
          }}
          title="Log out"
          className={`btn-secondary-danger mb-4 w-full ${isOpen ? "justify-start" : "justify-center"}`}
        >
          <LogOut size={18} className="shrink-0" />
          {isOpen && <span>Log out</span>}
        </button>
      </nav>

      <main className="relative z-10 h-screen min-w-0 flex-1 overflow-y-auto">
        <div className="p-8 min-h-full flex flex-col">{children}</div>
      </main>
    </div>
  );
}
