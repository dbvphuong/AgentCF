# Agents và Agent thay người duyệt

[Kế hoạch tổng](../../implementation-plan.md) · [Quy ước task](../README.md)

Vị trí: `features/agents/`, các lớp Server `agents/`; logic vòng chạy phối hợp qua use case công khai của `runs/`. Spec: [Agent/tool](../../../product/requirements.md#agent-và-tool), [runtime node](../../../product/requirements.md#cấu-hình-node-dùng-runtime-local).

Vị trí code/test và quy tắc phụ thuộc module: [project structure](../../project-structure.md#tra-cứu-menu-và-tính-năng).

## Đầu việc

| Đầu việc | Task con |
|---|---|
| [Agent giao việc, duyệt và yêu cầu sửa](001-agent-review.md) | [AGN-001](001-agent-review.md#agn-001), [AGN-002](001-agent-review.md#agn-002) |
| [Menu quản lý Agent (Backend)](002-agent-catalog.md) | [AGN-003](002-agent-catalog.md#agn-003) |
| [Giao diện Web quản lý Agent](003-agent-web.md) | [AGN-004](003-agent-web.md#agn-004) |
| [Bỏ gán cứng Skill cho Agent và hiển thị Skill đang dùng](004-derived-agent-skills.md) | [AGN-005](004-derived-agent-skills.md#agn-005) |

Trạng thái, nghiệm thu và bằng chứng nằm tại từng file đầu việc. Thêm tính năng/sửa lỗi tại đây theo [quy ước task](../README.md); chỉ đọc module khác khi có phụ thuộc.

Quy tắc xóa Agent khi không còn Process sử dụng, dọn snapshot/Team và bỏ gán PM thuộc task liên module [PROJ-007](../projects/007-permanent-deletion.md).
