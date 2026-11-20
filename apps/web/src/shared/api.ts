export type RecordData = Record<string, any>;

export async function request<T = RecordData>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(path, {
    method,
    signal,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      ...(method === "GET" ? {} : { "Idempotency-Key": crypto.randomUUID() }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  }).catch((error: unknown) => {
    if (method === "DELETE" && !(error instanceof Error && error.name === "AbortError")) {
      throw new Error("Không gửi được yêu cầu xóa. Kiểm tra kết nối tới Server rồi thử lại.", { cause: error });
    }
    throw error;
  });
  if (!response.ok) {
    const deleteErrors: Record<number, string> = {
      401: "Phiên đăng nhập đã hết hạn. Kết nối lại rồi thử xóa.",
      403: "Bạn không có quyền xóa mục này.",
      404: "Không tìm thấy mục cần xóa. Tải lại danh sách và thử lại.",
      409: "Chưa thể xóa do dữ liệu đang xung đột hoặc còn liên kết. Tải lại danh sách và kiểm tra các mục liên quan.",
      422: "Yêu cầu xóa chưa hợp lệ. Tải lại danh sách và thử lại.",
    };
    let detail = method === "DELETE"
      ? deleteErrors[response.status] ?? "Server chưa xử lý được yêu cầu xóa. Thử lại sau."
      : `HTTP ${response.status}`;
    try {
      const error = await response.json();
      detail =
        typeof error.detail === "string"
          ? error.detail
          : method === "DELETE" ? detail : JSON.stringify(error.detail ?? error);
    } catch {
      /* Keep the HTTP status when the server has no JSON body. */
    }
    throw new Error(detail);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const resource = (path: string, id: string) =>
  `${path}/${encodeURIComponent(id)}`;
export const dateTime = (value?: string | null) =>
  value && Number.isFinite(Date.parse(value))
    ? new Date(value).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })
    : "—";
