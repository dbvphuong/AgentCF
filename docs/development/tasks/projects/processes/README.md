# Process trong menu Projects

[Kế hoạch tổng](../../../implementation-plan.md) · [Quy ước task](../../README.md)

Vị trí: `web/src/features/projects/processes/`, các lớp Server `processes/`. Spec: [Process và version](../../../../product/requirements.md#process-và-version), [cấu hình node](../../../../product/requirements.md#cấu-hình-node-dùng-runtime-local).

Vị trí code/test và quy tắc phụ thuộc module: [project structure](../../../project-structure.md#tra-cứu-menu-và-tính-năng).

## Đầu việc

| Đầu việc | Task con |
|---|---|
| [Định nghĩa và version Process động](001-process-definition.md) | [PROC-001](001-process-definition.md#proc-001) |
| [Editor, validate và publish Process](002-process-editor.md) | [PROC-002](002-process-editor.md#proc-002), [PROC-003](002-process-editor.md#proc-003) |
| [Schedule và lựa chọn PC](003-scheduling.md) | [PROC-004](003-scheduling.md#proc-004) |
| [Form node, Nhiệm vụ và Model theo Runtime](004-node-task-form.md) | [PROC-005](004-node-task-form.md#proc-005) |
| [Thư mục làm việc cấu hình ở Project](005-project-working-directory.md) | [PROC-006](005-project-working-directory.md#proc-006) |
| [Giữ thư mục node cũ khi chuyển sang Project](006-legacy-project-root.md) | [PROC-007](006-legacy-project-root.md#proc-007) |

Xem [module Projects](../README.md) khi thay đổi quan hệ Project, Team hoặc Targets.

Trạng thái, nghiệm thu và bằng chứng nằm tại từng file đầu việc. Thêm tính năng/sửa lỗi tại đây theo [quy ước task](../../README.md); chỉ đọc module khác khi có phụ thuộc.
