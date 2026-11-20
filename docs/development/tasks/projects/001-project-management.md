# Quản lý Project và liên kết Process/Run

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## PROJ-001

- [x] **PROJ-001 — Quản lý Project và liên kết Process/Run** — Xong (local UI/API) | Feature
  - Phụ thuộc: [DATA-001](../data/001-sqlite-persistence.md#data-001), [RUN-006](../runs/003-skill0-web.md#run-006).
  - Nghiệm thu: CRUD/archive/restore giữ lịch sử, Process thuộc Project, tab Runs dùng lại module Runs và lọc đúng Project. Phân biệt dữ liệu Project tối thiểu ở [PROC-001](processes/001-process-definition.md#proc-001) với menu CRUD hoàn chỉnh.
  - Bằng chứng 2026-11-17: `api/projects.py`, `infrastructure/projects/management.py`, migration 010 và `features/projects/`. Project CRUD với PM/Workspace, Archive/Restore chặn Run chưa terminal, tắt lịch và giữ lịch sử; tab Runs gọi cùng module và query Project phía Server. Test persistence/reconnect, xóa draft chưa dùng, bảo toàn published và lịch sử tại `tests/integration/projects/test_project_web.py`; browser smoke tạo Project từ UI. [Báo cáo](../../../reports/ui-completion-check.md).
  - Giới hạn: published được Archive kể cả chưa có Run, tuân thủ trigger bất biến hiện có; form xác nhận nêu rõ. Remote auth/idempotency tạo mới editor chưa được nghiệm thu; không tích toàn bộ menu Projects thay cho PROC-003.
