import { useEffect, useRef, useState } from "react";
import {
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import {
  Bell,
  ChartNoAxesColumnIncreasing,
  FilePlus2,
  House,
  LogOut,
  Menu,
  Network,
  RefreshCw,
  Settings2,
  TriangleAlert,
  Info,
  X,
} from "lucide-react";
import { api, json, useAction, useApi } from "./lib/api";
import { useAuth } from "./lib/auth";
import type { Json } from "./lib/types";
import { Brand, Button, Loading } from "./components/UI";
import { ReportForm } from "./components/ReportForm";
import { IncidentDetails } from "./components/IncidentDetails";
import { Dashboard } from "./pages/Dashboard";
import { Incidents } from "./pages/Incidents";
import { Risk } from "./pages/Risk";
import { Agents } from "./pages/Agents";
import { Admin } from "./pages/Admin";
import { Notifications } from "./pages/Notifications";
import { Login } from "./pages/Login";
export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <Loading text="Opening your workspace…" />;
  if (!user) return <Login />;
  return <Workspace />;
}
function Workspace() {
  const { user, logout } = useAuth();
  const location = useLocation(),
    navigate = useNavigate();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);
  const [mobile, setMobile] = useState(false),
    [report, setReport] = useState(false),
    [details, setDetails] = useState<number | null>(null),
    [banner, setBanner] = useState(true);
  const notifications = useApi<Json[]>("/notifications"),
    health = useApi<Json>("/health"),
    operations = useApi<Json>("/dashboard");
  const [narrow, setNarrow] = useState(() => window.matchMedia("(max-width: 760px)").matches);
  const sidebarRef = useRef<HTMLElement>(null);
  const menuRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const media = window.matchMedia("(max-width: 760px)");
    const change = () => { setNarrow(media.matches); if (!media.matches) setMobile(false); };
    media.addEventListener("change", change);
    return () => media.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    if (!mobile || !narrow) return;
    const previous = document.activeElement as HTMLElement | null;
    const controls = () => Array.from(sidebarRef.current?.querySelectorAll<HTMLElement>("a[href], button:not([disabled])") || []);
    controls()[0]?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); setMobile(false); }
      if (event.key === "Tab") {
        const elements = controls(), first = elements[0], last = elements[elements.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("keydown", keydown);
      (previous?.isConnected ? previous : menuRef.current)?.focus();
    };
  }, [mobile, narrow]);
  const operator = user?.role === "authority" || user?.role === "admin";
  const refresh = useAction(
    () => api("/risk/refresh", { method: "POST", body: json({}) }),
    "Intelligence refreshed",
  );
  const titles: Record<string, [string, string]> = {
    "/": [
      user?.role === "citizen"
        ? "Your civic dashboard"
        : user?.role === "worker"
          ? "Field workspace"
          : "Command centre",
      user?.role === "citizen"
        ? "Your reports. Your neighbourhood. A safer city."
        : user?.role === "worker"
          ? "Your team’s assignments and response progress"
          : "Lahore · Civic operations",
    ],
    "/incidents": [
      user?.role === "citizen"
        ? "My reports"
        : user?.role === "worker"
          ? "My assignments"
          : "Incident management",
      "From reported hazard to verified resolution",
    ],
    "/risk": [
      "Disaster intelligence",
      "Local flooding & waterlogging · Lahore",
    ],
    "/agents": ["Agent activity", "Transparent intelligence. Human decisions."],
    "/admin": [
      "Administration",
      "Manage departments, teams, zones, and access",
    ],
    "/notifications": ["Notifications", "Stay connected to every response"],
  };
  const [title, subtitle] = titles[location.pathname] || titles["/"];
  const unread = notifications.data?.filter((n) => !n.read).length || 0;
  const links = [
    { to: "/", label: "Overview", icon: House },
    {
      to: "/incidents",
      label:
        user?.role === "citizen"
          ? "My reports"
          : user?.role === "worker"
            ? "My assignments"
            : "Incidents",
      icon: TriangleAlert,
    },
    ...(operator
      ? [
          {
            to: "/risk",
            label: "Disaster intelligence",
            icon: ChartNoAxesColumnIncreasing,
          },
          { to: "/agents", label: "Agent activity", icon: Network },
        ]
      : []),
    ...(user?.role === "admin"
      ? [{ to: "/admin", label: "Administration", icon: Settings2 }]
      : []),
    { to: "/notifications", label: "Notifications", icon: Bell },
  ];
  function closeNav() {
    setMobile(false);
  }
  function signOut() {
    setDetails(null);
    logout();
    navigate("/");
  }
  const syncedAt = operations.dataUpdatedAt
    ? new Intl.DateTimeFormat("en-GB", {
        day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
      }).format(operations.dataUpdatedAt)
    : null;
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      {mobile && (
        <button
          className="sidebar-overlay"
          aria-label="Dismiss navigation overlay"
          onClick={closeNav}
        />
      )}
      <aside ref={sidebarRef} className={`sidebar ${mobile ? "open" : ""}`} inert={narrow && !mobile ? true : undefined} aria-label="Workspace navigation">
        <Brand />
        <button type="button" className="icon-button sidebar-close" aria-label="Close navigation" onClick={closeNav}><X size={19} /></button>
        <nav aria-label="Main navigation">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              end={to === "/"}
              to={to}
              aria-label={label}
              title={label}
              onClick={closeNav}
              className={({ isActive }) =>
                isActive ? "nav-item active" : "nav-item"
              }
            >
              <Icon size={20} strokeWidth={1.7} />
              <span>{label}</span>
              {to === "/notifications" && unread > 0 && (
                <b className="nav-count">{unread}</b>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="system-status">
            <i />
            {health.isError ? "Connection unavailable" : health.data ? "Workspace connected" : "Connecting workspace"}
            <span>{health.data?.demo_mode ? "Lahore demonstration" : "Civic operations"}</span>
          </div>
          <div className="profile">
            <span className="avatar">
              {user?.name
                .split(" ")
                .map((n) => n[0])
                .slice(0, 2)
                .join("")}
            </span>
            <div>
              <strong>{user?.name}</strong>
              <small>{user?.role} workspace</small>
            </div>
            <button
              className="icon-button"
              aria-label="Sign out"
              title="Sign out"
              onClick={signOut}
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="page-header">
          <button
            ref={menuRef}
            className="icon-button mobile-menu"
            aria-label="Open navigation"
            aria-expanded={mobile}
            onClick={() => setMobile(true)}
          >
            <Menu size={23} />
          </button>
          <div className="page-title">
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
          <div className="header-actions">
            {syncedAt && <span className="data-recency">Synced {syncedAt}</span>}
            {user?.role === "citizen" && (
              <Button onClick={() => setReport(true)}>
                <FilePlus2 size={17} />
                New report
              </Button>
            )}
            {operator && (
              <Button
                pending={refresh.isPending}
                onClick={() => refresh.mutate(undefined)}
              >
                <RefreshCw size={17} />
                Refresh intelligence
              </Button>
            )}
            <button
              className="header-notifications icon-button"
              aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
              onClick={() => navigate("/notifications")}
            >
              <Bell size={19} />
              {unread > 0 && <i />}
            </button>
            <button
              className="mobile-profile icon-button"
              aria-label="Sign out"
              onClick={signOut}
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main id="main-content">
          {banner && health.data?.demo_mode !== false && (
            <div className="demo-banner">
              <Info size={15} />
              <span>
                Synthetic Lahore demonstration <b>·</b> {health.data?.ai_mode === "vision_api" ? "Model assisted analysis" : "Text-rule analysis"} <b>·</b> Human approval required.
              </span>
              <button
                className="icon-button"
                aria-label="Dismiss demonstration notice"
                onClick={() => setBanner(false)}
              >
                <X size={15} />
              </button>
            </div>
          )}
          <Routes>
            <Route path="/" element={<Dashboard onOpen={setDetails} />} />
            <Route
              path="/incidents"
              element={<Incidents onOpen={setDetails} />}
            />
            <Route
              path="/notifications"
              element={<Notifications onOpen={setDetails} />}
            />
            {operator && (
              <>
                <Route path="/risk" element={<Risk />} />
                <Route path="/agents" element={<Agents />} />
              </>
            )}
            {user?.role === "admin" && (
              <Route path="/admin" element={<Admin />} />
            )}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <footer className="workspace-footer">
            <span>
              CivicShield AI <b>·</b> Predict Risks. Prevent Disasters.
            </span>
            <span>
              Human oversight at every step
            </span>
          </footer>
        </main>
      </div>
      {report && (
        <ReportForm
          open
          onClose={() => setReport(false)}
          onSaved={(id) => {
            setDetails(id);
            navigate("/incidents");
          }}
        />
      )}
      {details != null && (
        <IncidentDetails
          key={details}
          id={details}
          onClose={() => setDetails(null)}
        />
      )}
    </div>
  );
}
