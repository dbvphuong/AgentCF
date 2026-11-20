import type { CreateRunPayload, Run, RunEvent } from "./types";

function generateKey(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export async function fetchRuns(
  statusFilter?: string,
  signal?: AbortSignal,
  projectId?: string,
): Promise<Run[]> {
  const params = new URLSearchParams();
  if (statusFilter) params.set("status", statusFilter);
  if (projectId) params.set("project_id", projectId);
  const url = `/v1/runs${params.size ? `?${params}` : ""}`;
  const resp = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!resp.ok) {
    throw new Error(`Lỗi tải danh sách Run: HTTP ${resp.status}`);
  }
  const data = await resp.json();
  return data.items || [];
}

export async function fetchRun(
  runId: string,
  signal?: AbortSignal,
): Promise<Run> {
  const resp = await fetch(`/v1/runs/${encodeURIComponent(runId)}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!resp.ok) {
    throw new Error(`Lỗi tải thông tin Run: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function createRun(
  payload: CreateRunPayload,
  signal?: AbortSignal,
): Promise<Run> {
  const resp = await fetch("/v1/runs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "Idempotency-Key": generateKey("run"),
    },
    body: JSON.stringify(payload),
    signal,
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(
      `Khởi tạo Run thất bại (HTTP ${resp.status}): ${errorText}`,
    );
  }
  return resp.json();
}

export async function cancelRun(
  runId: string,
  reason = "Operator cancelled",
  signal?: AbortSignal,
): Promise<Run> {
  const resp = await fetch(`/v1/runs/${encodeURIComponent(runId)}/cancel`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "Idempotency-Key": generateKey("cancel"),
    },
    body: JSON.stringify({ reason }),
    signal,
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(`Hủy Run thất bại (HTTP ${resp.status}): ${errorText}`);
  }
  return resp.json();
}

export interface ContinueRunPayload {
  task_id?: string;
  decision?: string;
  feedback?: string;
  input?: Record<string, unknown>;
}

export async function continueRun(
  runId: string,
  payload: ContinueRunPayload = {},
  signal?: AbortSignal,
): Promise<Run> {
  const resp = await fetch(`/v1/runs/${encodeURIComponent(runId)}/continue`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "Idempotency-Key": generateKey("continue"),
    },
    body: JSON.stringify(payload),
    signal,
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(
      `Tiếp tục Run thất bại (HTTP ${resp.status}): ${errorText}`,
    );
  }
  return resp.json();
}

export async function fetchRunEvents(
  runId: string,
  signal?: AbortSignal,
): Promise<RunEvent[]> {
  const resp = await fetch(
    `/v1/runs/${encodeURIComponent(runId)}/events?limit=100`,
    {
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal,
    },
  );
  if (!resp.ok) {
    throw new Error(`Lỗi tải sự kiện Run: HTTP ${resp.status}`);
  }
  const data = await resp.json();
  return data.items || [];
}

export function downloadArtifactUrl(artifactId: string): string {
  return `/v1/artifacts/${encodeURIComponent(artifactId)}/content`;
}

export async function fetchArtifactText(
  artifactId: string,
  signal?: AbortSignal,
): Promise<string> {
  const resp = await fetch(downloadArtifactUrl(artifactId), {
    headers: { Accept: "text/plain, */*" },
    signal,
  });
  if (!resp.ok) {
    throw new Error(`Không thể đọc nội dung artifact: HTTP ${resp.status}`);
  }
  return resp.text();
}

export async function createProcessRun(processId: string, input: Record<string, unknown>): Promise<Run> {
  const resp = await fetch(`/v1/processes/${encodeURIComponent(processId)}/runs`, {
    method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": generateKey("run") },
    body: JSON.stringify({ input }),
  });
  if (!resp.ok) {
    const error = await resp.json();
    throw new Error(typeof error.detail === "string" ? error.detail : "Không thể chạy Process. Kiểm tra cấu hình đã lưu.");
  }
  return resp.json();
}
