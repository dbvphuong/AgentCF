# Quản lý tiến trình và artifact từng lần chạy

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## CLI-002

- [x] **CLI-002 — Quản lý tiến trình và thư mục từng lần chạy** — Xong | Infrastructure
  - Phụ thuộc: [BASE-001](../base/001-foundation-design.md#base-001), [BASE-002](../base/002-application-bootstrap.md#base-002).
  - Nghiệm thu: thư mục Run/Attempt riêng, chặn đường dẫn thoát phạm vi và ghi đè output cũ; cấu hình timeout/hủy, dừng đúng cây tiến trình thử, không kill mọi Codex của máy. Test tiếng Việt, chủ đề trùng, lỗi spawn, timeout và chương trình con; không bypass quyền mặc định.
  - Bằng chứng 2026-11-16: `WorkspaceManager` (`apps/client/src/agent_cf_client/execution/workspace.py`) tạo thư mục cách ly `run_id/attempt_id/`, chặn mọi hành vi path traversal (`..` và symlink escape). `ProcessManager` (`apps/client/src/agent_cf_client/execution/process_manager.py`) chạy và giám sát tiến trình, hỗ trợ timeout và cancellation, dừng đúng cây tiến trình thử trên Windows qua `taskkill /F /T /PID`, xử lý hoàn hảo mã hóa tiếng Việt UTF-8 qua `PYTHONIOENCODING=utf-8` và `PYTHONUTF8=1`. Đã kiểm thử tự động tại `test_client_execution.py`.
