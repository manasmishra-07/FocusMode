import React, { useEffect, useState, useRef } from "react";
import {
  Routes,
  Route,
  NavLink,
  Link,
  Navigate,
  useNavigate,
} from "react-router-dom";
import {
  Aperture,
  LayoutDashboard,
  Monitor,
  ShieldCheck,
  CalendarDays,
  ChartNoAxesCombined,
  Settings,
  LogOut,
  ArrowUpRight,
  ArrowRight,
  Play,
  Square,
  Plus,
  LockKeyhole,
  Check,
  ChevronRight,
  Clock3,
  Flame,
  Target,
  Download,
  X,
  Menu,
  Sparkles,
  Laptop,
  CircleHelp,
} from "lucide-react";
import { api, getSession, saveSession } from "./api";
import { useAgent } from "./agent";

const NAV = [
  ["/dashboard", "Overview", LayoutDashboard],
  ["/devices", "My devices", Monitor],
  ["/allowlist", "Allowed apps", ShieldCheck],
  ["/schedules", "Schedules", CalendarDays],
  ["/insights", "Insights", ChartNoAxesCombined],
];
const minutes = (seconds) => `${Math.round((seconds || 0) / 60)} min`;
const date = (value) =>
  new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
function Brand() {
  return (
    <Link className="brand" to="/dashboard">
      <span className="brand-icon">
        <Aperture size={25} />
      </span>
      focus<span className="brand-light">mode</span>
      <span className="brand-dot">.</span>
    </Link>
  );
}
function Empty({ title = "A fresh start", children }) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Sparkles size={24} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
function Card({ children, className = "" }) {
  return <section className={`card ${className}`}>{children}</section>;
}
function Heading({ eyebrow, title, children, action }) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow || "YOUR FOCUS SPACE"}</div>
        <h1>{title}</h1>
        <p>{children}</p>
      </div>
      {action}
    </div>
  );
}
function useData(path, revision = 0) {
  const [data, setData] = useState(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    setLoading(true);
    api(path)
      .then((d) => {
        if (live) {
          setData(d);
          setError("");
        }
      })
      .catch((e) => {
        if (live) setError(e.message);
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [path, revision]);
  return { data, error, loading };
}
function DataError({ error, loading }) {
  return error ? (
    <div role="alert" className="error">
      {error}
    </div>
  ) : loading ? (
    <div className="loading">Loading your space…</div>
  ) : null;
}
function Chart({ daily = [] }) {
  const max = Math.max(...daily.map((d) => d.seconds), 60);
  return (
    <div className="chart" aria-label="Focus minutes over the last seven days">
      {daily.map((d) => (
        <div className="chart-column" key={d.date}>
          <span className="chart-value">{Math.round(d.seconds / 60)}</span>
          <div className="bar-track">
            <div
              className="bar"
              style={{ height: `${Math.max(3, (d.seconds / max) * 100)}%` }}
            />
          </div>
          <span>
            {new Date(d.date + "T12:00:00").toLocaleDateString([], {
              weekday: "short",
            })}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(getSession()?.user || null),
    [toast, setToast] = useState(""),
    [revision, setRevision] = useState(0),
    [menu, setMenu] = useState(false);
  const agent = useAgent(user);
  const navigate = useNavigate();
  useEffect(() => {
    if (getSession())
      api("/auth/me")
        .then(setUser)
        .catch(() => {
          saveSession(null);
          setUser(null);
        });
  }, []);
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(""), 6000);
      return () => clearTimeout(t);
    }
  }, [toast]);
  const previousFocus = useRef(null);
  useEffect(() => {
    if (previousFocus.current === "FOCUSING" && agent.state?.focus === "IDLE")
      setTimeout(() => setRevision((r) => r + 1), 6000);
    previousFocus.current = agent.state?.focus;
  }, [agent.state?.focus]);
  const refresh = () => setRevision((r) => r + 1);
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch (e) {
      setToast(e.message);
      return;
    }
    saveSession(null);
    setUser(null);
    navigate("/login");
  }
  const props = { user, setUser, agent, notify: setToast, revision, refresh };
  if (!user)
    return (
      <>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route
            path="/login"
            element={
              <Auth
                onLogin={(u) => {
                  setUser(u);
                  navigate("/dashboard");
                }}
              />
            }
          />
          <Route
            path="/signup"
            element={
              <Auth
                signup
                onLogin={(u) => {
                  setUser(u);
                  navigate("/dashboard");
                }}
              />
            }
          />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
        {toast && (
          <div role="status" className="toast">
            {toast}
          </div>
        )}
      </>
    );
  return (
    <div className="app">
      <aside className={`sidebar ${menu ? "open" : ""}`}>
        <Brand />
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {NAV.map(([path, label, Icon]) => (
            <NavLink onClick={() => setMenu(false)} key={path} to={path}>
              <Icon size={19} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="quiet-card">
            <div className="small-orbit">
              <Aperture size={25} />
            </div>
            <strong>
              A little less noise.
              <br />A little more you.
            </strong>
            <p>Make space for what matters.</p>
          </div>
          {user.role === "ADMIN" && (
            <NavLink to="/admin">
              <LockKeyhole size={18} />
              Admin console
            </NavLink>
          )}
          <NavLink to="/settings">
            <Settings size={18} />
            Settings
          </NavLink>
          <button className="profile" onClick={logout} title="Log out">
            <span className="avatar">{user.first_name?.[0] || "U"}</span>
            <span>
              <strong>{user.first_name}</strong>
              <small>Personal workspace</small>
            </span>
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Toggle navigation"
            onClick={() => setMenu(!menu)}
          >
            <Menu />
          </button>
          <span className="breadcrumb">
            Workspace <ChevronRight size={14} /> <strong>Focus Mode</strong>
          </span>
          <div className="top-actions">
            <span className={`status ${agent.connected ? "online" : ""}`}>
              <i />
              {agent.connected
                ? agent.state?.focus === "FOCUSING"
                  ? "Focusing"
                  : "Agent connected"
                : agent.status}
            </span>
            <Link className="help-link" to="/devices">
              <CircleHelp size={19} />
            </Link>
            <span className="avatar small">{user.first_name?.[0]}</span>
          </div>
        </header>
        {agent.state?.mode === "mock" && (
          <div className="mock-banner">
            Simulation mode · The companion is connected, but no windows will be
            changed.
          </div>
        )}
        {agent.state?.focus === "FOCUSING" && (
          <Link className="active-banner" to="/focus">
            Focus is on · {minutes(agent.state.remaining)} remaining{" "}
            <ArrowRight size={16} />
          </Link>
        )}
        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard {...props} />} />
            <Route path="/focus" element={<Focus {...props} />} />
            <Route path="/devices" element={<Devices {...props} />} />
            <Route path="/allowlist" element={<Allowlist {...props} />} />
            <Route path="/schedules" element={<Schedules {...props} />} />
            <Route path="/insights" element={<Insights {...props} />} />
            <Route path="/settings" element={<SettingsPage {...props} />} />
            <Route
              path="/admin"
              element={
                user.role === "ADMIN" ? (
                  <Admin {...props} />
                ) : (
                  <ErrorPage
                    code="403"
                    text="This space is for administrators."
                  />
                )
              }
            />
            <Route
              path="/login"
              element={<Navigate to="/dashboard" replace />}
            />
            <Route
              path="*"
              element={
                <ErrorPage code="404" text="This page took a little break." />
              }
            />
          </Routes>
          <footer>
            <span>
              <ShieldCheck size={14} /> Your computer. Your control. Always.
            </span>
            <span>
              FOCUS MODE <span className="footer-dot">·</span> PS03
            </span>
          </footer>
        </main>
      </div>
      {toast && (
        <div role="status" className="toast">
          {toast}
        </div>
      )}
    </div>
  );
}

function Dashboard(props) {
  const { user, agent, revision } = props;
  const insight = useData("/insights", revision),
    history = useData("/sessions?limit=4", revision),
    schedules = useData("/schedules", revision);
  const data = insight.data || {};
  const [duration, setDuration] = useState(user.default_duration),
    [confirm, setConfirm] = useState(false);
  const navigate = useNavigate();
  const next = schedules.data
    ?.filter((s) => s.enabled && s.next_at)
    .sort((a, b) => new Date(a.next_at) - new Date(b.next_at))[0];
  return (
    <>
      <Heading
        eyebrow="LESS DISTRACTION. MORE INTENTION."
        title={`Make room for deep work, ${user.first_name.split(" ")[0]}.`}
        action={
          <span className="date-label">
            <CalendarDays size={16} />
            {new Date().toLocaleDateString([], {
              weekday: "short",
              month: "short",
              day: "numeric",
            })}
          </span>
        }
      >
        One task. A clear mind. A little progress that adds up.
      </Heading>
      <DataError {...insight} />
      <div className="dashboard-grid">
        <Card className="focus-card">
          <div className="card-top">
            <span className="pill">
              <span className="tiny-dot" /> YOUR NEXT FOCUS SESSION
            </span>
            <span className="quiet-label">
              <ShieldCheck size={14} /> Always in your control
            </span>
          </div>
          <div className="focus-card-content">
            <div>
              <h2>
                Good work starts <br />
                with a little space.
              </h2>
              <p>
                Let distracting apps step aside. <br />
                Keep your attention on what matters.
              </p>
              <label className="section-label">
                HOW LONG WOULD YOU LIKE TO FOCUS?
              </label>
              <div className="duration-options">
                {[25, 50, 60].map((n) => (
                  <button
                    className={duration === n ? "selected" : ""}
                    onClick={() => setDuration(n)}
                    key={n}
                  >
                    {n}
                    <span> min</span>
                  </button>
                ))}
                <input
                  aria-label="Custom duration in minutes"
                  type="number"
                  min="1"
                  max="240"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                />
              </div>
              <button
                className="primary start-button"
                disabled={!agent.connected || duration < 1 || duration > 240}
                onClick={() =>
                  agent.state?.focus === "FOCUSING"
                    ? navigate("/focus")
                    : setConfirm(true)
                }
              >
                <Play size={17} fill="currentColor" />
                {agent.state?.focus === "FOCUSING"
                  ? "Back to focus"
                  : "Start focus"}
                <ArrowRight size={18} />
              </button>
              <span className="under-button">
                {agent.connected
                  ? "Your browser and allowed apps stay available."
                  : "Connect your companion to start a session."}
              </span>
            </div>
            <div className="focus-art" aria-hidden="true">
              <div className="orbit outer" />
              <div className="orbit middle" />
              <div className="orbit inner" />
              <div className="orbit-center">
                <Aperture size={66} strokeWidth={1.2} />
              </div>
              <span className="orbit-point p1" />
              <span className="orbit-point p2" />
              <span className="art-label">
                <Sparkles size={13} /> A quieter kind of productive
              </span>
            </div>
          </div>
        </Card>
        <Card className="device-card">
          <div className="card-top">
            <h3>Your focus companion</h3>
            <Monitor size={19} />
          </div>
          <div className="device-illustration">
            <Laptop size={76} strokeWidth={1} />
            <span
              className={agent.connected ? "connected-dot" : "offline-dot"}
            />
          </div>
          <h3>{agent.state?.name || "Your workspace, connected"}</h3>
          <span className={`pill ${agent.connected ? "teal" : "amber"}`}>
            {agent.connected ? "Connected & ready" : "Waiting for your agent"}
          </span>
          <p>
            {agent.connected
              ? "Your companion handles focus safely, right on this computer."
              : "Install the desktop companion, then pair it with this workspace."}
          </p>
          <Link className="outline full" to="/devices">
            {agent.connected ? "Manage device" : "Connect a device"}
            <ArrowUpRight size={16} />
          </Link>
          <div className="local-note">
            <LockKeyhole size={12} /> Secure, local connection
          </div>
        </Card>
      </div>
      <div className="stats-grid">
        <Stat
          label="FOCUSED TODAY"
          value={minutes(data.today_seconds)}
          sub="A little progress goes a long way"
          Icon={Clock3}
          color="indigo"
        />
        <Stat
          label="CURRENT STREAK"
          value={`${data.streak || 0} days`}
          sub="Build your rhythm, one day at a time"
          Icon={Flame}
          color="orange"
        />
        <Stat
          label="SESSIONS FINISHED"
          value={String(data.sessions || 0)}
          sub={`${data.completion_rate || 0}% completion rate · all time`}
          Icon={Target}
          color="teal"
        />
      </div>
      <div className="bottom-grid">
        <Card>
          <div className="card-top">
            <div>
              <h3>Your week in focus</h3>
              <p className="small-text">Small steps. Meaningful momentum.</p>
            </div>
            <Link className="text-link" to="/insights">
              View insights <ArrowUpRight size={15} />
            </Link>
          </div>
          <Chart daily={data.daily} />
          <div className="chart-footer">
            <span className="legend-dot" /> Focus time{" "}
            <span className="muted">in minutes · real sessions only</span>
          </div>
        </Card>
        <Card>
          <div className="card-top">
            <h3>Up next</h3>
            <CalendarDays size={19} />
          </div>
          {next ? (
            <div className="next-schedule">
              <span className="schedule-icon">
                <CalendarDays />
              </span>
              <h2>{next.name}</h2>
              <p>
                {next.start_time.slice(0, 5)} · {next.duration_minutes} minutes
              </p>
              <span className="small-text">
                {next.timezone} · device must be running
              </span>
            </div>
          ) : (
            <Empty title="Find your focus rhythm">
              Make deep work a regular part of your day with a recurring
              session.
            </Empty>
          )}
          <Link className="text-link" to="/schedules">
            <Plus size={16} /> {next ? "Manage schedules" : "Create a schedule"}
          </Link>
        </Card>
      </div>
      <Card className="history-card">
        <div className="card-top">
          <h3>Recent sessions</h3>
          <Link className="text-link" to="/insights">
            View all <ArrowRight size={15} />
          </Link>
        </div>
        <DataError {...history} />
        <SessionTable rows={history.data?.items || []} />
      </Card>
      {confirm && (
        <Confirm
          {...props}
          duration={duration}
          close={() => setConfirm(false)}
        />
      )}
    </>
  );
}
function Stat({ label, value, sub, Icon, color }) {
  return (
    <Card className="stat">
      <span className={`stat-icon ${color}`}>
        <Icon size={21} />
      </span>
      <div>
        <span className="stat-label">{label}</span>
        <strong>{value}</strong>
        <p>{sub}</p>
      </div>
    </Card>
  );
}
function SessionTable({ rows }) {
  return rows.length ? (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Session</th>
            <th>Device</th>
            <th>Actual / planned</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>
                <strong>{date(r.started_at)}</strong>
                <small>
                  {r.source.toLowerCase()}{" "}
                  {r.mode === "mock" ? "· simulation" : ""}
                </small>
              </td>
              <td>{r.device_name}</td>
              <td>
                {minutes(r.actual_seconds)} / {r.planned_minutes} min
              </td>
              <td>
                <span
                  className={`pill ${r.status === "COMPLETED" ? "teal" : ""}`}
                >
                  {r.status.toLowerCase()}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty title="Your first focused moment is ahead">
      Completed sessions will appear here. Start when you’re ready.
    </Empty>
  );
}
function Confirm({ agent, duration, close, notify }) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const dialog = useRef();
  useEffect(() => {
    dialog.current.showModal();
  }, []);
  async function start() {
    setBusy(true);
    // Must run directly inside the confirmation gesture, before awaiting the agent.
    const requestedFullscreen =
      !document.fullscreenElement && document.fullscreenEnabled;
    const fullscreenRequest = requestedFullscreen
      ? document.documentElement
          .requestFullscreen()
          .then(() => true)
          .catch(() => false)
      : Promise.resolve(Boolean(document.fullscreenElement));
    try {
      await agent.command("enterFocus", {
        durationMin: duration,
        confirmed: true,
      });
      close();
      navigate("/focus");
      if (!(await fullscreenRequest))
        notify(
          "Browser fullscreen was unavailable. Use Enter fullscreen or F11.",
        );
    } catch (e) {
      if (
        (await fullscreenRequest) &&
        requestedFullscreen &&
        document.fullscreenElement
      ) {
        await document.exitFullscreen().catch(() => {});
      }
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog ref={dialog} onCancel={close}>
      <div className="card-top">
        <span className="stat-icon indigo">
          <ShieldCheck />
        </span>
        <button
          className="icon-button"
          aria-label="Close confirmation"
          onClick={close}
        >
          <X />
        </button>
      </div>
      <h2>A little space to focus.</h2>
      <p>
        {agent.state?.mode === "mock"
          ? "This is a simulation. No windows will change."
          : "The dashboard opens fullscreen. The companion minimizes eligible distracting windows and keeps minimizing them if reopened or newly launched until focus ends. Nothing is closed and unsaved work stays intact."}
      </p>
      <div className="consent-box">
        <strong>These stay available</strong>
        <p>Supported browsers · Focus Mode · Windows system apps</p>
        <p>{agent.state?.apps.join(", ") || "No additional apps selected"}</p>
      </div>
      <p>
        Allowed apps stay usable. End focus from the dashboard or companion to
        stop app enforcement and restore changed windows. Esc leaves fullscreen
        without ending the session.
      </p>
      <div className="error" hidden={!error}>
        {error}
      </div>
      <button disabled={busy} className="primary full" onClick={start}>
        {busy
          ? "Waiting for companion…"
          : `Confirm & focus for ${duration} minutes`}
      </button>
      <button className="plain full" onClick={close}>
        Not right now
      </button>
    </dialog>
  );
}
function Focus({ agent, notify }) {
  const s = agent.state;
  const screen = useRef(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenError, setFullscreenError] = useState("");
  useEffect(() => {
    const element = screen.current;
    document.body.classList.add("focus-page-active");
    const ownsFullscreen = () =>
      document.fullscreenElement === element ||
      document.fullscreenElement === document.documentElement;
    const update = () => setFullscreen(ownsFullscreen());
    update();
    document.addEventListener("fullscreenchange", update);
    return () => {
      document.removeEventListener("fullscreenchange", update);
      document.body.classList.remove("focus-page-active");
      if (ownsFullscreen()) {
        document.exitFullscreen().catch(() => {});
      }
    };
  }, []);
  useEffect(() => {
    if (s?.focus === "IDLE" && document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
  }, [s?.focus]);
  async function toggleFullscreen() {
    setFullscreenError("");
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        if (!document.fullscreenEnabled || !screen.current.requestFullscreen) {
          throw new Error("Fullscreen unavailable");
        }
        await screen.current.requestFullscreen();
      }
    } catch {
      setFullscreenError(
        "Fullscreen could not open. Open this dashboard in Chrome or Edge and try again, or press F11.",
      );
    }
  }
  const remaining = s?.remaining || 0;
  const total = (s?.session?.planned_minutes || 25) * 60;
  return (
    <div className="focus-screen" ref={screen}>
      <span className="pill teal">
        {s?.focus === "FOCUSING" ? "FOCUS MODE IS ON" : "YOUR FOCUS SPACE"}
      </span>
      <h1>
        {s?.focus === "FOCUSING"
          ? "Just you and what matters."
          : "Ready when you are."}
      </h1>
      <p>
        {!agent.connected
          ? "Connection lost. The companion still owns the timer. Use its End Focus button if needed."
          : "Breathe in. Settle down. Take it one thing at a time."}
      </p>
      <div
        className="timer-ring"
        style={{ "--progress": `${(remaining / total) * 100}%` }}
      >
        <div>
          <strong>
            {String(Math.floor(remaining / 60)).padStart(2, "0")}
            <span>:</span>
            {String(remaining % 60).padStart(2, "0")}
          </strong>
          <span>{s?.mode === "mock" ? "SIMULATION" : "TIME TO FOCUS"}</span>
        </div>
      </div>
      <p className="preserved">
        <ShieldCheck size={18} /> Browsers, agent and system apps stay available
      </p>
      <p>{s?.session?.apps.join(" · ")}</p>
      {s?.focus === "FOCUSING" && (
        <>
          <p className="window-result">
            {s?.mode === "mock"
              ? "Simulation: no real windows were minimized."
              : typeof s?.result?.changed === "number"
                ? `${s.result.changed} window${s.result.changed === 1 ? "" : "s"} managed this session. ${s.result.enforcing ? "App enforcement is active." : "Restart the companion to enable continuous enforcement."}`
                : "Waiting for the companion's window report."}
          </p>
          <button className="fullscreen-button" onClick={toggleFullscreen}>
            {fullscreen ? "Exit fullscreen" : "Enter fullscreen"}
          </button>
          <small>Esc leaves fullscreen. Your focus timer keeps running.</small>
          {fullscreenError && <p role="alert">{fullscreenError}</p>}
        </>
      )}
      {s?.focus === "FOCUSING" ? (
        <button
          className="end-button"
          onClick={() =>
            agent
              .command("exitFocus")
              .then(() => notify("Focus ended. Restoration requested."))
              .catch((e) => notify(e.message))
          }
        >
          <Square size={17} /> End focus
        </button>
      ) : (
        <Link className="primary" to="/dashboard">
          Back to overview
        </Link>
      )}
      {s?.focus !== "FOCUSING" && s?.pending_restore > 0 && (
        <p role="alert">
          Some windows need manual restoration. Check the companion.
        </p>
      )}
      {s?.result?.error && <p role="alert">{s.result.error}</p>}
      <small>Your session continues even if you close this tab.</small>
    </div>
  );
}

function Devices({ agent, notify, revision, refresh }) {
  const result = useData("/devices", revision),
    downloads = useData("/downloads");
  const [code, setCode] = useState(""),
    [busy, setBusy] = useState(false);
  async function pair(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await agent.pair(code);
      notify("Companion paired successfully");
      setCode("");
      refresh();
    } catch (e) {
      notify(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading title="A companion for your focus.">
        A secure connection between your workspace and your own computer.
      </Heading>
      <div className="two-columns">
        <Card>
          <h3>Pair this computer</h3>
          <p>
            Open the desktop companion and enter the six-digit code shown in its
            window.
          </p>
          <form onSubmit={pair}>
            <Field label="Pairing code">
              <input
                className="code-input"
                placeholder="000000"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength="6"
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </Field>
            <button className="primary" disabled={busy}>
              {busy ? "Pairing…" : "Pair companion"}
              <ArrowRight size={16} />
            </button>
          </form>
          <p className="small-text">
            Codes expire in 3 minutes. To pair another browser tab, unpair
            locally and generate a new code.
          </p>
        </Card>
        <Card>
          <h3>Set up in three small steps</h3>
          <ol className="steps">
            <li>Install and open the Windows companion.</li>
            <li>Keep the companion visible and enter its local code.</li>
            <li>Choose your allowed apps, then start a session.</li>
          </ol>
          {downloads.data
            ?.filter((d) => d.url)
            .map((d) => (
              <a className="outline" href={d.url} key={d.id}>
                <Download size={16} />
                Download for {d.platform}
              </a>
            ))}
          {!downloads.data?.some((d) => d.url) && (
            <p className="notice">
              No hosted installer has been published. Run{" "}
              <code>python agent/main.py --adapter windows</code> from your
              configured project environment. See README for setup.
            </p>
          )}
        </Card>
      </div>
      <Card>
        <h3>Your paired devices</h3>
        <DataError {...result} />
        {result.data?.items.length ? (
          result.data.items.map((d) => (
            <div className="list-row" key={d.id}>
              <Monitor />
              <div className="grow">
                <strong>{d.name}</strong>
                <small>
                  {d.os} · Last seen{" "}
                  {d.last_seen ? date(d.last_seen) : "not yet synced"}
                </small>
              </div>
              <span className="pill">
                {agent.connected && agent.state?.deviceId === d.id
                  ? "Connected"
                  : "Not locally connected"}
              </span>
              <button
                className="danger-text"
                onClick={() =>
                  api(`/devices/${d.id}`, { method: "DELETE" })
                    .then(() => {
                      refresh();
                      notify(
                        "Device revoked. Agent will stop at its next sync.",
                      );
                    })
                    .catch((e) => notify(e.message))
                }
              >
                Unpair
              </button>
            </div>
          ))
        ) : (
          <Empty title="No devices paired yet">
            Your computer will appear here after pairing.
          </Empty>
        )}
      </Card>
    </>
  );
}

function Allowlist({ notify, revision, refresh }) {
  const result = useData("/allowlist", revision);
  const [name, setName] = useState("");
  async function save(apps) {
    try {
      await api("/allowlist", { method: "PUT", body: { apps } });
      refresh();
      notify("Allowed apps saved. Applies to the next session.");
    } catch (e) {
      notify(e.message);
    }
  }
  return (
    <>
      <Heading title="Keep your essentials close.">
        These apps stay available while everything else takes a step back.
      </Heading>
      <DataError {...result} />
      <Card>
        <div className="card-top">
          <h3>Always protected</h3>
          <span className="pill teal">
            <LockKeyhole size={12} /> Locked for your safety
          </span>
        </div>
        {(result.data?.protected || []).map((a) => (
          <div className="list-row" key={a}>
            <ShieldCheck className="teal-ink" />
            <strong className="grow">{a}</strong>
            <LockKeyhole size={16} />
          </div>
        ))}
      </Card>
      <Card>
        <h3>Your allowed apps</h3>
        <p>
          Add an application’s executable name, for example{" "}
          <code>Code.exe</code>.
        </p>
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            save([...(result.data?.apps || []), name]);
            setName("");
          }}
        >
          <input
            aria-label="Application executable"
            required
            pattern="[A-Za-z0-9 ._-]+\.exe"
            placeholder="Code.exe"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button className="primary">
            <Plus size={17} /> Add app
          </button>
        </form>
        {result.data?.apps.map((a) => (
          <div className="list-row" key={a}>
            <Monitor />
            <strong className="grow">{a}</strong>
            <button
              className="plain"
              onClick={() => save(result.data.apps.filter((x) => x !== a))}
            >
              Remove
            </button>
          </div>
        ))}
        {result.data?.apps.length === 0 && (
          <Empty title="Just the essentials, for now">
            Add the tools you use for your best work.
          </Empty>
        )}
      </Card>
      <Card>
        <h3>A helpful head start</h3>
        <p>Apply an administrator’s preset to your existing list.</p>
        <div className="chips">
          {result.data?.presets.map((p) => (
            <button
              className="outline"
              key={p.id}
              onClick={() =>
                save([...new Set([...result.data.apps, ...p.apps])])
              }
            >
              <Plus size={15} />
              {p.name}
            </button>
          ))}
        </div>
      </Card>
    </>
  );
}

function Schedules({ notify, revision, refresh, user }) {
  const result = useData("/schedules", revision),
    devices = useData("/devices", revision);
  const [editing, setEditing] = useState(null);
  const blank = {
    name: "Morning deep work",
    days: [0, 1, 2, 3, 4],
    start_time: "09:00",
    duration_minutes: 25,
    timezone: user.timezone,
    device: "",
    enabled: true,
    consent: false,
  };
  const [form, setForm] = useState(blank);
  const update = (key, value) => setForm({ ...form, [key]: value });
  async function save(e) {
    e.preventDefault();
    try {
      await api(editing ? `/schedules/${editing}` : "/schedules", {
        method: editing ? "PATCH" : "POST",
        body: form,
      });
      setEditing(null);
      setForm(blank);
      refresh();
      notify("Schedule saved");
    } catch (e) {
      notify(e.message);
    }
  }
  return (
    <>
      <Heading title="Give focus a place in your day.">
        A gentle routine, with a heads-up before every scheduled session.
      </Heading>
      <div className="two-columns">
        <Card>
          <h3>{editing ? "Edit schedule" : "Create a routine"}</h3>
          <form onSubmit={save}>
            <Field label="Name">
              <input
                required
                maxLength="80"
                value={form.name}
                onChange={(e) => update("name", e.target.value)}
              />
            </Field>
            <Field label="Device">
              <select
                required
                value={form.device}
                onChange={(e) => update("device", e.target.value)}
              >
                <option value="">Choose a paired device</option>
                {devices.data?.items.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </Field>
            <div className="day-picker">
              {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => (
                <button
                  aria-label={
                    [
                      "Monday",
                      "Tuesday",
                      "Wednesday",
                      "Thursday",
                      "Friday",
                      "Saturday",
                      "Sunday",
                    ][i]
                  }
                  type="button"
                  className={form.days.includes(i) ? "selected" : ""}
                  key={i}
                  onClick={() =>
                    update(
                      "days",
                      form.days.includes(i)
                        ? form.days.filter((x) => x !== i)
                        : [...form.days, i],
                    )
                  }
                >
                  {d}
                </button>
              ))}
            </div>
            <div className="two-fields">
              <Field label="Start time">
                <input
                  type="time"
                  required
                  value={form.start_time}
                  onChange={(e) => update("start_time", e.target.value)}
                />
              </Field>
              <Field label="Minutes">
                <input
                  type="number"
                  min="1"
                  max="240"
                  required
                  value={form.duration_minutes}
                  onChange={(e) =>
                    update("duration_minutes", Number(e.target.value))
                  }
                />
              </Field>
            </div>
            <Field label="IANA timezone">
              <input
                required
                value={form.timezone}
                onChange={(e) => update("timezone", e.target.value)}
              />
            </Field>
            <label className="checkbox">
              <input
                required
                type="checkbox"
                checked={form.consent}
                onChange={(e) => update("consent", e.target.checked)}
              />
              I allow this routine to minimize other apps. Browsers and allowed
              apps remain available. The companion gives 15 seconds to cancel.
            </label>
            <button className="primary">Save schedule</button>
            {editing && (
              <button
                className="plain"
                type="button"
                onClick={() => {
                  setEditing(null);
                  setForm(blank);
                }}
              >
                Cancel edit
              </button>
            )}
          </form>
        </Card>
        <div>
          <DataError {...result} />
          {result.data?.length ? (
            result.data.map((s) => (
              <Card key={s.id}>
                <div className="card-top">
                  <span className="stat-icon indigo">
                    <CalendarDays />
                  </span>
                  <span className={`pill ${s.enabled ? "teal" : ""}`}>
                    {s.enabled ? "Enabled" : "Paused"}
                  </span>
                </div>
                <h2>{s.name}</h2>
                <p>
                  {s.start_time.slice(0, 5)} · {s.duration_minutes} min ·{" "}
                  {s.timezone}
                </p>
                <p>
                  {s.days
                    .map(
                      (d) =>
                        ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d],
                    )
                    .join(" · ")}
                </p>
                <div className="chips">
                  <button
                    className="outline"
                    onClick={() => {
                      setEditing(s.id);
                      setForm(s);
                    }}
                  >
                    Edit
                  </button>
                  <button
                    className="plain"
                    onClick={() =>
                      api(`/schedules/${s.id}`, {
                        method: "PATCH",
                        body: { enabled: !s.enabled },
                      })
                        .then(refresh)
                        .catch((e) => notify(e.message))
                    }
                  >
                    {s.enabled ? "Pause" : "Enable"}
                  </button>
                  <button
                    className="danger-text"
                    onClick={() =>
                      api(`/schedules/${s.id}`, { method: "DELETE" })
                        .then(refresh)
                        .catch((e) => notify(e.message))
                    }
                  >
                    Delete
                  </button>
                </div>
              </Card>
            ))
          ) : (
            <Card>
              <Empty title="A routine worth keeping">
                Your scheduled sessions will appear here.
              </Empty>
            </Card>
          )}
          <div className="notice">
            The companion must be running and synced. Missed sessions are
            recorded, never started late. Sleep or an overlapping session can
            cause a missed run.
          </div>
        </div>
      </div>
    </>
  );
}

