# PM, Team và Targets

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## PROJ-002

Team chuyển sang view tự tổng hợp, không quản lý membership thủ công tại [PROJ-009](009-derived-team.md). Bằng chứng bên dưới mô tả triển khai ban đầu.

- [x] **PROJ-002 — PM, Team và Targets** — Xong (local UI/API) | Feature
  - Phụ thuộc: [PROJ-001](001-project-management.md#proj-001), [AGN-003](../agents/002-agent-catalog.md#agn-003).
  - Nghiệm thu: Agent tham gia Project đúng quan hệ, PM không suy từ tên Role; Target và số kết quả được duyệt theo spec, không lấy Run succeeded tự tăng kết quả nghiệm thu. Tách Team/Targets khi giao.
  - Bằng chứng 2026-11-17: bảng `project_team`, PM ID riêng, form Manage team; Server giữ PM và Agent đã được gán trong Process. Targets có kỳ, ngày, tiêu chí, số mục tiêu và số kết quả được duyệt; không tự tăng theo Run. Overview ưu tiên target tháng/tuần còn hiệu lực. Regression persistence, sai ngày, giữ PM; browser smoke tạo Target qua Web. [Báo cáo](../../../reports/ui-completion-check.md).
