import { useEffect, useRef, useState } from "react";
import { Overview } from "../features/overview";
import { RunDetail, RunForm, RunList } from "../features/runs";
import {
  RobotDetail,
  RobotForm,
  RobotList,
  RobotVersionForm,
} from "../features/robots";
import { Projects } from "../features/projects";
import { Agents } from "../features/agents";
import { Skills } from "../features/skills";
import { Runners } from "../features/runners";
import { Settings } from "../features/settings";
import { fetchHealth } from "./health";
import { BrandIdentity } from "../shared/BrandIdentity";
import type { Health } from "./health";
import { Modal, Notice, PageHead, useResource } from "../shared/ui";
import {
  OverviewIcon,
  ProjectsIcon,
  RunsIcon,
  AgentsIcon,
  SkillsIcon,
  RobotsIcon,
  PcIcon,
  SettingsIcon,
  MenuIcon,
} from "../shared/icons";
import type { Robot } from "../features/robots";
import type { RecordData } from "../shared/api";

const menus = [
  { id: "overview", label: "Overview", Icon: OverviewIcon, group: "" },
  { id: "projects", label: "Projects", Icon: ProjectsIcon, group: "CÔNG VIỆC" },
  { id: "runs", label: "Runs", Icon: RunsIcon, group: "" },
  { id: "agents", label: "Agent điều phối", Icon: AgentsIcon, group: "ĐIỀU PHỐI" },
  { id: "skills", label: "Skills", Icon: SkillsIcon, group: "" },
  { id: "robots", label: "Robots", Icon: RobotsIcon, group: "" },
  { id: "pc", label: "PC", Icon: PcIcon, group: "HỆ THỐNG" },
  { id: "settings", label: "Settings", Icon: SettingsIcon, group: "" },
];

function RobotScreen({ id, mode }: { id?: string; mode?: string }) {
  const robot = useResource<RecordData>(
    id && id !== "new" ? `/v1/robots/${encodeURIComponent(id)}` : "/v1/robots",
  );
  const go = (suffix = "") => {
    window.location.hash = `robots${suffix}`;
  };
  if (!id)
    return (
      <RobotList
        onSelectRobot={(id) => go(`/${encodeURIComponent(id)}`)}
        onNewRobot={() => go("/new")}
        onEditRobot={(r) => go(`/${encodeURIComponent(r.id)}/edit`)}
        onNewVersion={(id) => go(`/${encodeURIComponent(id)}/new-version`)}
      />
    );
  if (id === "new")
    return (
      <RobotForm
        onCancel={() => go()}
        onSuccess={(r) => go(`/${encodeURIComponent(r.id)}`)}
      />
    );
  if (robot.error) return <Notice error>{robot.error}</Notice>;
  if (!robot.data) return <Notice>Đang tải Robot…</Notice>;
  if (mode === "edit")
    return (
      <RobotForm
        initialRobot={robot.data as Robot}
        onCancel={() => go(`/${encodeURIComponent(id)}`)}
        onSuccess={(r) => go(`/${encodeURIComponent(r.id)}`)}
      />
    );
  if (mode === "new-version")
    return (
      <RobotVersionForm
        robot={robot.data as Robot}
        onCancel={() => go(`/${encodeURIComponent(id)}`)}
        onSuccess={() => go(`/${encodeURIComponent(id)}`)}
      />
    );
  return (
    <RobotDetail
      robotId={id}
      onBack={() => go()}
      onEdit={(r) => go(`/${encodeURIComponent(r.id)}/edit`)}
      onNewVersion={(id) => go(`/${encodeURIComponent(id)}/new-version`)}
    />
  );
}

