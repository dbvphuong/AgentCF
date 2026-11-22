import { useEffect, useState } from "react";
import { cancelRun, continueRun, downloadArtifactUrl, fetchArtifactText, fetchRun, fetchRunEvents } from "./api";
import type { ArtifactRef, Run, RunEvent, RunStatus } from "./types";
import { request, resource } from "../../shared/api";
import type { RecordData } from "../../shared/api";
import { useResource } from "../../shared/ui";
import { TechnicalDetails } from "../../shared/TechnicalDetails";
import { RunLogViewer } from "./RunLogViewer";

interface RunDetailProps {
  runId: string;
  onBack: () => void;
}

export function RunDetail({ runId, onBack }: RunDetailProps) {
  const [run, setRun] = useState<Run | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "tasks" | "artifacts" | "events">("overview");
  const [loading, setLoading] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [continuing, setContinuing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactRef | null>(null);
  const [artifactContent, setArtifactContent] = useState<string | null>(null);
  const [loadingArtifact, setLoadingArtifact] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const runners = useResource<RecordData[]>("/v1/runners");
  const skills = useResource<RecordData[]>("/v1/skills");
  const [process, setProcess] = useState<RecordData | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setProcess(null);
    if (run?.process_id) request(resource("/v1/processes", run.process_id), "GET", undefined, controller.signal)
      .then(setProcess).catch(() => { /* Identifiers remain available in technical details. */ });
    return () => controller.abort();
  }, [run?.process_id]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [runData, eventData] = await Promise.all([
        fetchRun(runId),
        fetchRunEvents(runId),
      ]);
      setRun(runData);
      setEvents(eventData);

      // If artifacts exist and none selected, select first
      if (runData.artifacts && runData.artifacts.length > 0 && !selectedArtifact) {
        handleSelectArtifact(runData.artifacts[0]);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Lỗi khi tải thông tin chi tiết Run.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [runId]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      if (run && (run.status === "queued" || run.status === "running" || run.status === "reconciling")) {
        loadData();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh, run?.status]);

  const handleCancel = async () => {
    if (!confirm("Bạn có chắc chắn muốn hủy lượt chạy này?")) return;
    setCancelling(true);
    try {
      const updated = await cancelRun(runId);
      setRun(updated);
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Hủy Run thất bại.");
    } finally {
      setCancelling(false);
    }
  };

  const handleContinue = async () => {
    setContinuing(true);
    try {
      const updated = await continueRun(runId, { decision: "proceed" });
      setRun(updated);
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Tiếp tục Run thất bại.");
    } finally {
      setContinuing(false);
    }
  };

  const handleSelectArtifact = async (art: ArtifactRef) => {
    setSelectedArtifact(art);
    setLoadingArtifact(true);
    try {
      const text = await fetchArtifactText(art.id);
      setArtifactContent(text);
    } catch (err: unknown) {
      setArtifactContent("Không thể tải nội dung artifact: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoadingArtifact(false);
    }
  };

  const getStatusBadgeClass = (status: RunStatus) => {
    switch (status) {
      case "succeeded":
        return "badge badge-success";
      case "running":
      case "queued":
        return "badge badge-running";
      case "reconciling":
      case "cancelling":
        return "badge badge-warning";
      case "failed":
        return "badge badge-failed";
      case "cancelled":
        return "badge badge-cancelled";
      default:
        return "badge";
    }
  };

  if (!run && loading) {
    return <div className="loading-state">Đang tải thông tin lượt chạy…</div>;
  }

  if (!run) {
    return (
      <div className="error-state">
        <p>{error || "Không tìm thấy thông tin lượt chạy."}</p>
        <button type="button" className="btn btn-secondary" onClick={onBack}>
          Quay lại danh sách
        </button>
      </div>
    );
  }

  const topic = (run.input?.topic as string) || (run.input?.prompt as string) || JSON.stringify(run.input);
  const isTerminal = ["succeeded", "failed", "cancelled"].includes(run.status);
  const version = process?.versions?.find((v: RecordData) => v.id === run.process_version_id);
  const nodeName = (id: string, index: number) => version?.definition?.tasks?.find((t: RecordData) => t.id === id)?.name || `Bước ${index + 1}`;

  return (
    <div className="run-detail-container">
      <div className="run-detail-topbar">
        <button type="button" className="btn btn-secondary btn-sm" onClick={onBack}>
          &larr; Danh sách Run
        </button>
        <div className="run-title-group">
          <h2>Lần chạy · {process?.name || run.process_name || "Process"}</h2>
          <span className={getStatusBadgeClass(run.status)}>{run.status.toUpperCase()}</span>
        </div>
        <div className="topbar-actions">
          <label className="auto-refresh-toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Tự động làm mới
          </label>
          <button type="button" className="btn btn-secondary btn-sm" onClick={loadData} disabled={loading}>
            {loading ? "Đang tải…" : "Làm mới"}
          </button>
          {run.attention_reason && !isTerminal && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleContinue}
              disabled={continuing}
            >
              {continuing ? "Đang xử lý…" : "Tiếp tục (Continue)"}
            </button>
          )}
          {!isTerminal && (
            <button
              type="button"
              className="btn btn-danger btn-sm"
              onClick={handleCancel}
              disabled={cancelling}
            >
              {cancelling ? "Đang hủy…" : "Hủy lượt chạy"}
            </button>
          )}
        </div>
      </div>

      {run.attention_reason && (
        <div className="attention-banner">
          <div>
            <strong>Đang chờ người dùng:</strong> {run.attention_reason}
          </div>
          {!isTerminal && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleContinue}
              disabled={continuing}
            >
              {continuing ? "Đang xử lý…" : "Tiếp tục ngay"}
            </button>
          )}
        </div>
      )}

      {error && <div className="error-alert" role="alert">{error}</div>}

      {run.task_runs.filter(t => Array.isArray(t.output?.local_files)).map(task => (
        <section className="panel" key={task.id}>
          <h3>Kết quả trên PC</h3>
          <p>PC: {runners.data?.find(r => r.id === task.output?.runner_id)?.name || "Không có tên PC"}</p>
            <p>Thư mục làm việc: <code>{String(task.output?.working_directory ?? "")}</code></p>
            {!!task.output?.topic_directory && <p>Chủ đề: <code>{String(task.output?.topic_directory)}</code></p>}
          <p>Skill: <code>{String(task.output?.skill_source_path ?? "")}</code></p>
          <p>File gốc nằm trên PC thực thi. Sao chép đường dẫn để mở bằng ứng dụng trên PC.</p>
          <ul>{(task.output!.local_files as Array<{path: string; size_bytes: number}>).map(file => (
            <li key={file.path}><code>{file.path}</code> ({file.size_bytes.toLocaleString("vi-VN")} byte){" "}
              <button type="button" className="btn btn-outline btn-sm" onClick={() => {
                navigator.clipboard.writeText(file.path).catch(() => setError("Không sao chép được; hãy chọn và sao chép đường dẫn."));
              }}>Sao chép đường dẫn</button>
            </li>
          ))}</ul>
        </section>
      ))}
      <div className="detail-tabs">
        <button
          type="button"
          className={`tab-btn ${activeTab === "overview" ? "active" : ""}`}
          onClick={() => setActiveTab("overview")}
        >
          Tổng quan & Kết quả
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === "tasks" ? "active" : ""}`}
          onClick={() => setActiveTab("tasks")}
        >
          Tasks ({run.task_runs.length})
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === "artifacts" ? "active" : ""}`}
          onClick={() => setActiveTab("artifacts")}
        >
          Bản sao trên Web ({run.artifacts?.length || 0})
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === "events" ? "active" : ""}`}
          onClick={() => setActiveTab("events")}
        >
          Nhật ký thực thi ({events.length})
        </button>
      </div>

      <div className="tab-content">
        {activeTab === "overview" && (
          <div className="overview-panel">
            <div className="detail-card">
              <h4>Thông tin chung</h4>
              <dl className="property-list">
                <div><dt>Chủ đề (Topic)</dt><dd className="topic-text">{topic}</dd></div>
                <div><dt>Thời điểm tạo</dt><dd>{new Date(run.created_at).toLocaleString("vi-VN")}</dd></div>
                <div><dt>Bắt đầu lúc</dt><dd>{run.started_at ? new Date(run.started_at).toLocaleString("vi-VN") : "Chưa chạy"}</dd></div>
                <div><dt>Kết thúc lúc</dt><dd>{run.ended_at ? new Date(run.ended_at).toLocaleString("vi-VN") : "Chưa kết thúc"}</dd></div>
              </dl>
              <TechnicalDetails values={{ "Run ID": run.id, "Project ID": run.project_id, "Process ID": run.process_id, "Snapshot ID": run.process_version_id, "Snapshot SHA-256": run.snapshot_sha256 }} />
            </div>

            {run.error && (
              <div className="detail-card card-error">
                <h4>Chi tiết lỗi</h4>
                <p className="error-text">{typeof run.error.message === "string" ? run.error.message : "Lần chạy gặp lỗi; mở chi tiết kỹ thuật để xem đầy đủ."}</p>
                {run.task_runs.some((t) => t.error) && (
                  <ul style={{ margin: "8px 0", paddingLeft: "18px" }}>
                    {run.task_runs.map((t, index) =>
                      t.error ? (
                        <li key={t.id}>
                          <strong>{nodeName(t.task_id, index)}</strong>:{" "}
                          {t.error.code ? <code>[{String(t.error.code)}] </code> : null}
                          {String(t.error.message ?? "Thực thi thất bại")}
                        </li>
                      ) : null,
                    )}
                  </ul>
                )}
                <TechnicalDetails values={{ "Error JSON": run.error }} />
              </div>
            )}

            {run.output && (
              <div className="detail-card">
                <h4>Dữ liệu kết quả đầu ra (Output)</h4>
                <TechnicalDetails values={{ "Output JSON": run.output }} />
              </div>
            )}
          </div>
        )}

        {activeTab === "tasks" && (
          <div className="tasks-panel">
            <table className="tasks-table">
              <thead>
                <tr>
                  <th>Bước thực hiện</th>
                  <th>Trạng thái</th>
                  <th>Lần thử (Gen)</th>
                  <th>Output / Lỗi</th>
                </tr>
              </thead>
              <tbody>
                {run.task_runs.map((t, index) => (
                  <tr key={t.id}>
                    <td>{nodeName(t.task_id, index)}
                      <TechnicalDetails values={{ "Task ID": t.task_id, "TaskRun ID": t.id, "Task key": t.task_key }} />
                    </td>
                    <td>
                      <span className={getStatusBadgeClass(t.status as RunStatus)}>{t.status}</span>
                      {t.waiting_for && (
                        <div style={{ fontSize: "11px", color: "#856404", marginTop: "2px" }}>
                          (Chờ: {t.waiting_for})
                        </div>
                      )}
                    </td>
                    <td>{t.generation}</td>
                    <td>
                      {t.output && <span className="text-success">Có kết quả</span>}
                      {t.error && <span className="text-danger">{(t.error.message as string) || "Lỗi"}</span>}
                      {!t.output && !t.error && <span className="text-muted">-</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === "artifacts" && (
          <div className="artifacts-panel">
            <div className="artifacts-sidebar">
              <h4>Danh sách file Artifact</h4>
              {(!run.artifacts || run.artifacts.length === 0) ? (
                <p className="text-muted">Không có bản sao trên Web. Kết quả local được liệt kê trong phần Kết quả trên PC.</p>
              ) : (
                <ul className="artifact-list">
                  {run.artifacts.map((art) => (
                    <li
                      key={art.id}
                      className={`artifact-item ${selectedArtifact?.id === art.id ? "active" : ""}`}
                      onClick={() => handleSelectArtifact(art)}
                    >
                      <div className="art-name">{art.logical_name}</div>
                      <div className="art-meta">{Math.round(art.size_bytes / 1024)} KB · {art.availability}</div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="artifact-viewer">
              {selectedArtifact ? (
                <div>
                  <div className="viewer-header">
                    <h4>{selectedArtifact.logical_name}</h4>
                    <a
                      href={downloadArtifactUrl(selectedArtifact.id)}
                      download={selectedArtifact.logical_name}
                      className="btn btn-outline btn-sm"
                      target="_blank"
                      rel="noreferrer"
                    >
                      Tải về file
                    </a>
                  </div>
                  {loadingArtifact ? (
                    <p>Đang tải nội dung…</p>
                  ) : (
                    <pre className="artifact-content-pre">{artifactContent}</pre>
                  )}
                </div>
              ) : (
                <p className="text-muted">Chọn một file artifact ở bên trái để xem nội dung.</p>
              )}
            </div>
          </div>
        )}

        {activeTab === "events" && (
          <div className="events-panel">
            <RunLogViewer
              run={run}
              events={events}
              process={process}
              runners={runners.data || []}
              skills={skills.data || []}
            />
          </div>
        )}
      </div>
    </div>
  );
}
