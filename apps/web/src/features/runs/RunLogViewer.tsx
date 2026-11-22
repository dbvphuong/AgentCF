import { useMemo, useState } from "react";
import type { RecordData } from "../../shared/api";
import type { Run, RunEvent } from "./types";
import { formatRunEventsToLogItems, type LogItem, type LogLevel } from "./formatRunLog";

export type { LogItem, LogLevel };

interface RunLogViewerProps {
  run: Run;
  events: RunEvent[];
  process: RecordData | null;
  runners: RecordData[];
  skills: RecordData[];
}

export function RunLogViewer({ run, events, process, runners, skills }: RunLogViewerProps) {
  const [levelFilter, setLevelFilter] = useState<LogLevel>("ALL");
  const [nodeFilter, setNodeFilter] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState<boolean>(false);

  const logItems: LogItem[] = useMemo(
    () => formatRunEventsToLogItems({ run, events, process, runners, skills }),
    [events, run, process, runners, skills],
  );

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
    const lines = filteredLogs.map((l) => {
      const base = `[${l.timeStr}] [${l.level.padEnd(7)}] [Node: ${l.nodeName}] [Skill: ${l.skillName}] ${l.message}`;
      return l.details?.errorText ? `${base}\n  -> ${l.details.errorText}` : base;
    });
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
