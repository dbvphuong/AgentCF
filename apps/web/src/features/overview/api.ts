import type { OverviewSummaryData } from "./types";

function generateKey(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export async function fetchOverviewSummary(signal?: AbortSignal): Promise<OverviewSummaryData> {
  const resp = await fetch("/v1/overview/summary", {
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!resp.ok) {
    throw new Error(`Lỗi tải dữ liệu Tổng quan: HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function acknowledgeRunError(
  runId: string,
  notes = "",
  signal?: AbortSignal
): Promise<{ run_id: string; status: string; acknowledged_at: string }> {
  const resp = await fetch(`/v1/runs/${encodeURIComponent(runId)}/acknowledge-error`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "Idempotency-Key": generateKey("ack"),
    },
    body: JSON.stringify({ notes }),
    signal,
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(`Xử lý cảnh báo lỗi thất bại (HTTP ${resp.status}): ${errorText}`);
  }
  return resp.json();
}
