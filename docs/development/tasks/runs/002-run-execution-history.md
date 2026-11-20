# Điều phối và API lịch sử chạy

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## RUN-002

- [x] **RUN-002 — Server tạo và điều phối lượt chạy thật** — Xong | Feature
  - Phụ thuộc: [RUN-001](001-skill0-run-design.md#run-001), [API-001](../api/001-run-client-contract.md#api-001), [DATA-001](../data/001-sqlite-persistence.md#data-001), [BASE-003](../base/002-application-bootstrap.md#base-003), [REL-004](../execution/001-execution-permissions.md#rel-004), [CLI-001](../client/001-authenticated-connection.md#cli-001), [RTM-005](../runtime/002-codex-adapter.md#rtm-005).
  - Nghiệm thu: request hợp lệ tạo dữ liệu bền vững và bộ điều phối ngoài HTTP giao cho Client; triển khai ranh giới ghi DB/gửi engine đã chốt ở [BASE-001](../base/001-foundation-design.md#base-001). Lỗi runtime được lưu, đóng HTTP/tab không dừng công việc. Có test thành công, lỗi, đầu vào sai, request/giao việc trùng, kết quả đến muộn và lỗi giữa ghi DB/gửi engine theo contract; không chỉ chạy background task trong request rồi coi đã có engine. Không giao lại Attempt chưa rõ kết quả; recovery đầy đủ thuộc [REL-001](../execution/002-recovery.md#rel-001).

### Bằng chứng và nghiệm thu RUN-002
- **Mã nguồn Server**:
  - `apps/server/src/agent_cf_server/infrastructure/runs/repository.py`:
    - `create_from_version`: Tạo `process_runs`, giải quyết root tasks (`queued`), non-root (`pending`), `run_events`, `audit_events`, `engine_outbox`, khóa khử trùng `receipts`.
    - `list_work`: Trả về danh sách TaskRun đủ điều kiện cho Runner trong cùng Workspace.
    - `claim_task_run`: Thực hiện claim nguyên tử (CAS), tăng `generation`, tạo `attempts`, cấp `execution_token` (lưu SHA-256 hash tại `execution_grants`), chống giao trùng (409 Conflict cho Runner đến sau), idempotency trả receipt cũ khi trùng key/hash.
    - `complete_attempt`: Đối soát token bí mật, cập nhật Attempt/TaskRun, giải quyết DAG dependency (mở khóa downstream tasks từ `pending` sang `queued`), tự động settle ProcessRun khi tất cả tasks kết thúc (tổng hợp output nếu thành công, ghi nhận error nếu thất bại).
    - `cancel_run`: Hủy an toàn, chuyển pending/queued sang cancelled, bảo toàn TaskRun đã hoàn tất.
  - `apps/server/src/agent_cf_server/api/runs.py`: API routes `/v1/runs`, `/v1/runners/{runner_id}/work`, `/v1/task-runs/{task_run_id}/claim`, `/v1/attempts/{attempt_id}/complete`, `/v1/runs/{run_id}/cancel`.
- **Mã nguồn Client**:
  - `apps/client/src/agent_cf_client/execution/task_worker.py`: `TaskExecutionWorker` polling việc từ server, claim độc quyền, lập nhật ký journal trước khi chạy, cách ly thư mục workspace, kích hoạt adapter và gửi báo cáo kết quả.
- **Kiểm thử tự động**:
  - `apps/server/tests/integration/runs/test_run_execution.py`:
    - `test_run_creation_idempotency_and_initial_queuing`: PASSED.
    - `test_work_polling_and_claim_cas_prevents_duplicate_assignment`: PASSED (kiểm thử 2 Runner cùng claim, 1 thành công 1 nhận 409).
    - `test_dag_progression_and_run_completion`: PASSED (Task 1 xong -> Task 2 mở khóa -> Run settle `succeeded`).
    - `test_run_cancellation_lifecycle`: PASSED (hủy run và dừng các task chưa chạy).

## RUN-003

- [x] **RUN-003 — API đọc lịch sử, log và artifact an toàn** — Xong | Feature
  - Phụ thuộc: [RUN-002](002-run-execution-history.md#run-002).
  - Nghiệm thu: đọc lại Run đã lưu, trạng thái/timestamp thực tế, log có giới hạn và output đúng Run; không lộ secret hoặc cho đọc đường dẫn tùy ý.

### Bằng chứng và nghiệm thu RUN-003
- **Mã nguồn**:
  - `apps/server/src/agent_cf_server/infrastructure/runs/repository.py`:
    - `list_runs`: Lọc theo `project_id`, `process_id`, `status` (queued/running/succeeded/failed/cancelled), phân trang cursor ổn định.
    - `get`: Đọc toàn diện ProcessRun, TaskRuns, Attempts và Artifacts.
    - `get_run_events`: Lấy chuỗi audit logs theo trình tự thời gian và số sequence.
    - `register_artifact`, `save_artifact_content`, `get_artifact`: Quản lý upload artifact có kiểm tra kích thước declared size và SHA-256 hash; tải về với kiểm tra path traversal an toàn, không mở đường dẫn tùy ý trên filesystem máy chủ.
  - `apps/server/src/agent_cf_server/api/runs.py`:
    - `GET /v1/runs`, `GET /v1/runs/{run_id}`, `GET /v1/runs/{run_id}/events`.
    - `POST /v1/attempts/{attempt_id}/artifacts`, `PUT /v1/artifacts/{artifact_id}/content`, `GET /v1/artifacts/{artifact_id}/content`.
- **Kiểm thử tự động**:
  - `apps/server/tests/integration/runs/test_run_execution.py::test_artifact_registration_upload_and_safe_download`: PASSED.
