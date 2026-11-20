import type {
  CreateRobotPayload,
  CreateRobotVersionPayload,
  Robot,
  RobotStatistics,
  RobotVersion,
  UpdateRobotPayload,
} from "./types";
import { request } from "../../shared/api";

export async function fetchRobots(statusFilter?: string, signal?: AbortSignal): Promise<Robot[]> {
  const url = statusFilter ? `/v1/robots?status=${encodeURIComponent(statusFilter)}` : "/v1/robots";
  const resp = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!resp.ok) {
    throw new Error(`Lỗi tải danh sách Robot: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function fetchRobot(robotId: string, signal?: AbortSignal): Promise<Robot> {
  const resp = await fetch(`/v1/robots/${encodeURIComponent(robotId)}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!resp.ok) {
    throw new Error(`Lỗi tải thông tin Robot: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function createRobot(payload: CreateRobotPayload, signal?: AbortSignal): Promise<Robot> {
  const resp = await fetch("/v1/robots", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    signal,
  });
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Tạo Robot thất bại (HTTP ${resp.status}): ${errText}`);
  }
  return resp.json();
}

export async function updateRobot(robotId: string, payload: UpdateRobotPayload, signal?: AbortSignal): Promise<Robot> {
  const resp = await fetch(`/v1/robots/${encodeURIComponent(robotId)}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    signal,
  });
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Cập nhật Robot thất bại (HTTP ${resp.status}): ${errText}`);
  }
  return resp.json();
}

export async function deleteRobot(robotId: string, signal?: AbortSignal): Promise<void> {
  await request<void>(`/v1/robots/${encodeURIComponent(robotId)}`, "DELETE", undefined, signal);
}

export async function fetchRobotVersions(robotId: string, signal?: AbortSignal): Promise<RobotVersion[]> {
  const resp = await fetch(`/v1/robots/${encodeURIComponent(robotId)}/versions`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!resp.ok) {
    throw new Error(`Lỗi tải phiên bản Robot: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function createRobotVersion(
  robotId: string,
  payload: CreateRobotVersionPayload,
  signal?: AbortSignal
): Promise<RobotVersion> {
  const resp = await fetch(`/v1/robots/${encodeURIComponent(robotId)}/versions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    signal,
  });
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Tạo version mới thất bại (HTTP ${resp.status}): ${errText}`);
  }
  return resp.json();
}

export async function publishRobotVersion(
  robotId: string,
  versionId: string,
  bundleSha256?: string,
  signal?: AbortSignal
): Promise<RobotVersion> {
  const resp = await fetch(`/v1/robots/${encodeURIComponent(robotId)}/versions/${encodeURIComponent(versionId)}/publish`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(bundleSha256 ? { bundle_sha256: bundleSha256 } : {}),
    signal,
  });
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Publish version thất bại (HTTP ${resp.status}): ${errText}`);
  }
  return resp.json();
}

export async function fetchRobotStatistics(robotId: string, signal?: AbortSignal): Promise<RobotStatistics> {
  const resp = await fetch(`/v1/robots/${encodeURIComponent(robotId)}/statistics`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!resp.ok) {
    throw new Error(`Lỗi tải thống kê Robot: HTTP ${resp.status}`);
  }
  return resp.json();
}
