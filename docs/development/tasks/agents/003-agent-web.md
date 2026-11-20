# Giao diện Web quản lý Agent

> Last updated: 2026-11-17

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## AGN-004

- [x] **AGN-004 — Giao diện Web quản lý Agent (Agents View)** — Xong | Feature
  - Phụ thuộc: [AGN-003](002-agent-catalog.md#agn-003), [SET-002](../settings/002-general-configuration.md#set-002), [SKL-002](../skills/001-skill-catalog.md#skl-002).
  - Nghiệm thu: Giao diện Web hiển thị danh sách Agent, lọc trạng thái active/archived; form tạo/sửa Agent cho phép chọn Role, Model từ catalog Settings, Skills được gán và Allowed Tools từ catalog Skills; kiểm tra logic validation phía UI và hiển thị lỗi từ Server; bảng hiển thị số token tháng thực tế từ backend; không bịa số liệu ngân sách/chi phí.
  - Bằng chứng 2026-11-17: `apps/web/src/features/agents/`, API catalog thật, lọc/tìm kiếm, tạo/sửa và Archive/Restore/Delete có xác nhận. Token tháng theo giờ Việt Nam từ Overview, thiếu usage ghi rõ. Browser smoke tạo Agent với Skill mới từ UI; kiểm tra tám menu desktop/mobile và test tích hợp catalog. [Báo cáo](../../../reports/ui-completion-check.md).
  - Giới hạn: task này nghiệm thu giao diện catalog; quyền thực thi generic và snapshot worker còn theo RTM-008/RUN-008, không tự hoàn thành toàn bộ menu Agents.
