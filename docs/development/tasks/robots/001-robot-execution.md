# Robot catalog, version và node thực thi

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## ROB-001

- [x] **ROB-001 — Robot catalog, version và node thực thi** — Xong | Feature
  - Phụ thuộc: [PROC-003](../projects/processes/002-process-editor.md#proc-003), [PC-001](../runners/001-runner-registration.md#pc-001), [AGN-003](../agents/002-agent-catalog.md#agn-003).
  - Nghiệm thu: Hoàn thành toàn diện các phần ROB-001-1 đến ROB-001-5: version chương trình bất biến, metadata/catalog tách gán Agent/PC ở node, thực thi trên PC runner, thống kê theo version từ dữ liệu thực tế, giao diện Web quản lý đầy đủ và 100% test tự động đạt.

### ROB-001-1: Schema SQLite, Trigger bất biến và Repository Robot
- [x] **ROB-001-1 — SQLite migration 006 và RobotRepository** — Xong | Feature
  - Vị trí code: `apps/server/migrations/006_robots.sql`, `apps/server/src/agent_cf_server/infrastructure/robots/repository.py`.
  - Phụ thuộc: DATA-001, SKL-001.
  - Nghiệm thu: Đã tạo bảng `robots`, `robot_versions` kèm trigger `immutable_published_robot_version_*` chặn sửa/xóa version đã publish; unique index `one_draft_per_robot`; CRUD robot và draft/publish version; bảo vệ Delete đối với robot đã có liên kết/lịch sử/published version (chuyển sang Archive/Restore).

### ROB-001-2: REST API Robot Catalog và Thống kê theo Version từ dữ liệu thật
- [x] **ROB-001-2 — REST API Robots và Thống kê chất lượng** — Xong | Feature
  - Vị trí code: `apps/server/src/agent_cf_server/api/robots.py`, `openapi/openapi.yaml`.
  - Phụ thuộc: ROB-001-1, RUN-002, RUN-003.
  - Nghiệm thu: Endpoint `/v1/robots`, `/v1/robots/{id}`, `/v1/robots/{id}/versions`, `/v1/robots/{id}/versions/{version_id}/publish`, `/v1/robots/{id}/archive`, `/v1/robots/{id}/restore`, `/v1/robots/{id}/statistics`. Thống kê success rate tính từ `task_runs`/`attempts` thật: `succeeded / (succeeded + failed)`, timeout tính là lỗi, cancelled tách riêng, version mới chưa chạy trả `null` (không hiển thị 0%).

### ROB-001-3: Thực thi node Robot trên PC Runner
- [x] **ROB-001-3 — Thực thi node Robot và gán PC tại node** — Xong | Feature
  - Vị trí code: `apps/client/src/agent_cf_client/execution/task_worker.py`, `apps/server/src/agent_cf_server/infrastructure/runs/repository.py`.
  - Phụ thuộc: ROB-001-2, CLI-002, PC-001.
  - Nghiệm thu: Task loại `robot` trong DAG bắt buộc gán `runner_id` tại node (catalog không gán PC/Agent); `list_work` và `claim_task_run` kiểm tra quyền chỉ Runner được gán mới claim được task (runner khác bị 409 Conflict); worker thực thi chương trình robot độc lập trong workspace cô lập, chuyển giao input/output schema, ghi journal, thu thập và upload artifact an toàn, hoàn tất attempt.

### ROB-001-4: Giao diện Web quản lý Robots và Thống kê Version
- [x] **ROB-001-4 — Web UI Robots Catalog & Version Details** — Xong | Feature
  - Vị trí code: `apps/web/src/features/robots/`, `apps/web/src/app/App.tsx`, `apps/web/src/app/styles.css`.
  - Phụ thuộc: ROB-001-2.
  - Nghiệm thu: Tab Robots trên navigation Web; danh sách Robot hiển thị Active Version, badge trạng thái (active/archived), success rate thật (hoặc "Chưa có dữ liệu"); form tạo/sửa Robot; form tạo Draft version và nút Publish; xem chi tiết Robot và bảng thống kê từng version; URL hash routing (`#robots`, `#robots/new`, `#robots/:id`, `#robots/:id/new-version`, `#robots/:id/edit`).

### ROB-001-5: Tích hợp và Kiểm thử Toàn diện
- [x] **ROB-001-5 — Kiểm thử tích hợp Robot Catalog, Version và Execution** — Xong | Verification
  - Vị trí code: `apps/server/tests/integration/robots/test_robot_lifecycle.py`, `apps/web/tests/app/robots.test.mjs`.
  - Phụ thuộc: ROB-001-1 đến ROB-001-4.
  - Bằng chứng nghiệm thu:
    - `apps/server/tests/integration/robots/test_robot_lifecycle.py`: 4 passed (test CRUD, triggers immutability, delete protection, pinned runner check, worker execution, artifact upload và statistics calculation).
    - Toàn bộ pytest: 112 passed, 1 skipped.
    - Web test: 11 passed (`npm.cmd --prefix apps/web test`).
    - Web build: 0 errors (`npm.cmd --prefix apps/web run build`).
    - OpenAPI: 54 schemas compiled, 28 operations passed (`node openapi/check-contract.cjs`).
