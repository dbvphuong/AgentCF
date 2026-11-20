# Kết nối và giao việc có xác thực

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## CLI-001

- [x] **CLI-001 — Kết nối và nhận/gửi kết quả có xác thực** — Xong | Feature
  - Phụ thuộc: [BASE-002](../base/002-application-bootstrap.md#base-002), [API-001](../api/001-run-client-contract.md#api-001), [REL-004](../execution/001-execution-permissions.md#rel-004).
  - Nghiệm thu: Client có identity/phạm vi quyền, nhận đúng TaskRun, báo kết quả gắn Run/TaskRun/Attempt và quyền thực thi theo contract; request giao việc lặp không tự chạy thêm. Kiểm thử credential sai/thu hồi, giao trùng và quyền thực thi không còn hợp lệ. Chỉ Server truy cập DB nghiệp vụ. Theo [contract Client](../../../architecture/client-protocol.md) và [OpenAPI](../../../../openapi/openapi.yaml): kiểm chứng pairing/session, journal trước spawn, claim/renew/observations và receipt sau mất phản hồi; không cấp lại quyền khi tiến trình cũ chưa rõ.
  - Bằng chứng 2026-11-16: `ClientSessionManager` (`apps/client/src/agent_cf_client/connection/client_session.py`), `RunnerRepository` và API routes `/v1/runners/` (ghép nối, mở session, gửi heartbeat với Bearer token, session deduplication khi mở session mới sẽ revoke session cũ, từ chối heartbeat session cũ 403, kiểm thử credential revoked trả 401). Journaling bền vững trước spawn qua `ExecutionJournal`. Đã kiểm thử tự động tại `test_client_execution.py`.
