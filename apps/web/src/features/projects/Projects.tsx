import { useCallback, useEffect, useRef, useState } from "react";
import { Toast } from "../../shared/Toast";
import type { ToastMessage } from "../../shared/Toast";
import {
  Confirm,
  EntityForm,
  Modal,
  Notice,
  PageHead,
  useResource,
} from "../../shared/ui";
import type { Field } from "../../shared/ui";
import { request, resource } from "../../shared/api";
import type { RecordData } from "../../shared/api";
import { RunForm } from "../runs";
import { ProcessEditor } from "./processes/ProcessEditor";
import { Schedules } from "./processes/Schedules";
import type { ProjectAction } from "./ProjectActions";
import { ProjectList } from "./ProjectList";

export function Projects({
  projectId,
  processId,
}: {
  projectId?: string;
  processId?: string;
  initialTab?: string;
}) {
  const projects = useResource<RecordData[]>("/v1/projects");
  const agents = useResource<RecordData[]>("/v1/agents?status=active");
  const workspaces = useResource<RecordData[]>("/v1/workspaces");

  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => {
    const initial = new Set<string>();
    if (projectId) initial.add(projectId);
    return initial;
  });

  useEffect(() => {
    if (projectId) {
      setExpandedIds((prev) => new Set(prev).add(projectId));
    }
  }, [projectId]);

  const [targetsProjectId, setTargetsProjectId] = useState<string | null>(null);

  const [edit, setEdit] = useState<{
    kind: "project" | "workspace" | "process" | "target";
    row: RecordData;
    projectId?: string;
  } | null>(null);

  const [action, setAction] = useState<{
    kind: "project" | "process";
    row: RecordData;
    remove?: boolean;
    projectId?: string;
  } | null>(null);

  const [schedule, setSchedule] = useState<RecordData | null>(null);
  const [runProcessId, setRunProcessId] = useState("");
  const [notification, setNotification] = useState<ToastMessage | null>(null);
  const dismissNotification = useCallback(() => setNotification(null), []);
  const [cloneSource, setCloneSource] = useState<RecordData | null>(null);

  const previousProcessId = useRef(processId);
  useEffect(() => {
    if (previousProcessId.current && !processId) projects.reload();
    previousProcessId.current = processId;
  }, [processId]);

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleProjectAction = (kind: ProjectAction, row: RecordData) => {
    if (kind === "edit") setEdit({ kind: "project", row });
    else if (kind === "clone") setCloneSource(row);
    else setAction({ kind: "project", row, remove: kind === "delete" });
  };

  const reload = () => {
    projects.reload();
  };

  const fields: Field[] = [
    { key: "name", label: "Tên", required: true },
    { key: "description", label: "Mô tả", type: "textarea" },
  ];

  const projectFields: Field[] = [
    ...fields,
    {
      key: "working_directory",
      label: "Thư mục Project trên PC",
      hint: "Thư mục mở trong Codex/Antigravity, chứa các Skill và thư mục chủ đề. Các node mới dùng thư mục này nếu không có cấu hình riêng.",
    },
    {
      key: "workspace_id",
      label: "Workspace",
      type: "select",
      immutable: true,
      required: true,
      options: workspaces.data ?? [],
    },
    {
      key: "pm_agent_id",
      label: "PM",
      type: "select",
      required: true,
      options: agents.data ?? [],
    },
  ];

  const targetFields: Field[] = [
    { key: "name", label: "Tên mục tiêu", required: true },
    {
      key: "period",
      label: "Kỳ",
      type: "select",
      required: true,
      default: "monthly",
      options: [
        { id: "monthly", name: "Tháng" },
        { id: "weekly", name: "Tuần" },
      ],
    },
    { key: "starts_on", label: "Bắt đầu", type: "date", required: true },
    { key: "ends_on", label: "Kết thúc", type: "date", required: true },
    {
      key: "target_count",
      label: "Số lượng mục tiêu",
      type: "number",
      min: 1,
      required: true,
    },
    {
      key: "completed_count",
      label: "Kết quả được duyệt",
      type: "number",
      min: 0,
      default: 0,
      required: true,
    },
    {
      key: "acceptance_criteria",
      label: "Tiêu chí nghiệm thu",
      type: "textarea",
      required: true,
    },
  ];

  const activeProject = projectId
    ? projects.data?.find((p) => p.id === projectId)
    : null;

  if (processId && (activeProject || projectId)) {
    const projectForEditor =
      activeProject || { id: projectId!, name: "Project", workspace_id: "" };
    return (
      <ProcessEditor
        processId={processId}
        project={projectForEditor}
        onBack={() => {
          window.location.hash = "projects";
        }}
      />
    );
  }

  const targetsProject = targetsProjectId
    ? projects.data?.find((p) => p.id === targetsProjectId) ?? null
    : null;

  return (
    <>
      <PageHead title="Projects" />
      {[projects.error, agents.error, workspaces.error]
        .filter(Boolean)
        .map((e, i) => (
          <Notice error key={i}>
            {e}
          </Notice>
        ))}
      <Toast message={notification} onDismiss={dismissNotification} />

      <ProjectList
        projects={projects.data ?? []}
        loading={projects.loading}
        onReload={reload}
        onCreate={() => setEdit({ kind: "project", row: {} })}
        onWorkspace={() => setEdit({ kind: "workspace", row: {} })}
        onAction={handleProjectAction}
        expandedIds={expandedIds}
        onToggleExpand={toggleExpand}
        onOpenTargets={(p) => setTargetsProjectId(p.id)}
        onAddProcess={(p) =>
          setEdit({ kind: "process", row: {}, projectId: p.id })
        }
        onEditProcess={(proc, p) =>
          setEdit({ kind: "process", row: proc, projectId: p.id })
        }
        onDeleteProcess={(proc) =>
          setAction({ kind: "process", row: proc, remove: true })
        }
        onRunProcess={(procId) => setRunProcessId(procId)}
        onScheduleProcess={(proc) => setSchedule(proc)}
      />

      {/* Target Management Modal */}
      {targetsProject && (
        <Modal
          title={`Mục tiêu dự án · ${targetsProject.name}`}
          onClose={() => setTargetsProjectId(null)}
        >
          <div className="targets-modal-content">
            <div
              className="section-heading"
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 14,
              }}
            >
              <span className="muted" style={{ fontSize: 13 }}>
                Chỉ tiêu sản lượng và kết quả nghiệm thu theo kỳ của dự án.
              </span>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() =>
                  setEdit({
                    kind: "target",
                    row: {},
                    projectId: targetsProject.id,
                  })
                }
              >
                ＋ Thêm mục tiêu
              </button>
            </div>
            {(targetsProject.targets ?? []).length > 0 ? (
              <div className="table-scroll">
                <table className="targets-table">
                  <thead>
                    <tr>
                      <th style={{ width: "32%" }}>Mục tiêu</th>
                      <th style={{ width: "14%" }}>Kỳ</th>
                      <th style={{ width: "22%" }}>Thời gian</th>
                      <th style={{ width: "20%" }}>Đã duyệt / Chỉ tiêu</th>
                      <th style={{ width: "12%", textAlign: "right" }}>
                        Thao tác
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {targetsProject.targets.map((t: RecordData) => (
                      <tr key={t.id}>
                        <td>
                          <strong>{t.name}</strong>
                          {t.acceptance_criteria && (
                            <div className="cell-note">
                              {t.acceptance_criteria}
                            </div>
                          )}
                        </td>
                        <td>{t.period === "monthly" ? "Tháng" : "Tuần"}</td>
                        <td>
                          {t.starts_on ?? "—"} → {t.ends_on ?? "—"}
                        </td>
                        <td>
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 8,
                            }}
                          >
                            <span style={{ fontWeight: 600 }}>
                              {t.completed_count} / {t.target_count}
                            </span>
                            <progress
                              style={{ width: 70, height: 7 }}
                              max={t.target_count || 1}
                              value={t.completed_count}
                            />
                          </div>
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <button
                            type="button"
                            className="btn btn-outline btn-sm"
                            onClick={() =>
                              setEdit({
                                kind: "target",
                                row: t,
                                projectId: targetsProject.id,
                              })
                            }
                          >
                            Sửa
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div
                style={{
                  padding: "24px 16px",
                  textAlign: "center",
                  color: "#8a7d97",
                }}
              >
                Chưa có mục tiêu nào. Bấm <strong>＋ Thêm mục tiêu</strong> để
                đặt chỉ tiêu sản lượng cho dự án.
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Edit/Create Modal */}
      {edit && (
        <Modal
          title={`${edit.row.id ? "Sửa" : "Thêm"} ${
            edit.kind === "project"
              ? "Project"
              : edit.kind === "workspace"
                ? "Workspace"
                : edit.kind === "process"
                  ? "Process"
                  : "Mục tiêu"
          }`}
          onClose={() => setEdit(null)}
        >
          <EntityForm
            initial={edit.row}
            fields={
              edit.kind === "workspace"
                ? [fields[0]]
                : edit.kind === "project"
                  ? projectFields
                  : edit.kind === "target"
                    ? targetFields
                    : fields
            }
            onCancel={() => setEdit(null)}
            onSave={async (data) => {
              const base =
                edit.kind === "workspace"
                  ? "/v1/workspaces"
                  : edit.kind === "project"
                    ? "/v1/projects"
                    : edit.kind === "target"
                      ? `/v1/projects/${encodeURIComponent(edit.projectId!)}/targets`
                      : edit.row.id
                        ? "/v1/processes"
                        : `/v1/projects/${encodeURIComponent(edit.projectId!)}/processes`;
              await request(
                edit.row.id ? resource(base, edit.row.id) : base,
                edit.row.id ? "PATCH" : "POST",
                data,
              );
              setEdit(null);
              reload();
              workspaces.reload();
            }}
          />
        </Modal>
      )}

      {/* Clone Source Modal */}
      {cloneSource && (
        <Modal
          title={`Nhân bản “${cloneSource.name}”`}
          onClose={() => setCloneSource(null)}
        >
          <p className="project-clone-note">
            Sao chép toàn bộ cấu hình, thành viên, Process và Targets (giữ số
            liệu hiện tại). Lịch ở bản sao luôn tắt; không chép lịch sử Run, Logs
            hoặc artifact. Agent, Skill, Robot và PC tiếp tục dùng chung danh
            mục.
          </p>
          <EntityForm
            fields={[{ key: "name", label: "Tên Project mới", required: true }]}
            initial={{ name: `${cloneSource.name} (bản sao)` }}
            submitLabel="Nhân bản Project"
            busyLabel="Đang nhân bản…"
            onCancel={() => setCloneSource(null)}
            onSave={async (data) => {
              const copied = await request(
                `${resource("/v1/projects", cloneSource.id)}/clone`,
                "POST",
                data,
              );
              setCloneSource(null);
              setNotification({
                tone: "success",
                text: `Đã tạo bản sao “${copied.name}”. Các lịch chạy của bản sao đang tắt.`,
              });
              reload();
            }}
          />
        </Modal>
      )}

      {/* Action / Confirm Modal */}
      {action && (
        <Confirm
          title={`${action.remove ? "Xóa" : action.row.status === "archived" ? "Kích hoạt lại" : "Ngừng hoạt động"} “${action.row.name}”?`}
          confirmLabel={
            action.remove
              ? `Xóa ${action.kind === "project" ? "Project" : "Process"}`
              : action.row.status === "archived"
                ? "Kích hoạt lại"
                : "Ngừng hoạt động"
          }
          danger={!!action.remove || action.row.status === "active"}
          onError={(failure) =>
            setNotification({ tone: "error", text: failure.message })
          }
          onClose={() => {
            setAction(null);
            if (notification?.tone === "error") dismissNotification();
          }}
          onConfirm={async () => {
            const path = resource(
              action.kind === "project" ? "/v1/projects" : "/v1/processes",
              action.row.id,
            );
            const result = await request(
              action.remove
                ? path
                : `${path}/${action.row.status === "archived" ? "restore" : "archive"}`,
              action.remove ? "DELETE" : "POST",
            );
            if (action.remove && result?.deleted !== true)
              throw new Error(
                "Project/Process chưa được xóa. Hãy tải lại trang và thử lại.",
              );
            setNotification({
              tone: "success",
              text: action.remove
                ? `Đã xóa “${action.row.name}” cùng lịch sử thuộc nó.`
                : `Đã ${action.row.status === "archived" ? "kích hoạt lại" : "ngừng hoạt động"} “${action.row.name}”.`,
            });
            reload();
          }}
        >
          {action.remove
            ? `Xóa vĩnh viễn ${action.kind === "project" ? "Project cùng các Process, thành viên và Targets thuộc nó" : "Process này"}, toàn bộ cấu hình, lịch chạy và lịch sử Run/Logs/artifact trên hệ thống. Không thể hoàn tác. Skill, Agent dùng chung và file trên PC được giữ nguyên. Nếu còn Run chưa kết thúc, cần dừng Run và chờ kết thúc trước khi xóa.`
            : action.row.status === "archived"
              ? `${action.kind === "project" ? "Project" : "Process"} sẽ trở lại trạng thái Đang hoạt động. Các lịch chạy vẫn tắt; bạn cần bật lại lịch mong muốn. Dữ liệu và lịch sử được giữ nguyên.`
              : `${action.kind === "project" ? "Project" : "Process"} sẽ chuyển sang Không hoạt động và các lịch chạy liên quan sẽ tắt. Dữ liệu và lịch sử được giữ nguyên. Nếu còn Run chưa kết thúc, hệ thống sẽ chặn thao tác này.`}
        </Confirm>
      )}

      {/* Schedules Modal */}
      {schedule && (
        <Schedules
          process={schedule}
          projectId={schedule.project_id || projectId || ""}
          onClose={() => setSchedule(null)}
        />
      )}

      {/* Run Form Modal */}
      {runProcessId && (
        <Modal title="Chạy Process" onClose={() => setRunProcessId("")}>
          <RunForm
            embedded
            initialProcessId={runProcessId}
            onCancel={() => setRunProcessId("")}
            onRunCreated={(run) => {
              window.location.hash = `runs/${encodeURIComponent(run.id)}`;
              setRunProcessId("");
            }}
          />
        </Modal>
      )}
    </>
  );
}
