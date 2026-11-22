import type { RecordData } from "../../shared/api.ts";
import type { Run, RunEvent, TaskRun } from "./types.ts";

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

function formatTaskFailureText(
  errObj?: Record<string, unknown> | null,
  fallbackMessage?: unknown,
  fallbackCode?: unknown,
): { code: string; message: string; fullText: string } {
  const code = String(errObj?.code ?? fallbackCode ?? "").trim();
  const message = String(errObj?.message ?? fallbackMessage ?? "").trim() || "Thực thi thất bại";
  const fullText = code ? `[${code}] ${message}` : message;
  return { code, message, fullText };
}

export function formatRunEventsToLogItems({
  run,
  events,
  process,
  runners,
  skills,
}: {
  run: Run;
  events: RunEvent[];
  process: RecordData | null;
  runners: RecordData[];
  skills: RecordData[];
}): LogItem[] {
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

  const topic =
    (run.input?.topic as string) ||
    (run.input?.topic_directory as string) ||
    (run.input?.prompt as string) ||
    "";
  const items: LogItem[] = [];
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

      case "task_completed":
      case "task_failed": {
        const outcome = ev.data?.outcome as string | undefined;
        const exitCode = typeof ev.data?.exit_code === "number" ? ev.data.exit_code : null;
        const isSuccess = ev.event_type === "task_completed" && outcome === "succeeded";

        const localFiles = (tr?.output?.local_files as Array<{ path: string; size_bytes?: number }>) || [];
        if (localFiles.length > 0) details.files = localFiles;
        if (tr?.output?.working_directory) details.workingDir = String(tr.output.working_directory);
        if (tr?.output?.summary && typeof tr.output.summary === "string" && tr.output.summary.trim()) {
          details.summary = tr.output.summary;
        }

        if (isSuccess) {
          level = "SUCCESS";
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
          const evError =
            ev.data?.error && typeof ev.data.error === "object"
              ? (ev.data.error as Record<string, unknown>)
              : null;
          const formatted = formatTaskFailureText(
            evError || tr?.error,
            ev.data?.message ?? tr?.error?.message,
            ev.data?.error_code ?? tr?.error?.code,
          );
          details.errorText = formatted.fullText;
          const exitPart = exitCode !== null ? ` (Exit code: ${exitCode})` : "";
          const codePart = formatted.code ? ` [${formatted.code}]` : "";
          message = `Thực thi thất bại${exitPart}${codePart}: ${formatted.message}`;
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
        const failedTaskRuns = run.task_runs.filter((t: TaskRun) => t.error);
        const rawErrMsg =
          (ev.data?.message as string) ||
          (run.error?.message as string) ||
          "Quy trình dừng do lỗi";

        const eventFailedTasks = Array.isArray(ev.data?.failed_tasks)
          ? (ev.data.failed_tasks as Array<Record<string, unknown>>)
          : [];

        const detailLines: string[] = [];
        if (eventFailedTasks.length > 0) {
          for (const ft of eventFailedTasks) {
            const name = String(ft.task_name ?? ft.task_id ?? "Bước");
            const formatted = formatTaskFailureText(ft);
            detailLines.push(`• ${name}: ${formatted.fullText}`);
          }
        } else if (failedTaskRuns.length > 0) {
          for (const ft of failedTaskRuns) {
            const name = resolveNodeName(ft.task_id, ft.id);
            const formatted = formatTaskFailureText(ft.error);
            detailLines.push(`• ${name}: ${formatted.fullText}`);
          }
        }

        const displayMsg =
          rawErrMsg === "One or more tasks failed" && detailLines.length > 0
            ? detailLines[0].replace(/^•\s*/, "")
            : rawErrMsg;

        details.errorText = detailLines.length > 0 ? detailLines.join("\n") : displayMsg;
        message = `Lượt chạy thất bại: ${displayMsg}`;
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
        const extraMsg =
          (ev.data?.message as string) ||
          ((ev.data?.error as Record<string, unknown> | undefined)?.message as string);
        if (ev.data?.error) {
          level = "ERROR";
          details.errorText = formatTaskFailureText(ev.data.error as Record<string, unknown>).fullText;
        } else {
          level = "INFO";
        }
        message = extraMsg
          ? `Sự kiện hệ thống (${ev.event_type}): ${extraMsg}`
          : `Sự kiện hệ thống: ${ev.event_type}`;
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
}
