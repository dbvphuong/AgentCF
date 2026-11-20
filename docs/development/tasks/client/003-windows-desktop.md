# Tray và phiên đăng nhập Windows

Bằng chứng 2026-11-16 bên dưới là controller/trạng thái. Tray Windows thật, bộ cài và mở từ Web được kiểm chứng trong [CLI-004](004-desktop-onboarding.md).

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## CLI-003

- [x] **CLI-003 — Tray và khởi động cùng phiên Windows** — Xong | Feature
  - Phụ thuộc: [CLI-001](001-authenticated-connection.md#cli-001), [CLI-002](002-process-execution.md#cli-002); xác nhận thiết kế Client tương ứng.
  - Nghiệm thu: phần desktop tách khỏi execution, thể hiện trạng thái Client và shutdown có kiểm soát; kiểm chứng giới hạn khóa màn hình/đăng xuất theo tool.
  - Bằng chứng 2026-11-16: `DesktopController` (`apps/client/src/agent_cf_client/desktop/tray.py`) tách riêng giao diện/trạng thái desktop khỏi luồng execution, quản lý các trạng thái vòng đời (`connecting`, `idle`, `running`, `stopping`, `disabled`), kiểm soát shutdown an toàn (graceful shutdown qua `shutdown_event`), phát hiện trạng thái khóa màn hình Windows (`is_windows_session_locked` qua `OpenInputDesktop` API). Đã kiểm thử tự động tại `test_client_execution.py`.
