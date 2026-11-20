import { useState } from "react";
import type { ComponentProps } from "react";
import type { RecordData } from "../../shared/api";
import { Notice } from "../../shared/ui";
import { ProjectActions } from "./ProjectActions";
import { filterProjects } from "./filterProjects";
import "./projects.css";

export function ProjectList({
  projects,
  loading,
  onReload,
  onCreate,
  onWorkspace,
  onAction,
  expandedIds,
  onToggleExpand,
  onOpenTargets,
  onAddProcess,
  onEditProcess,
  onDeleteProcess,
  onRunProcess,
  onScheduleProcess,
}: {
  projects: RecordData[];
  loading: boolean;
  onReload: () => void;
  onCreate: () => void;
  onWorkspace: () => void;
  onAction: ComponentProps<typeof ProjectActions>["onAction"];
  expandedIds: Set<string>;
  onToggleExpand: (projectId: string) => void;
  onOpenTargets: (project: RecordData) => void;
  onAddProcess: (project: RecordData) => void;
  onEditProcess: (process: RecordData, project: RecordData) => void;
  onDeleteProcess: (process: RecordData) => void;
  onRunProcess: (processId: string) => void;
  onScheduleProcess: (process: RecordData) => void;
}) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("active");
  const filtered = filterProjects(projects, status, search);

  return (
    <section className="panel projects-list" aria-label="Danh sách Projects">
      <div className="projects-toolbar">
        <div className="projects-filters">
          <div className="project-search">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              aria-hidden="true"
            >
              <circle cx="10.5" cy="10.5" r="6.5" />
              <path d="m16 16 4.5 4.5" />
            </svg>
            <input
              aria-label="Tìm Project"
              placeholder="Tìm tên, mô tả hoặc thành viên…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <select
            aria-label="Trạng thái Project"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="all">Tất cả</option>
            <option value="active">Đang hoạt động</option>
            <option value="archived">Không hoạt động</option>
          </select>
          <button
            type="button"
            className="projects-refresh"
            title="Làm mới"
            aria-label="Làm mới Projects"
            disabled={loading}
            onClick={onReload}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1" />
            </svg>
          </button>
        </div>
        <div className="row-actions">
          <button
            type="button"
            className="btn btn-outline"
            onClick={onWorkspace}
          >
            + Workspace
          </button>
          <button
            type="button"
            className="btn btn-primary projects-create"
            aria-label="Tạo Project"
            onClick={onCreate}
          >
            <span aria-hidden="true">＋</span> Tạo Project
          </button>
        </div>
      </div>

      {loading && !projects.length ? (
        <Notice>Đang tải Projects…</Notice>
      ) : (
        <>
          <div className="table-scroll">
            <table className="projects-table" aria-busy={loading}>
              <colgroup>
                <col className="project-name-col" style={{ width: "26%" }} />
                <col className="project-description-col" style={{ width: "22%" }} />
                <col className="project-team-col" style={{ width: "22%" }} />
                <col className="project-target-col" style={{ width: "13%" }} />
                <col className="project-status-col" style={{ width: "11%" }} />
                <col className="project-actions-col" style={{ width: "60px" }} />
              </colgroup>
              <thead>
                <tr>
                  <th scope="col">Project</th>
                  <th scope="col">Mô tả</th>
                  <th scope="col">Thành viên</th>
                  <th scope="col">Mục tiêu</th>
                  <th scope="col">Trạng thái</th>
                  <th scope="col">
                    <span className="visually-hidden">Thao tác</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((project) => {
                  const isExpanded = expandedIds.has(project.id);
                  const processes = (project.processes ?? []).filter(
                    (p: RecordData) => p.status !== "archived",
                  );
                  const team = project.team ?? [];
                  const targets = project.targets ?? [];
                  const completedCount = targets.reduce(
                    (acc: number, t: RecordData) => acc + (t.completed_count || 0),
                    0,
                  );
                  const targetCount = targets.reduce(
                    (acc: number, t: RecordData) => acc + (t.target_count || 0),
                    0,
                  );
                  const nonPmAgents = team.filter(
                    (a: RecordData) => a.id !== project.pm_agent_id,
                  );

                  return [
                    <tr
                      key={project.id}
                      className={isExpanded ? "project-row-expanded" : undefined}
                    >
                      <td>
                        <div className="project-name-wrapper">
                          <button
                            type="button"
                            className={`project-expand-toggle ${isExpanded ? "is-expanded" : ""}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              onToggleExpand(project.id);
                            }}
                            aria-label={
                              isExpanded
                                ? `Thu gọn ${project.name}`
                                : `Mở rộng ${project.name}`
                            }
                            title={
                              isExpanded
                                ? "Thu gọn danh sách quy trình"
                                : "Bấm để xem các quy trình (Processes)"
                            }
                          >
                            <svg
                              width="14"
                              height="14"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2.5"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <path d="m9 18 6-6-6-6" />
                            </svg>
                          </button>
                          <button
                            type="button"
                            className="project-name-btn"
                            onClick={() => onToggleExpand(project.id)}
                            title="Bấm để xem / đóng các Process"
                          >
                            <span className="project-folder" aria-hidden="true">
                              <svg
                                width="18"
                                height="18"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="1.6"
                                strokeLinejoin="round"
                              >
                                <path d="M3 7V4h6l2 3h10v13H3Z" />
                              </svg>
                            </span>
                            <div className="project-title-meta">
                              <span className="project-title-text">
                                {project.name}
                              </span>
                              <span className="project-process-pill">
                                {processes.length} quy trình
                              </span>
                            </div>
                          </button>
                        </div>
                      </td>
                      <td>
                        <span
                          className={`project-description ${!project.description ? "is-empty" : ""}`}
                          title={project.description || undefined}
                        >
                          {project.description || "Chưa có mô tả"}
                        </span>
                      </td>
                      <td>
                        <div className="project-members">
                          {project.pm_name ? (
                            <span
                              className="member-tag member-pm"
                              title={`PM: ${project.pm_name}`}
                            >
                              <span className="member-icon">👑</span>
                              <span className="member-name">
                                {project.pm_name}
                              </span>
                            </span>
                          ) : (
                            <span className="member-unassigned">Chưa có PM</span>
                          )}
                          {(() => {
                            if (!nonPmAgents.length) return null;
                            const maxVisible = 2;
                            const visible = nonPmAgents.slice(0, maxVisible);
                            const hiddenCount = nonPmAgents.length - maxVisible;
                            return (
                              <>
                                {visible.map((a: RecordData) => (
                                  <span
                                    key={a.id}
                                    className="member-tag"
                                    title={`Agent: ${a.name}`}
                                  >
                                    <span className="member-icon">👤</span>
                                    <span className="member-name">{a.name}</span>
                                  </span>
                                ))}
                                {hiddenCount > 0 && (
                                  <span
                                    className="member-tag member-more"
                                    title={nonPmAgents
                                      .map((a: RecordData) => a.name)
                                      .join(", ")}
                                  >
                                    +{hiddenCount}
                                  </span>
                                )}
                              </>
                            );
                          })()}
                        </div>
                      </td>
                      <td>
                        {targets.length > 0 ? (
                          <button
                            type="button"
                            className="target-summary-badge"
                            onClick={() => onOpenTargets(project)}
                            title="Bấm để xem và sửa mục tiêu sản lượng"
                          >
                            <span className="target-icon">🎯</span>
                            <span className="target-counts">
                              {completedCount}/{targetCount}
                            </span>
                            {targetCount > 0 && (
                              <span className="target-pct">
                                {Math.round((completedCount / targetCount) * 100)}%
                              </span>
                            )}
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="target-empty-badge"
                            onClick={() => onOpenTargets(project)}
                            title="Bấm để đặt mục tiêu cho dự án này"
                          >
                            <span className="target-icon">🎯</span>
                            <span>+ Mục tiêu</span>
                          </button>
                        )}
                      </td>
                      <td>
                        <span
                          className={`project-status ${project.status === "active" ? "is-active" : "is-inactive"}`}
                        >
                          <span aria-hidden="true" />
                          {project.status === "active"
                            ? "Đang hoạt động"
                            : "Không hoạt động"}
                        </span>
                      </td>
                      <td className="project-actions-cell">
                        <ProjectActions project={project} onAction={onAction} />
                      </td>
                    </tr>,
                    isExpanded && (
                      <tr
                        key={`${project.id}-nested`}
                        className="project-nested-row"
                      >
                        <td colSpan={6} className="project-nested-cell">
                          <div className="nested-processes-panel">
                            <div className="nested-processes-header">
                              <div className="nested-header-title">
                                <span className="nested-icon">⚡</span>
                                <strong>
                                  Quy trình (Processes) của {project.name}
                                </strong>
                                <span className="process-count-badge">
                                  {processes.length}
                                </span>
                              </div>
                              <button
                                type="button"
                                className="btn btn-outline btn-sm"
                                disabled={project.status !== "active"}
                                onClick={() => onAddProcess(project)}
                              >
                                ＋ Thêm Process
                              </button>
                            </div>

                            {processes.length > 0 ? (
                              <div className="nested-table-scroll">
                                <table className="nested-processes-table">
                                  <thead>
                                    <tr>
                                      <th style={{ width: "36%" }}>
                                        Tên Process
                                      </th>
                                      <th style={{ width: "16%" }}>
                                        Trạng thái
                                      </th>
                                      <th
                                        style={{
                                          width: "48%",
                                          textAlign: "right",
                                        }}
                                      >
                                        Thao tác
                                      </th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {processes.map((p: RecordData) => (
                                      <tr key={p.id}>
                                        <td>
                                          <a
                                            className="nested-process-link"
                                            href={`#projects/${encodeURIComponent(project.id)}/processes/${encodeURIComponent(p.id)}`}
                                            title="Bấm để mở Canvas thiết kế quy trình"
                                          >
                                            <span className="process-flow-icon">
                                              ☊
                                            </span>
                                            <span className="nested-process-name">
                                              {p.name}
                                            </span>
                                          </a>
                                          {p.description && (
                                            <div className="nested-process-desc">
                                              {p.description}
                                            </div>
                                          )}
                                        </td>
                                        <td>
                                          <span className="badge">
                                            {p.status === "active"
                                              ? "Đang hoạt động"
                                              : p.status}
                                          </span>
                                        </td>
                                        <td>
                                          <div className="nested-process-actions">
                                            {p.status === "active" &&
                                              project.status === "active" && (
                                                <>
                                                  <button
                                                    type="button"
                                                    className="btn btn-primary btn-sm"
                                                    onClick={() =>
                                                      onRunProcess(p.id)
                                                    }
                                                    title="Chạy quy trình ngay"
                                                  >
                                                    ▶ Chạy
                                                  </button>
                                                  <button
                                                    type="button"
                                                    className="btn btn-outline btn-sm"
                                                    onClick={() =>
                                                      onScheduleProcess(p)
                                                    }
                                                    title="Cài đặt lịch chạy tự động"
                                                  >
                                                    ⏱ Lịch
                                                  </button>
                                                </>
                                              )}
                                            <a
                                              className="btn btn-outline btn-sm"
                                              href={`#projects/${encodeURIComponent(project.id)}/processes/${encodeURIComponent(p.id)}`}
                                              title="Mở Canvas thiết kế sơ đồ node"
                                            >
                                              ✎ Sửa sơ đồ
                                            </a>
                                            <button
                                              type="button"
                                              className="btn btn-outline btn-sm"
                                              onClick={() =>
                                                onEditProcess(p, project)
                                              }
                                              title="Đổi tên hoặc mô tả Process"
                                            >
                                              Sửa tên
                                            </button>
                                            <a
                                              className="btn btn-outline btn-sm"
                                              href={`#runs?process_id=${encodeURIComponent(p.id)}`}
                                              title="Xem lịch sử chạy trong menu Runs"
                                            >
                                              Lịch sử
                                            </a>
                                            <button
                                              type="button"
                                              className="btn btn-danger btn-sm"
                                              onClick={() =>
                                                onDeleteProcess(p)
                                              }
                                              title="Xóa Process này"
                                            >
                                              Xóa
                                            </button>
                                          </div>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            ) : (
                              <div className="nested-empty-processes">
                                <span>
                                  Project này chưa có quy trình nào.
                                </span>
                                <button
                                  type="button"
                                  className="btn btn-primary btn-sm"
                                  disabled={project.status !== "active"}
                                  onClick={() => onAddProcess(project)}
                                  style={{ marginLeft: 12 }}
                                >
                                  ＋ Tạo Process đầu tiên
                                </button>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    ),
                  ];
                })}
                {!filtered.length && (
                  <tr>
                    <td colSpan={6}>
                      <div className="projects-empty">
                        <span
                          className="projects-empty-icon"
                          aria-hidden="true"
                        >
                          ▱
                        </span>
                        <strong>
                          {projects.length
                            ? "Không tìm thấy Project phù hợp"
                            : "Bắt đầu với Project đầu tiên"}
                        </strong>
                        <p>
                          {projects.length
                            ? "Thử đổi từ khóa hoặc trạng thái để tìm Project."
                            : "Tạo Project để tổ chức công việc, thành viên và các Process của bạn."}
                        </p>
                        {!projects.length && (
                          <button
                            type="button"
                            className="btn btn-primary"
                            onClick={onCreate}
                          >
                            Tạo Project
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="projects-table-footer">
            Hiển thị <strong>{filtered.length}</strong> trong {projects.length}{" "}
            Project
          </div>
        </>
      )}
    </section>
  );
}