function Insights({ revision }) {
  const [status, setStatus] = useState(""),
    [page, setPage] = useState(1),
    [from, setFrom] = useState(""),
    [to, setTo] = useState("");
  const result = useData("/insights", revision),
    history = useData(
      `/sessions?limit=10&page=${page}&status=${status}&from=${from}&to=${to}`,
      revision,
    );
  const d = result.data || {};
  return (
    <>
      <Heading title="Progress, at your own pace.">
        A little perspective on the time you made for what matters.
      </Heading>
      <DataError {...result} />
      <div className="stats-grid">
        <Stat
          label="TOTAL FOCUS"
          value={minutes(d.total_seconds)}
          sub="Actual time from real sessions"
          Icon={Clock3}
          color="indigo"
        />
        <Stat
          label="CURRENT STREAK"
          value={`${d.streak || 0} days`}
          sub="Consecutive days with focus time"
          Icon={Flame}
          color="orange"
        />
        <Stat
          label="COMPLETION RATE"
          value={`${d.completion_rate || 0}%`}
          sub="Timed completions / ended sessions"
          Icon={Target}
          color="teal"
        />
      </div>
      <Card>
        <div className="card-top">
          <h3>The last seven days</h3>
          <span className="muted">
            {d.best_hour !== null && d.best_hour !== undefined
              ? `Best starting hour: ${d.best_hour}:00`
              : "Your rhythm is still taking shape"}
          </span>
        </div>
        <Chart daily={d.daily} />
      </Card>
      <Card>
        <div className="card-top">
          <h3>Session history</h3>
          <select
            aria-label="Filter session status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All sessions</option>
            {["ACTIVE", "COMPLETED", "CANCELLED"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="two-fields">
          <Field label="From">
            <input
              type="date"
              value={from}
              onChange={(e) => {
                setFrom(e.target.value);
                setPage(1);
              }}
            />
          </Field>
          <Field label="To">
            <input
              type="date"
              value={to}
              onChange={(e) => {
                setTo(e.target.value);
                setPage(1);
              }}
            />
          </Field>
        </div>
        <DataError {...history} />
        <SessionTable rows={history.data?.items || []} />
        <div className="pagination">
          <button
            className="plain"
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </button>
          <span>Page {page}</span>
          <button
            className="plain"
            disabled={page >= (history.data?.totalPages || 1)}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      </Card>
      {d.missed?.length > 0 && (
        <Card>
          <h3>Missed scheduled sessions</h3>
          {d.missed.map((m) => (
            <div className="list-row" key={m.occurrence}>
              {date(m.at)}
              <span className="muted">{m.reason}</span>
            </div>
          ))}
        </Card>
      )}
      <p className="small-text">
        Simulation sessions remain visible in history but are excluded from
        focus metrics. Times are grouped by the timezone in your profile.
      </p>
    </>
  );
}

function SettingsPage({ user, setUser, notify }) {
  const [form, setForm] = useState(user),
    [old, setOld] = useState(""),
    [password, setPassword] = useState("");
  return (
    <>
      <Heading title="Make this space yours.">
        The small preferences that make focus feel natural.
      </Heading>
      <div className="two-columns">
        <Card>
          <h3>Your profile</h3>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                const u = await api("/auth/me", {
                  method: "PATCH",
                  body: form,
                });
                setUser(u);
                saveSession({ ...getSession(), user: u });
                notify("Preferences saved");
              } catch (e) {
                notify(e.message);
              }
            }}
          >
            <Field label="Name">
              <input
                required
                value={form.first_name}
                onChange={(e) =>
                  setForm({ ...form, first_name: e.target.value })
                }
              />
            </Field>
            <Field label="Email">
              <input disabled value={user.email} />
            </Field>
            <Field label="Default session length (minutes)">
              <input
                type="number"
                min="1"
                max="240"
                required
                value={form.default_duration}
                onChange={(e) =>
                  setForm({ ...form, default_duration: Number(e.target.value) })
                }
              />
            </Field>
            <Field label="Timezone">
              <input
                required
                value={form.timezone}
                onChange={(e) => setForm({ ...form, timezone: e.target.value })}
              />
            </Field>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={form.notifications}
                onChange={(e) =>
                  setForm({ ...form, notifications: e.target.checked })
                }
              />
              Save notification preference (OS notifications not yet
              implemented)
            </label>
            <button className="primary">Save preferences</button>
          </form>
        </Card>
        <div>
          <Card>
            <h3>Change password</h3>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  await api("/auth/password", {
                    method: "POST",
                    body: { old_password: old, password },
                  });
                  saveSession(null);
                  setUser(null);
                } catch (e) {
                  notify(e.message);
                }
              }}
            >
              <Field label="Current password">
                <input
                  autoComplete="current-password"
                  type="password"
                  required
                  value={old}
                  onChange={(e) => setOld(e.target.value)}
                />
              </Field>
              <Field label="New password">
                <input
                  autoComplete="new-password"
                  type="password"
                  minLength="10"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>
              <button className="outline">Update password & log out</button>
            </form>
          </Card>
          <Card>
            <h3>Device access</h3>
            <p>
              Revoke all paired devices. Running companions stop focus when they
              next reach the backend.
            </p>
            <button
              className="danger-text"
              onClick={() =>
                api("/devices", { method: "DELETE" })
                  .then(() => notify("All device credentials revoked"))
                  .catch((e) => notify(e.message))
              }
            >
              Unpair all devices
            </button>
            <p>
              <Link className="text-link" to="/devices">
                Companion setup and downloads <ArrowUpRight size={15} />
              </Link>
            </p>
          </Card>
        </div>
      </div>
    </>
  );
}

