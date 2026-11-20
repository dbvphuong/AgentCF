import { useEffect, useState } from "react";
import { acknowledgeRunError, fetchOverviewSummary } from "./api";
import type { OverviewSummaryData } from "./types";
import { useResource } from "../../shared/ui";
import type { RecordData } from "../../shared/api";
import { TechnicalDetails } from "../../shared/TechnicalDetails";

interface OverviewProps {
  onOpenRun: (runId: string) => void;
  onOpenProjects?: () => void;
}

export function Overview({ onOpenRun, onOpenProjects }: OverviewProps) {
  const roles = useResource<RecordData[]>("/v1/settings/roles");
  const models = useResource<RecordData[]>("/v1/settings/models");
  const [data, setData] = useState<OverviewSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const summary = await fetchOverviewSummary();
      setData(summary);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Lỗi khi tải dữ liệu Tổng quan",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAcknowledge = async (runId: string) => {
    setAcknowledgingId(runId);
    try {
      await acknowledgeRunError(runId, "Đã xử lý từ màn hình Overview");
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Không thể đánh dấu đã xử lý");
    } finally {
      setAcknowledgingId(null);
    }
  };

  if (loading && !data) {
    return <div className="loading-state">Đang tải dữ liệu tổng quan…</div>;
  }
  if (!data && error) {
    return (
      <div className="error-alert" role="alert">
        {error}{" "}
        <button className="btn btn-outline" onClick={loadData}>
          Thử lại
        </button>
      </div>
    );
  }

  const totalRunning =
    data?.projects_progress.reduce((acc, p) => acc + (p.running_runs || 0), 0) ?? 0;
  const totalRuns =
    data?.projects_progress.reduce((acc, p) => acc + (p.total_runs || 0), 0) ?? 0;
  const totalSucceeded =
    data?.projects_progress.reduce((acc, p) => acc + (p.succeeded_runs || 0), 0) ?? 0;
  const totalTokens =
    data?.agents_token_usage.reduce((acc, a) => acc + (a.total_tokens || 0), 0) ?? 0;

  return (
    <div className="overview-container">
      {/* 1. Header */}
      <div className="page-heading">
        <div>
          <p className="nav-label" style={{ margin: "0 0 4px", padding: 0 }}>
            TỔNG QUAN HỆ THỐNG
          </p>
          <h1>Bảng điều khiển Trung tâm</h1>
        </div>
        <div className="row-actions">
          <button
            type="button"
            className="btn btn-outline"
            onClick={loadData}
            disabled={loading}
          >
            {loading ? "Đang tải…" : "Làm mới"}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-alert" role="alert">
          {error}
        </div>
      )}

      {/* 2. KPI Summary Cards Grid */}
      <div className="overview-kpi-grid">
        <div
          className="overview-kpi-card"
          style={{ cursor: onOpenProjects ? "pointer" : "default" }}
          onClick={onOpenProjects}
        >
          <div className="kpi-label">Dự án hoạt động</div>
          <div className="kpi-value">{data?.summary_stats.active_projects_count ?? 0}</div>
          <div className="kpi-hint">Tổng số projects trong hệ thống</div>
        </div>

        <div className="overview-kpi-card">
          <div className="kpi-label">Lượt chạy đang chạy</div>
          <div
            className="kpi-value"
            style={{ color: totalRunning > 0 ? "var(--info-text)" : "inherit" }}
          >
            {totalRunning}
          </div>
          <div className="kpi-hint">{totalRuns} tổng lượt chạy đã ghi nhận</div>
        </div>

        <div className="overview-kpi-card">
          <div className="kpi-label">Lượt chạy thành công</div>
          <div className="kpi-value" style={{ color: "var(--success-text)" }}>
            {totalSucceeded}
          </div>
          <div className="kpi-hint">
            {totalRuns > 0 ? Math.round((totalSucceeded / totalRuns) * 100) : 0}% tỉ lệ hoàn thành
          </div>
        </div>

        <div className="overview-kpi-card">
          <div className="kpi-label">Tokens theo Agent điều phối</div>
          <div className="kpi-value">
            {totalTokens.toLocaleString("vi-VN")}
          </div>
          <div className="kpi-hint">
            {data?.summary_stats.active_agents_count ?? 0} Agent điều phối đang hoạt động
          </div>
        </div>
      </div>

      {/* 3. Khối lỗi nổi bật (Unresolved Errors) */}
      <section className="panel" style={{ padding: "20px 22px" }}>
        <div className="section-heading" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
            <span>Cảnh báo lỗi cần xử lý</span>
            {data && data.unresolved_errors.length > 0 && (
              <span className="badge badge-failed">
                {data.unresolved_errors.length} lỗi
              </span>
            )}
          </h2>
        </div>

        {!data || data.unresolved_errors.length === 0 ? (
          <div className="overview-status-ok">
            <span>✓</span>
            <span>Không có cảnh báo lỗi nào đang chờ xử lý. Mọi quy trình hoạt động bình thường.</span>
          </div>
        ) : (
          <div className="error-alerts-list">
            {data.unresolved_errors.map((err) => (
              <div key={err.run_id} className="error-alert-card">
                <div>
                  <div className="error-alert-title-row">
                    <span className="badge badge-failed">FAILED</span>
                    <strong>
                      {err.project_name} / {err.process_name}
                    </strong>
                    <TechnicalDetails values={{ "Run ID": err.run_id }} />
                  </div>
                  {err.topic && (
                    <div className="error-topic-row">
                      Chủ đề: <em>{err.topic}</em>
                    </div>
                  )}
                  <div className="error-message-text">
                    {err.error?.message
                      ? String(err.error.message)
                      : err.error?.code
                        ? String(err.error.code)
                        : "Thất bại trong quá trình thực thi"}
                  </div>
                  <div className="error-time-text">
                    Thời điểm: {new Date(err.occurred_at).toLocaleString("vi-VN")}
                  </div>
                </div>

                <div className="row-actions" style={{ flexShrink: 0 }}>
                  <button
                    type="button"
                    className="btn btn-outline btn-sm"
                    onClick={() => onOpenRun(err.run_id)}
                  >
                    Xem chi tiết
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() => handleAcknowledge(err.run_id)}
                    disabled={acknowledgingId === err.run_id}
                  >
                    {acknowledgingId === err.run_id
                      ? "Đang lưu…"
                      : "Đánh dấu đã xử lý"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 4. Bảng tiến độ Projects */}
      <section className="panel" style={{ padding: "20px 22px" }}>
        <div className="section-heading">
          <h2>Tiến độ Projects & Mục tiêu</h2>
        </div>
        <div className="table-scroll">
          <table className="runs-table">
            <thead>
              <tr>
                <th>Tên Dự án</th>
                <th>Mục tiêu (Target)</th>
                <th>Đang chạy</th>
                <th>Thành công</th>
                <th>Thất bại</th>
                <th>Tổng lượt chạy</th>
              </tr>
            </thead>
            <tbody>
              {!data || data.projects_progress.length === 0 ? (
                <tr>
                  <td colSpan={6} className="empty-state">
                    Chưa có dự án nào trong hệ thống.
                  </td>
                </tr>
              ) : (
                data.projects_progress.map((p) => {
                  const target =
                    p.targets && p.targets.length > 0 ? p.targets[0] : null;
                  return (
                    <tr key={p.project_id}>
                      <td className="bold-cell">
                        <a
                          className="entity-link"
                          href={`#projects/${encodeURIComponent(p.project_id)}`}
                        >
                          {p.name}
                        </a>
                      </td>
                      <td>
                        {target ? (
                          <span>
                            <strong>
                              {target.completed_count}/{target.target_count}
                            </strong>{" "}
                            <span className="text-muted" style={{ fontSize: "12px" }}>
                              ({target.name} · {target.status})
                            </span>
                          </span>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                      <td>
                        {p.running_runs > 0 ? (
                          <a
                            className="badge badge-running"
                            href={`#projects/${encodeURIComponent(p.project_id)}/runs`}
                          >
                            {p.running_runs} running
                          </a>
                        ) : (
                          <span className="text-muted">0</span>
                        )}
                      </td>
                      <td>
                        <span className="text-success">
                          {p.succeeded_runs}
                        </span>
                      </td>
                      <td>
                        {p.failed_runs > 0 ? (
                          <span className="text-danger">
                            {p.failed_runs}
                          </span>
                        ) : (
                          <span className="text-muted">0</span>
                        )}
                      </td>
                      <td>{p.total_runs}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* 5. Bảng xếp hạng Token Agents */}
      <section className="panel" style={{ padding: "20px 22px" }}>
        <div className="section-heading">
          <h2>Thống kê Token theo Agent điều phối</h2>
        </div>
        <div className="table-scroll">
          <table className="runs-table">
            <thead>
              <tr>
                <th style={{ width: "70px", textAlign: "center" }}>Hạng</th>
                <th>Agent điều phối</th>
                <th>Role</th>
                <th>Model</th>
                <th>Tổng Token sử dụng</th>
              </tr>
            </thead>
            <tbody>
              {!data || data.agents_token_usage.length === 0 ? (
                <tr>
                  <td colSpan={5} className="empty-state">
                    Chưa có Agent điều phối nào được cấu hình trong danh mục.
                  </td>
                </tr>
              ) : (
                data.agents_token_usage.map((ag, idx) => (
                  <tr key={ag.agent_id}>
                    <td style={{ textAlign: "center" }}>
                      <span
                        className={`rank-badge ${
                          idx === 0
                            ? "rank-1"
                            : idx === 1
                              ? "rank-2"
                              : idx === 2
                                ? "rank-3"
                                : ""
                        }`}
                      >
                        #{idx + 1}
                      </span>
                    </td>
                    <td className="bold-cell">
                      <span>{ag.name}</span>
                      <TechnicalDetails values={{ "Agent ID": ag.agent_id, "Role ID": ag.role_id, "Model ID": ag.model_id }} />
                    </td>
                    <td>{roles.data?.find(r => r.id === ag.role_id)?.name || "—"}</td>
                    <td>{models.data?.find(m => m.id === ag.model_id)?.name || "—"}</td>
                    <td>
                      {ag.has_usage &&
                      ag.total_tokens !== null &&
                      ag.total_tokens !== undefined ? (
                        <span style={{ fontWeight: 650, color: "var(--ink)" }}>
                          {ag.total_tokens.toLocaleString("vi-VN")} tokens
                        </span>
                      ) : (
                        <span className="text-muted" style={{ fontStyle: "italic" }}>
                          — (Chưa có dữ liệu)
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
