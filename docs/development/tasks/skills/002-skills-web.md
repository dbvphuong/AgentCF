# Giao diện Web quản lý Skills và Tools

> Last updated: 2026-11-17

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## SKL-003

- [x] **SKL-003 — Giao diện Web quản lý Skills và Tools (Skills View)** — Xong | Feature
  - Phụ thuộc: [SKL-002](001-skill-catalog.md#skl-002).
  - Nghiệm thu: Giao diện Web gồm 2 tab: Skills và Tools; xem danh sách Skill, lịch sử version/snapshot bất biến; form tạo/sửa draft version cho Skill và publish version; tab Tools quản lý danh mục tool nội bộ (tên, mô tả, configuration schema) và các Agent được phép dùng; xác nhận trước khi Archive/Delete; ngăn xóa tool đang được Skill gán.
  - Bằng chứng 2026-11-17: `features/skills/Skills.tsx`, endpoint PATCH draft Skill (published từ chối 409), danh sách Tools kèm Agent được phép; CRUD/archive/restore dùng API hiện có, lỗi tham chiếu trả từ Server. Browser smoke tạo/publish Skill mới qua UI; regression kiểm tra chỉ sửa draft, snapshot đã publish bất biến. [Báo cáo và lệnh](../../../reports/ui-completion-check.md).
  - Giới hạn: UI catalog và version không chứng minh worker đã thực thi instruction/bundle tổng quát; xem RTM-008.