function Admin({ notify, revision, refresh }) {
  const result = useData("/admin", revision),
    [name, setName] = useState(""),
    [apps, setApps] = useState(""),
    [url, setUrl] = useState("");
  const d = result.data;
  return (
    <>
      <Heading
        eyebrow="PLATFORM ADMINISTRATION"
        title="A healthy focus community."
      >
        Manage access, useful presets, and companion downloads.
      </Heading>
      <DataError {...result} />
      {d && (
        <>
          <div className="stats-grid">
            <Stat
              label="USERS"
              value={d.stats.users}
              sub="Registered accounts"
              Icon={Monitor}
              color="indigo"
            />
            <Stat
              label="DEVICES"
              value={d.stats.devices}
              sub="Paired and not revoked"
              Icon={Laptop}
              color="teal"
            />
            <Stat
              label="TOTAL FOCUS"
              value={minutes(d.stats.seconds)}
              sub="Aggregate real focus time"
              Icon={Clock3}
              color="orange"
            />
          </div>
          <Card>
            <h3>User access</h3>
            {d.users.items.map((u) => (
              <div className="list-row" key={u.id}>
                <span className="avatar">{u.first_name[0]}</span>
                <div className="grow">
                  <strong>{u.first_name}</strong>
                  <small>
                    {u.email} · {u.role}
                  </small>
                </div>
                <button
                  className="outline"
                  onClick={() =>
                    api(`/admin/users/${u.id}`, {
                      method: "PATCH",
                      body: { is_active: !u.is_active },
                    })
                      .then(() => {
                        refresh();
                        notify("User access updated");
                      })
                      .catch((e) => notify(e.message))
                  }
                >
                  {u.is_active ? "Deactivate" : "Activate"}
                </button>
              </div>
            ))}
          </Card>
          <div className="two-columns">
            <Card>
              <h3>Publish a preset</h3>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  api("/admin/presets", {
                    method: "POST",
                    body: {
                      name,
                      apps: apps
                        .split(",")
                        .map((s) => s.trim())
                        .filter(Boolean),
                    },
                  })
                    .then(() => {
                      refresh();
                      setName("");
                      setApps("");
                    })
                    .catch((e) => notify(e.message));
                }}
              >
                <Field label="Preset name">
                  <input
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </Field>
                <Field label="Executable names, comma separated">
                  <input
                    required
                    placeholder="Code.exe, Notepad.exe"
                    value={apps}
                    onChange={(e) => setApps(e.target.value)}
                  />
                </Field>
                <button className="primary">Publish preset</button>
              </form>
              {d.presets.map((p) => (
                <div className="list-row" key={p.id}>
                  <strong className="grow">{p.name}</strong>
                  <button
                    className="danger-text"
                    onClick={() =>
                      api(`/admin/presets/${p.id}`, { method: "DELETE" })
                        .then(refresh)
                        .catch((e) => notify(e.message))
                    }
                  >
                    Delete
                  </button>
                </div>
              ))}
            </Card>
            <Card>
              <h3>Windows download</h3>
              <p>Publish the HTTPS address of your reviewed companion build.</p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const existing = d.downloads.find(
                    (x) => x.platform === "Windows",
                  );
                  api(
                    existing
                      ? `/admin/downloads/${existing.id}`
                      : "/admin/downloads",
                    {
                      method: existing ? "PATCH" : "POST",
                      body: { platform: "Windows", url, version: "1.0.0" },
                    },
                  )
                    .then(() => {
                      refresh();
                      notify("Download link updated");
                    })
                    .catch((e) => notify(e.message));
                }}
              >
                <Field label="HTTPS build URL">
                  <input
                    type="url"
                    required
                    placeholder="https://…/FocusMode.exe"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                  />
                </Field>
                <button className="primary">Save download link</button>
              </form>
              {d.downloads.map((x) => (
                <p key={x.id}>
                  {x.platform}: {x.url || "Not published"}
                </p>
              ))}
            </Card>
          </div>
        </>
      )}
    </>
  );
}

