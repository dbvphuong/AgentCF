export interface Health {
  status: "ok";
  database: { schema_version: number };
  temporal: { configured: boolean };
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseHealth(value: unknown): Health {
  if (
    !isObject(value) || value.status !== "ok" ||
    !isObject(value.database) ||
    typeof value.database.schema_version !== "number" ||
    !Number.isSafeInteger(value.database.schema_version) || value.database.schema_version < 1 ||
    !isObject(value.temporal) || typeof value.temporal.configured !== "boolean"
  ) {
    throw new Error("Phản hồi kiểm tra kết nối không hợp lệ.");
  }
  return {
    status: "ok",
    database: { schema_version: value.database.schema_version },
    temporal: { configured: value.temporal.configured },
  };
}

export async function fetchHealth(
  request: typeof fetch = fetch,
  signal?: AbortSignal,
): Promise<Health> {
  const response = await request("/healthz", {
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(5000)]) : AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error(`Server trả mã HTTP ${response.status}.`);
  let value: unknown;
  try {
    if (!response.body) throw new Error();
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8", { fatal: true });
    let content = "";
    let size = 0;
    try {
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        size += chunk.value.byteLength;
        if (size > 16384) {
          await reader.cancel();
          throw new Error();
        }
        content += decoder.decode(chunk.value, { stream: true });
      }
      content += decoder.decode();
    } finally {
      reader.releaseLock();
    }
    value = JSON.parse(content);
  } catch {
    throw new Error("Phản hồi kiểm tra kết nối không hợp lệ.");
  }
  return parseHealth(value);
}
