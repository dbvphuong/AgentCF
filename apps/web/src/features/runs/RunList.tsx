import { useEffect, useState } from "react";
import type { Run } from "./types";
import { dateTime, request } from "../../shared/api";
import type { RecordData } from "../../shared/api";
import { Notice, useResource } from "../../shared/ui";

interface RunListProps {
  onSelectRun: (runId: string) => void;
  onCreateNew: () => void;
  selectedRunId?: string | null;
  projectId?: string;
}
interface RunPage {
  items: Run[];
  next_cursor: string | null;
  total: number;
  total_all: number;
}
const initialFrom = () =>
  new Date(Date.now() + 7 * 3600000 - 6 * 86400000).toISOString().slice(0, 10);
export function RunList({
  onSelectRun,
  onCreateNew,
  selectedRunId,
  projectId,
}: RunListProps) {
  const projects = useResource<RecordData[]>("/v1/projects");
  const [project, setProject] = useState(projectId ?? "");
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [from, setFrom] = useState(initialFrom);
  const [to, setTo] = useState("");
  const [limit, setLimit] = useState(25);
  const [cursors, setCursors] = useState<string[]>([]);
  const [revision, setRevision] = useState(0);
  const [data, setData] = useState<RunPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const handleResetFilters = () => {
    setSearch("");
    setQuery("");
    setProject(projectId ?? "");
    setFilter("all");
    setFrom(initialFrom());
    setTo("");
    setCursors([]);
    setRevision((n) => n + 1);
  };

  useEffect(() => {
    const id = setTimeout(() => {
      setQuery(search);
      setCursors([]);
    }, 250);
    return () => clearTimeout(id);
  }, [search]);

  useEffect(() => {
    const c = new AbortController();
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ limit: String(limit) });
    if (project) params.set("project_id", project);
    if (filter !== "all")
      params.set(
        "status",
        filter === "active" ? "queued,running,reconciling,cancelling" : filter,
      );
    if (query.trim()) params.set("search", query.trim());
    if (cursors.length) params.set("cursor", cursors.at(-1)!);
    if (from)
      params.set(
        "started_from",
        new Date(from + "T00:00:00+07:00").toISOString(),
      );
    if (to)
      params.set(
        "started_to",
        new Date(
          new Date(to + "T00:00:00+07:00").getTime() + 86400000,
        ).toISOString(),
      );
    request<RunPage>(`/v1/runs?${params}`, "GET", undefined, c.signal)
      .then(setData)
      .catch((e) => {
        if (!c.signal.aborted) {
          setData(null);
          setError(e.message);
        }
      })
      .finally(() => {
        if (!c.signal.aborted) setLoading(false);
      });
    return () => c.abort();
  }, [project, filter, query, from, to, limit, cursors, revision]);
  const badge = (status: string) =>
    `badge badge-${status === "succeeded" ? "success" : ["queued", "running"].includes(status) ? "running" : ["reconciling", "cancelling"].includes(status) ? "warning" : status}`;
  return (
    <section className="run-list-container">
      <div className="run-list-header">
        <div className="run-list-title-group">
          {!projectId && <h2>Runs</h2>}
          {data && (
            <span className="run-count-badge">
              {data.total_all} lượt chạy
            </span>
          )}
        </div>
        <div className="row-actions">
          <button className="btn btn-primary" onClick={onCreateNew}>
            + Run
          </button>
        </div>
      </div>
      <div className="run-filters-compact">
        <div className="run-search-input">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            aria-label="Tra cứu lần chạy theo ID"
            placeholder="Tìm theo ID khi cần…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="filter-select"
          aria-label="Project"
          disabled={!!projectId}
          value={project}
          onChange={(e) => {
            setProject(e.target.value);
            setCursors([]);
          }}
        >
          <option value="">Tất cả Projects</option>
          {projects.data?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <select
          className="filter-select"
          aria-label="Status"
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value);
            setCursors([]);
          }}
        >
          <option value="all">Trạng thái: Tất cả</option>
          <option value="active">Running</option>
          <option value="succeeded">Succeeded</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <div className="date-filter-group">
          <span className="date-filter-label">Từ</span>
          <input
            type="date"
            aria-label="Started từ"
            value={from}
            onChange={(e) => {
              setFrom(e.target.value);
              setCursors([]);
            }}
          />
          <span className="date-filter-label">Đến</span>
          <input
            type="date"
            aria-label="Đến"
            value={to}
            min={from}
            onChange={(e) => {
              setTo(e.target.value);
              setCursors([]);
            }}
          />
        </div>
        <button
          type="button"
          className="run-filter-reset"
          title="Đặt lại bộ lọc và làm mới"
          aria-label="Đặt lại bộ lọc và làm mới"
          disabled={loading}
          onClick={handleResetFilters}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1" />
          </svg>
        </button>
      </div>
      {(error || projects.error) && (
        <Notice error>{error || projects.error}</Notice>
      )}
      {loading && <Notice>Đang tải Runs…</Notice>}
      <div className="table-scroll">
        <table className="runs-table">
          <thead>
            <tr>
              <th>STT</th>
              <th>Run / Process</th>
              <th>Status</th>
              <th>Tiến độ</th>
              <th>Started</th>
              <th>Ended</th>
              <th>Duration</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((run, i) => {
              const completed = run.task_runs.filter(
                (t) => t.status === "succeeded",
              ).length;
              const started = run.started_at ?? run.created_at;
              const duration = Math.max(
                0,
                Math.floor(
                  ((run.ended_at ? Date.parse(run.ended_at) : Date.now()) -
                    Date.parse(started)) /
                    1000,
                ),
              );
              return (
                <tr
                  key={run.id}
                  className={selectedRunId === run.id ? "selected" : ""}
                >
                  <td>{cursors.length * limit + i + 1}</td>
                  <td>
                    <button
                      className="link-button"
                      onClick={() => onSelectRun(run.id)}
                    >
                      {run.process_name || "Lần chạy"}
                    </button>
                    <small className="cell-note">
                      {typeof run.input?.topic === "string" ? run.input.topic : dateTime(run.created_at)}
                    </small>
                  </td>
                  <td>
                    <span className={badge(run.status)}>{run.status}</span>
                  </td>
                  <td>
                    {completed} / {run.task_runs.length}
                    <progress
                      max={run.task_runs.length || 1}
                      value={completed}
                    />
                  </td>
                  <td>{dateTime(started)}</td>
                  <td>{dateTime(run.ended_at)}</td>
                  <td>
                    {Number.isFinite(duration)
                      ? `${Math.floor(duration / 60)}m ${duration % 60}s`
                      : "—"}
                  </td>
                  <td>
                    <button
                      className="btn btn-outline btn-sm"
                      onClick={() => onSelectRun(run.id)}
                    >
                      Chi tiết
                    </button>
                  </td>
                </tr>
              );
            })}
            {!loading && !data?.items.length && (
              <tr>
                <td colSpan={8} className="empty-state">
                  Chưa có Run phù hợp với bộ lọc.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <span>
          Total {data?.total ?? "—"} / {data?.total_all ?? "—"} Runs
        </span>
        <div className="row-actions">
          <label>
            Số dòng{" "}
            <select
              value={limit}
              onChange={(e) => {
                setLimit(Number(e.target.value));
                setCursors([]);
              }}
            >
              {[25, 50, 100].map((n) => (
                <option key={n}>{n}</option>
              ))}
            </select>
          </label>
          <button
            className="btn btn-outline btn-sm"
            disabled={!cursors.length || loading}
            onClick={() => setCursors((c) => c.slice(0, -1))}
          >
            Previous
          </button>
          <span>{cursors.length + 1}</span>
          <button
            className="btn btn-outline btn-sm"
            disabled={!data?.next_cursor || loading}
            onClick={() => setCursors((c) => [...c, data!.next_cursor!])}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