function ErrorPage({ code, text }) {
  return (
    <Empty title={`${code} · ${text}`}>
      <Link to="/dashboard" className="text-link">
        Return to your workspace
      </Link>
    </Empty>
  );
}
function Auth({ signup = false, onLogin }) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <div className="auth-page">
      <div className="auth-art">
        <Brand />
        <div>
          <span className="eyebrow">LESS NOISE. MORE POSSIBILITY.</span>
          <h1>
            Your attention
            <br />
            is worth
            <br />
            <em>protecting.</em>
          </h1>
          <p>
            A calmer computer.
            <br />A clearer mind. A little more progress.
          </p>
          <div className="auth-orbit">
            <Aperture size={100} strokeWidth={0.8} />
          </div>
        </div>
        <small>Personal focus. Always in your control.</small>
      </div>
      <div className="auth-form">
        <Link className="text-link" to="/">
          ← Back to home
        </Link>
        <h1>{signup ? "Make space for your best work." : "Welcome back."}</h1>
        <p>
          {signup
            ? "Create your personal focus workspace."
            : "A little focus can change your day."}
        </p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            const data = Object.fromEntries(new FormData(e.currentTarget));
            try {
              const session = await api(
                `/auth/${signup ? "register" : "login"}`,
                { method: "POST", body: data },
              );
              saveSession(session);
              onLogin(session.user);
            } catch (e) {
              setError(e.message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {signup && (
            <Field label="Your name">
              <input
                name="name"
                autoComplete="given-name"
                required
                maxLength="100"
              />
            </Field>
          )}
          <Field label="Email address">
            <input
              type="email"
              name="email"
              autoComplete="email"
              required
              placeholder="you@example.com"
            />
          </Field>
          <Field label="Password">
            <input
              type="password"
              name="password"
              autoComplete={signup ? "new-password" : "current-password"}
              minLength={signup ? 10 : 1}
              required
            />
          </Field>
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
          <button className="primary full" disabled={busy}>
            {busy ? "One moment…" : signup ? "Create your account" : "Log in"}
            <ArrowRight size={18} />
          </button>
        </form>
        <p>
          {signup ? "Already have a workspace?" : "New to Focus Mode?"}{" "}
          <Link className="text-link" to={signup ? "/login" : "/signup"}>
            {signup ? "Log in" : "Create an account"}
          </Link>
        </p>
        <span className="privacy-note">
          <ShieldCheck size={15} />
          Your activity stays yours. No window titles collected.
        </span>
      </div>
    </div>
  );
}
function Landing() {
  return (
    <div className="landing">
      <header>
        <Brand />
        <nav>
          <a href="#how">How it works</a>
          <Link to="/login">Log in</Link>
          <Link className="primary" to="/signup">
            Find your focus <ArrowUpRight size={16} />
          </Link>
        </nav>
      </header>
      <section className="landing-hero">
        <span className="pill">
          <span className="tiny-dot" /> A LITTLE LESS DISTRACTION
        </span>
        <h1>
          Make room for
          <br />
          <em>what matters.</em>
        </h1>
        <p>
          Give your attention a place to land. Focus Mode gently moves
          <br />
          distracting apps aside, so you can get into your best work.
        </p>
        <Link className="primary" to="/signup">
          Create your focus space <ArrowRight size={18} />
        </Link>
        <span className="privacy-note">
          <ShieldCheck size={15} />
          Your computer. Your control. Always.
        </span>
        <div className="landing-orbit" aria-hidden="true">
          <Aperture size={190} strokeWidth={0.65} />
        </div>
      </section>
      <section id="how" className="landing-steps">
        {[
          [
            "01",
            "A small companion",
            "Run the visible Windows app. It is your safe bridge from browser to computer.",
          ],
          [
            "02",
            "A connection you choose",
            "Pair using a short-lived code shown only on your computer.",
          ],
          [
            "03",
            "A little space to focus",
            "Choose a duration, review what stays open, and focus. End it whenever you like.",
          ],
        ].map(([n, t, p]) => (
          <Card key={n}>
            <span className="eyebrow">{n}</span>
            <h2>{t}</h2>
            <p>{p}</p>
          </Card>
        ))}
      </section>
      <div className="landing-note">
        Windows companion available from your project build. No public installer
        published yet. <Link to="/login">Log in for setup guidance →</Link>
      </div>
    </div>
  );
}