export function App() {
  const [hash, setHash] = useState(window.location.hash);
  const acceptedHash = useRef(window.location.hash);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState("");
  const [checking, setChecking] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [switcher, setSwitcher] = useState(false);
  const [search, setSearch] = useState("");
  useEffect(() => {
    const change = () => {
      if (
        document.querySelector('[data-unsaved="true"]') &&
        !window.confirm("Có thay đổi chưa lưu trong Process. Rời editor?")
      ) {
        window.history.replaceState(
          null,
          "",
          acceptedHash.current || "#overview",
        );
        return;
      }
      acceptedHash.current = window.location.hash;
      setHash(window.location.hash);
      setMobileOpen(false);
    };
    window.addEventListener("hashchange", change);
    return () => window.removeEventListener("hashchange", change);
  }, []);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSwitcher((v) => !v);
      }
      if (e.key === "Escape") {
        setSwitcher(false);
        setMobileOpen(false);
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setChecking(true);
    setHealthError("");
    fetchHealth(fetch, controller.signal)
      .then(setHealth)
      .catch((e) => {
        if (!controller.signal.aborted) {
          setHealth(null);
          setHealthError(e.message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setChecking(false);
      });
    return () => controller.abort();
  }, [refresh]);
  const parts = hash
    .replace(/^#\/?/, "")
    .split("/")
    .map((p) => {
      try {
        return decodeURIComponent(p);
      } catch {
        return "";
      }
    });
  const tab = parts[0] || "overview";
  const current = menus.find((m) => m.id === tab);
  const go = (route: string) => {
    window.location.hash = route;
    setSwitcher(false);
    setMobileOpen(false);
    setSearch("");
  };
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Bỏ qua điều hướng
      </a>
      {mobileOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="Đóng menu"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        className={`sidebar ${mobileOpen ? "open" : ""}`}
        aria-label="Điều hướng chính"
      >
        <a href="#overview" className="brand" aria-label="Agent CF — Overview">
          <BrandIdentity />
        </a>
        <nav aria-label="Các màn hình">
          {menus.map((m) => (
            <div key={m.id}>
              {m.group && <p className="nav-label">{m.group}</p>}
              <a
                className={`nav-item ${tab === m.id ? "active" : ""}`}
                href={`#${m.id}`}
                aria-current={tab === m.id ? "page" : undefined}
              >
                <span className="nav-icon" aria-hidden="true">
                  <m.Icon size={20} />
                </span>
                {m.label}
              </a>
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <a href="#health" className="connection-link">
            <span className={`status-dot ${health ? "online" : ""}`} />
            {checking
              ? "Đang kết nối…"
              : health
                ? "Server đã kết nối"
                : "Chưa kết nối Server"}
          </a>
          <small>Agent CF · Control Center</small>
        </div>
      </aside>
      <div className="main-shell">
        <header className="app-topbar">
          <div className="row-actions">
            <button
              className="icon-button mobile-menu"
              aria-label="Mở menu"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((v) => !v)}
            >
              <MenuIcon size={18} />
            </button>
            <span className="breadcrumb">
              Agent CF <span>/</span> {current?.label ?? "Kết nối"}
            </span>
          </div>
          <button
            className="quick-search"
            onClick={() => setSwitcher((v) => !v)}
          >
            Tìm màn hình… <kbd>Ctrl K</kbd>
          </button>
        </header>
        <main id="main-content" className="workspace" key={tab}>
          {tab === "overview" && (
            <Overview
              onOpenRun={(id) => go(`runs/${encodeURIComponent(id)}`)}
              onOpenProjects={() => go("projects")}
            />
          )}
          {tab === "projects" && (
            <Projects
              key={parts[1] ?? "list"}
              projectId={parts[1]}
              processId={parts[2] === "processes" ? parts[3] : undefined}
              initialTab={
                parts[2] === "runs"
                  ? "Runs"
                  : parts[2] === "team"
                    ? "Team"
                    : parts[2] === "targets"
                      ? "Targets"
                      : "Processes"
              }
            />
          )}
          {tab === "agents" && <Agents />}
          {tab === "skills" && <Skills />}
          {tab === "pc" && <Runners />}
          {tab === "settings" && <Settings />}
          {tab === "runs" &&
            (parts[1] === "new" ? (
              <RunForm
                onCancel={() => go("runs")}
                onRunCreated={(r) => go(`runs/${encodeURIComponent(r.id)}`)}
              />
            ) : parts[1] ? (
              <RunDetail
                key={parts[1]}
                runId={parts[1]}
                onBack={() => go("runs")}
              />
            ) : (
              <RunList
                onSelectRun={(id) => go(`runs/${encodeURIComponent(id)}`)}
                onCreateNew={() => go("runs/new")}
              />
            ))}
          {tab === "robots" && (
            <RobotScreen key={hash} id={parts[1]} mode={parts[2]} />
          )}
          {tab === "health" && (
            <>
              <PageHead title="Trạng thái hệ thống">
                <button
                  className="btn btn-outline"
                  disabled={checking}
                  onClick={() => setRefresh((v) => v + 1)}
                >
                  Kiểm tra lại
                </button>
              </PageHead>
              <section className="panel">
                {healthError && <Notice error>{healthError}</Notice>}
                <dl className="detail-grid">
                  <div>
                    <dt>Server</dt>
                    <dd>
                      {checking
                        ? "Đang kiểm tra…"
                        : health
                          ? "Đã kết nối"
                          : "Chưa kết nối"}
                    </dd>
                  </div>
                  <div>
                    <dt>Database</dt>
                    <dd>
                      {health
                        ? `Schema ${health.database.schema_version}`
                        : "Chưa xác nhận"}
                    </dd>
                  </div>
                  <div>
                    <dt>Temporal</dt>
                    <dd>
                      {health
                        ? health.temporal.configured
                          ? "Đã cấu hình; chưa xác nhận Service/worker"
                          : "Chưa cấu hình"
                        : "Chưa xác nhận"}
                    </dd>
                  </div>
                </dl>
              </section>
            </>
          )}
          {!current && tab !== "health" && (
            <Notice error>
              Không tìm thấy màn hình. <a href="#overview">Về Overview</a>
            </Notice>
          )}
        </main>
        <footer>
          Agent CF <span>Quản lý Project, Agent điều phối và Process</span>
        </footer>
      </div>
      {switcher && (
        <Modal title="Đi tới màn hình" onClose={() => setSwitcher(false)}>
          <div className="command-panel">
            <input
              autoFocus
              aria-label="Tên màn hình"
              placeholder="Đi tới màn hình…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {menus
              .filter((m) =>
                m.label.toLowerCase().includes(search.toLowerCase()),
              )
              .map((m) => (
                <button
                  className="command-option"
                  key={m.id}
                  onClick={() => go(m.id)}
                >
                  <span aria-hidden="true">
                    <m.Icon size={16} />
                  </span>
                  {m.label}
                </button>
              ))}
          </div>
        </Modal>
      )}
    </div>
  );
}
