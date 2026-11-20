# Danh mục, snapshot và quản lý Skill/Tool

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## SKL-001

- [x] **SKL-001 — Danh mục và snapshot Skill cho form chạy/node** — Xong | Feature
  - Phụ thuộc: [BASE-001](../base/001-foundation-design.md#base-001), [PROC-001](../projects/processes/001-process-definition.md#proc-001), [API-001](../api/001-run-client-contract.md#api-001).
  - Nghiệm thu: cung cấp tên/identity, nội dung hoặc version/hash và input/output cần thiết; Server kiểm tra Skill được phép dùng. Trước mắt chỉ cho thực thi Skill đã tích hợp, ghi rõ trạng thái các Skill khác; giữ nguyên ba Skill mẫu nếu chưa được yêu cầu chỉnh sửa.
  - Bằng chứng 2026-11-16: `SkillRepository` và hàm `compute_skill_bundle_hash` / `compute_directory_bundle_hash`, dynamic loader `sync_skills_from_directory` quét và nạp động 3 Skill nghiệp vụ từ `tests/.agents/skills/` mà không hard-code. Version publish tính hash SHA-256 bất biến.

## SKL-002

- [x] **SKL-002 — Menu CRUD Skill/Tool và vòng đời catalog** — Xong | Feature
  - Phụ thuộc: [SKL-001](001-skill-catalog.md#skl-001), [DATA-001](../data/001-sqlite-persistence.md#data-001).
  - Nghiệm thu: danh mục theo spec, Skill dùng Tool đúng quyền, archive giữ lịch sử/tham chiếu; không coi có Tool trên UI là đã cấp quyền thực thi. Tách CRUD/version/quyền thành task nhỏ khi giao.
  - Bằng chứng 2026-11-16: Schema migration 004 tạo bảng `skills`, `skill_versions`, `tools`, `skill_version_tools`. Triggers SQLite bảo vệ version đã publish chống sửa/xóa; hỗ trợ Archive/Restore, ràng buộc foreign key chống xóa tool/skill đang được dùng; API endpoints `/v1/skills/` đầy đủ CRUD. Đã kiểm thử tự động tại `test_settings_skills_agents.py`.
