# Providers, Models, Roles và General

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## SET-002

- [x] **SET-002 — Providers, Models, Roles và General** — Xong | Feature
  - Phụ thuộc: [DATA-001](../data/001-sqlite-persistence.md#data-001), [BASE-002](../base/002-application-bootstrap.md#base-002).
  - Nghiệm thu: cấu hình theo spec, secret xử lý phía tin cậy, Role không tự đồng nghĩa quyền thực thi; đổi mặc định không sửa version đã publish. Tách từng mục trước khi giao, không mở thêm Account/Workspace ngoài phạm vi hiện tại.
  - Bằng chứng 2026-11-16: Migration 004 (`004_settings_skills_agents.sql`), `SettingsRepository` (`apps/server/src/agent_cf_server/infrastructure/settings/repository.py`), API router `/v1/settings/` (providers, models, roles, general). Secret API Key được mask tự động (`****`) khi đọc, ràng buộc foreign key ngăn xóa provider khi model đang tham chiếu, General settings cấu hình default timeout/logs/timezone. Đã kiểm thử tự động tại `test_settings_skills_agents.py`.
