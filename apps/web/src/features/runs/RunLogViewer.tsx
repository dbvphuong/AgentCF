import { useMemo, useState } from "react";
import type { RecordData } from "../../shared/api";
import type { Run, RunEvent } from "./types";

interface RunLogViewerProps {
  run: Run;
  events: RunEvent[];
  process: RecordData | null;
  runners: RecordData[];
  skills: RecordData[];
}

export type LogLevel = "ALL" | "INFO" | "SUCCESS" | "WARN" | "ERROR";

export interface LogItem {
  id: string;
  seq: number;
  timeStr: string;
  dateStr: string;
  level: "INFO" | "SUCCESS" | "WARN" | "ERROR";
  nodeName: string;
  skillName: string;
  message: string;
  details?: {
    files?: Array<{ path: string; size_bytes?: number }>;
    workingDir?: string;
    summary?: string;
    errorText?: string;
    runnerName?: string;
    rawData?: Record<string, unknown>;
  };
}

export function RunLogViewer({ run, events, process, runners, skills }: RunLogViewerProps) {
  const [levelFilter, setLevelFilter] = useState<LogLevel>("ALL");
  const [nodeFilter, setNodeFilter] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState<boolean>(false);

  const version = process?.versions?.find((v: RecordData) => v.id === run.process_version_id);
  const tasksDef = (version?.definition?.tasks as RecordData[]) || [];

  const resolveNodeName = (taskId?: string | null, taskRunId?: string | null): string => {
    if (!taskId && taskRunId) {
      const tr = run.task_runs.find((t) => t.id === taskRunId);
      if (tr) taskId = tr.task_id;
    }
    if (taskId) {
      const def = tasksDef.find((t) => t.id === taskId);
      if (def?.name) return String(def.name);
      const idx = run.task_runs.findIndex((t) => t.task_id === taskId);
      if (idx >= 0) return `Bước ${idx + 1}`;
    }
    return "Toàn bộ Process";
  };

  const resolveSkillName = (taskId?: string | null, taskRunId?: string | null): string => {
    let tr = taskRunId ? run.task_runs.find((t) => t.id === taskRunId) : undefined;
    if (!tr && taskId) {
      tr = run.task_runs.find((t) => t.task_id === taskId);
    }
    if (tr?.output?.skill_source_path) {
      const parts = String(tr.output.skill_source_path).split(/[\\/]/);
      return parts[parts.length - 1] || "Skill";
    }
    if (taskId) {
      const def = tasksDef.find((t) => t.id === taskId);
      if (def?.skill_id) {
        const skl = skills.find((s) => s.id === def.skill_id);
        if (skl?.name) return String(skl.name);
      }
    }
    return "—";
  };

  const resolveRunnerName = (runnerId?: string | null): string => {
    if (!runnerId) return "PC Runner";
    const found = runners.find((r) => r.id === runnerId);
    return found?.name ? String(found.name) : runnerId;
  };

  const logItems: LogItem[] = useMemo(() => {
    const topic = (run.input?.topic as string) || (run.input?.prompt as string) || "";
    const items: LogItem[] = [];

    // Sort events by sequence
    const sorted = [...events].sort((a, b) => a.sequence - b.sequence);

    for (const ev of sorted) {
      const tr = ev.task_run_id ? run.task_runs.find((t) => t.id === ev.task_run_id) : undefined;
      const taskId = tr?.task_id;
      const nodeName = resolveNodeName(taskId, ev.task_run_id);
      const skillName = resolveSkillName(taskId, ev.task_run_id);
      const date = new Date(ev.recorded_at);
      const timeStr = date.toLocaleTimeString("vi-VN");
      const dateStr = date.toLocaleDateString("vi-VN");

      let level: "INFO" | "SUCCESS" | "WARN" | "ERROR" = "INFO";
      let message = "";
      const details: LogItem["details"] = {
        rawData: ev.data,
      };

      const eventRunnerId = (ev.data?.runner_id as string) || (tr?.output?.runner_id as string);
      if (eventRunnerId) {
        details.runnerName = resolveRunnerName(eventRunnerId);
      }

      switch (ev.event_type) {
        case "run_created": {
          level = "INFO";
          const procName = process?.name || run.process_name || "Process";
          message = `Khởi tạo lượt chạy Process "${procName}"${topic ? ` · Chủ đề: "${topic}"` : ""}`;
          break;
        }

        case "task_claimed": {
          level = "INFO";
          const gen = ev.data?.generation ?? tr?.generation ?? 1;
          const rName = details.runnerName || "PC Runner";
          message = `PC "${rName}" đã nhận nhiệm vụ thực thi (Lần thử ${gen})`;
          break;
        }

        case "task_waiting_for_input": {
          level = "WARN";
          const reason = (ev.data?.reason as string) || "Đang chờ người dùng kiểm duyệt hoặc xác nhận";
          message = `Tạm dừng bước thực thi — ${reason}`;
          break;
        }

        case "run_continued": {
          level = "INFO";
          const decision = (ev.data?.decision as string) || "tiếp tục";
          const feedback = ev.data?.feedback as string | undefined;
          message = `Xác nhận tiếp tục lượt chạy (Quyết định: ${decision}${feedback ? ` · Phản hồi: ${feedback}` : ""})`;
          break;
        }

        case "task_completed": {
          const outcome = ev.data?.outcome as string | undefined;
          const exitCode = typeof ev.data?.exit_code === "number" ? ev.data.exit_code : 0;
          const isSuccess = outcome === "succeeded";

          if (isSuccess) {
            level = "SUCCESS";
            const localFiles = (tr?.output?.local_files as Array<{ path: string; size_bytes?: number }>) || [];
            details.files = localFiles;
            details.workingDir = tr?.output?.working_directory as string | undefined;
            if (tr?.output?.summary && typeof tr.output.summary === "string") {
              details.summary = tr.output.summary;
            }

            if (localFiles.length > 0) {
              message = `Hoàn thành thực thi (Exit code: 0) — Đã tạo/cập nhật ${localFiles.length} file tại PC`;
            } else if (details.summary) {
              const preview = details.summary.trim().split("\n")[0]?.slice(0, 100) || "Thành công";
              message = `Hoàn thành thực thi (Exit code: 0) — ${preview}`;
            } else {
              message = "Hoàn thành thực thi bước này thành công (Exit code: 0)";
            }
          } else {
            level = "ERROR";
            const errCode = (tr?.error?.code as string) || (ev.data?.error_code as string) || "E_FAILED";
            const errMsg = (tr?.error?.message as string) || (ev.data?.message as string) || "Thực thi thất bại";
            details.errorText = `[${errCode}] ${errMsg}`;
            message = `Thực thi thất bại (Exit code: ${exitCode}): ${errMsg}`;
          }
          break;
        }

        case "run_succeeded": {
          level = "SUCCESS";
          message = "Lượt chạy hoàn thành thành công tất cả các bước!";
          break;
        }

        case "run_failed": {
          level = "ERROR";
          const errMsg = (run.error?.message as string) || (ev.data?.message as string) || "Quy trình dừng do lỗi";
          details.errorText = errMsg;
          message = `Lượt chạy thất bại: ${errMsg}`;
          break;
        }

        case "run_cancelled": {
          level = "WARN";
          const reason = (ev.data?.reason as string) || "Người dùng hủy lượt chạy";
          message = `Lượt chạy đã bị hủy: ${reason}`;
          break;
        }

        case "attempt_observation": {
          level = "INFO";
          const obsType = (ev.data?.observation_type as string) || "Tiến trình";
          message = `Ghi nhận quan sát: ${obsType}`;
          break;
        }

        case "state_changed": {
          level = "INFO";
          const st = (ev.data?.status as string) || "đối soát";
          const re = ev.data?.reason ? ` (${ev.data.reason})` : "";
          message = `Trạng thái hệ thống chuyển sang "${st}"${re}`;
          break;
        }

        default: {
          level = "INFO";
          message = `Sự kiện hệ thống: ${ev.event_type}`;
          break;
        }
      }

      items.push({
        id: ev.id,
        seq: ev.sequence,
        timeStr,
        dateStr,
        level,
        nodeName,
        skillName,
        message,
        details,
      });
    }

    return items;
  }, [events, run, process, runners, skills]);

  const uniqueNodes = useMemo(() => {
    const set = new Set<string>();
    for (const item of logItems) {
      if (item.nodeName && item.nodeName !== "—") set.add(item.nodeName);
    }
    return Array.from(set);
  }, [logItems]);

  const counts = useMemo(() => {
    const c = { ALL: logItems.length, INFO: 0, SUCCESS: 0, WARN: 0, ERROR: 0 };
    for (const item of logItems) {
      if (item.level === "INFO") c.INFO++;
      else if (item.level === "SUCCESS") c.SUCCESS++;
      else if (item.level === "WARN") c.WARN++;
      else if (item.level === "ERROR") c.ERROR++;
    }
    return c;
  }, [logItems]);

  const filteredLogs = useMemo(() => {
    return logItems.filter((item) => {
      if (levelFilter !== "ALL" && item.level !== levelFilter) return false;
      if (nodeFilter !== "ALL" && item.nodeName !== nodeFilter) return false;
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const text = `${item.timeStr} ${item.level} ${item.nodeName} ${item.skillName} ${item.message} ${item.details?.summary || ""} ${item.details?.errorText || ""}`.toLowerCase();
        if (!text.includes(q)) return false;
      }
      return true;
    });
  }, [logItems, levelFilter, nodeFilter, searchTerm]);

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleCopyLogs = () => {
    const lines = filteredLogs.map((l) =>
      `[${l.timeStr}] [${l.level.padEnd(7)}] [Node: ${l.nodeName}] [Skill: ${l.skillName}] ${l.message}`
    );
    navigator.clipboard.writeText(lines.join("\n")).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => { /* ignore */ });
  };

  return (
    <div className="run-log-viewer">
      {/* Control Toolbar */}
      <div className="log-viewer-toolbar">
        <div className="log-filter-pills">
          <button
            type="button"
            className={`log-pill ${levelFilter === "ALL" ? "active" : ""}`}
            onClick={() => setLevelFilter("ALL")}
          >
            Tất cả <span className="pill-badge">{counts.ALL}</span>
          </button>
          <button
            type="button"
            className={`log-pill pill-error ${levelFilter === "ERROR" ? "active" : ""}`}
            onClick={() => setLevelFilter("ERROR")}
          >
            Lỗi <span className="pill-badge">{counts.ERROR}</span>
          </button>
          <button
            type="button"
            className={`log-pill pill-warn ${levelFilter === "WARN" ? "active" : ""}`}
            onClick={() => setLevelFilter("WARN")}
          >
            Cảnh báo <span className="pill-badge">{counts.WARN}</span>
          </button>
          <button
            type="button"
            className={`log-pill pill-success ${levelFilter === "SUCCESS" ? "active" : ""}`}
            onClick={() => setLevelFilter("SUCCESS")}
          >
            Thành công <span className="pill-badge">{counts.SUCCESS}</span>
          </button>
          <button
            type="button"
            className={`log-pill pill-info ${levelFilter === "INFO" ? "active" : ""}`}
            onClick={() => setLevelFilter("INFO")}
          >
            Thông tin <span className="pill-badge">{counts.INFO}</span>
          </button>
        </div>

        <div className="log-toolbar-right">
          {uniqueNodes.length > 1 && (
            <select
              className="log-node-select"
              value={nodeFilter}
              onChange={(e) => setNodeFilter(e.target.value)}
              title="Lọc theo Node"
            >
              <option value="ALL">Tất cả Node</option>
              {uniqueNodes.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          )}

          <div className="log-search-box">
            <input
              type="text"
              placeholder="Tìm kiếm trong log…"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            {searchTerm && (
              <button
                type="button"
                className="log-search-clear"
                onClick={() => setSearchTerm("")}
                title="Xóa tìm kiếm"
              >
                ✕
              </button>
            )}
          </div>

          <button
            type="button"
            className="btn btn-outline btn-sm log-copy-btn"
            onClick={handleCopyLogs}
            title="Sao chép toàn bộ dòng log đang hiển thị"
          >
            {copied ? "✓ Đã sao chép!" : "Sao chép log"}
          </button>
        </div>
      </div>

      {/* Terminal Console Stream */}
      <div className="log-terminal-container">
        {filteredLogs.length === 0 ? (
          <div className="log-empty-state">
            Không có dòng nhật ký nào phù hợp với bộ lọc hiện tại.
          </div>
        ) : (
          <div className="log-stream">
            {filteredLogs.map((log) => {
              const isExpanded = expandedIds.has(log.id);
              const hasDetails = Boolean(
                log.details?.files?.length ||
                log.details?.summary ||
                log.details?.errorText ||
                (log.details?.rawData && Object.keys(log.details.rawData).length > 0)
              );

              return (
                <div
                  key={log.id}
                  className={`log-row log-row-${log.level.toLowerCase()} ${isExpanded ? "expanded" : ""}`}
                >
                  <div className="log-row-main" onClick={() => hasDetails && toggleExpand(log.id)}>
                    <span className="log-col-time" title={log.dateStr}>
                      {log.timeStr}
                    </span>

                    <span className={`log-badge log-badge-${log.level.toLowerCase()}`}>
                      {log.level}
                    </span>

                    <span className="log-col-node" title={`Node: ${log.nodeName}`}>
                      {log.nodeName}
                    </span>

                    <span className="log-col-skill" title={`Skill: ${log.skillName}`}>
                      {log.skillName}
                    </span>

                    <span className="log-col-message">
                      {log.message}
                    </span>

                    {hasDetails && (
                      <button
                        type="button"
                        className="log-expand-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleExpand(log.id);
                        }}
                        title={isExpanded ? "Thu gọn chi tiết" : "Xem chi tiết"}
                      >
                        {isExpanded ? "Thu gọn ▲" : "Chi tiết ▼"}
                      </button>
                    )}
                  </div>

                  {/* Expanded detail box */}
                  {isExpanded && hasDetails && (
                    <div className="log-row-details">
                      {log.details?.files && log.details.files.length > 0 && (
                        <div className="detail-section">
                          <div className="detail-heading">File kết quả được tạo tại PC:</div>
                          <ul className="log-files-list">
                            {log.details.files.map((f) => (
                              <li key={f.path}>
                                <code>{f.path}</code>
                                {typeof f.size_bytes === "number" && (
                                  <span className="log-file-size">
                                    ({(f.size_bytes / 1024).toFixed(1)} KB)
                                  </span>
                                )}
                                <button
                                  type="button"
                                  className="btn btn-outline btn-xs"
                                  onClick={() => navigator.clipboard.writeText(f.path)}
                                  title="Sao chép đường dẫn file"
                                >
                                  Sao chép
                                </button>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {log.details?.summary && (
                        <div className="detail-section">
                          <div className="detail-heading">Tóm tắt kết quả AI / Model:</div>
                          <pre className="log-detail-pre">{log.details.summary}</pre>
                        </div>
                      )}

                      {log.details?.errorText && (
                        <div className="detail-section">
                          <div className="detail-heading detail-heading-error">Thông tin lỗi:</div>
                          <pre className="log-detail-pre log-pre-error">{log.details.errorText}</pre>
                        </div>
                      )}

                      {log.details?.rawData && Object.keys(log.details.rawData).length > 0 && (
                        <details className="log-raw-details">
                          <summary>Dữ liệu sự kiện kỹ thuật (JSON)</summary>
                          <pre className="log-detail-pre">{JSON.stringify(log.details.rawData, null, 2)}</pre>
                        </details>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
