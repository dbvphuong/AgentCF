# Audit và kiểm thử quyền xuyên luồng

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## REL-002

- [x] **REL-002 — Audit và kiểm thử quyền xuyên luồng** — Hoàn thành | Verification
  - Phụ thuộc: [RUN-006](../runs/003-skill0-web.md#run-006).
  - Nghiệm thu: truy vết Run/TaskRun/Attempt, thay đổi cấu hình/quyết định, kiểm tra credential/quyền và che dữ liệu nhạy cảm; có test từ chối thực thi trái quyền. Quyền tối thiểu vẫn bắt buộc ngay [API-001](../api/001-run-client-contract.md#api-001)/[CLI-001](../client/001-authenticated-connection.md#cli-001)/[RUN-002](../runs/002-run-execution-history.md#run-002), không chờ task này mới bảo vệ.
  - Mã nguồn triển khai:
    - `AuditRepository` và tiện ích `redact_secrets` tại `apps/server/src/agent_cf_server/infrastructure/audit/repository.py`:
      - Khử trùng tự động các trường bí mật (`api_key`, `token`, `password`, `secret`, `credential`, `authorization` Bearer headers) thành `***REDACTED***` đệ quy qua dictionary, list và string.
      - Ghi nhận đầy đủ chuỗi audit xuyên suốt vòng đời: `run_created` -> `task_claimed` -> `attempt_observation` -> `task_completed` -> `run_succeeded` / `run_failed` / `run_cancelled` / `run_continued`.
      - Bảo toàn nguyên tắc Append-Only: bảng `audit_events` được bảo vệ bởi trigger SQLite ngăn chặn mọi thao tác `UPDATE` hoặc `DELETE` (`audit_immutable`).
    - Ma trận kiểm soát quyền và từ chối thực thi trái phép (Cross-System Permission Enforcement):
      - Từ chối Runner khi credential bị thu hồi (`Runner credential has expired or been revoked`).
      - Từ chối Heartbeat trên phiên làm việc bị thu hồi (`Session is not active (revoked)`).
      - Từ chối nhận việc sai Workspace (`Runner workspace mismatch`).
      - Từ chối Runner nhận task đã ghim cho PC chuyên dụng (`Task is pinned to runner 'pc-dedicated'`).
      - Từ chối Attempt khi cung cấp token thực thi không hợp lệ (`Invalid execution token`).
      - Từ chối hoàn thành Attempt khi lease thực thi đã hết hạn (`stale_execution: lease has expired`).
  - Kiểm chứng tự động:
    - `test_rel002_secret_redaction_utility`
    - `test_rel002_end_to_end_audit_trail_tracing`
    - `test_rel002_revoked_runner_and_session_rejection`
    - `test_rel002_cross_workspace_unauthorized_claim_rejection`
    - `test_rel002_pinned_runner_mismatch_rejection`
    - `test_rel002_stale_lease_and_invalid_token_rejection`
