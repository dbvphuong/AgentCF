# Connection, execution và desktop của CF Client

[Kế hoạch tổng](../../implementation-plan.md) · [Quy ước task](../README.md)

Vị trí: `client/.../connection/`, `execution/`, `desktop/`. Spec: [Runner Client](../../../product/requirements.md#runner-client), [execution](../../../architecture/execution-model.md).

Vị trí code/test và quy tắc phụ thuộc module: [project structure](../../project-structure.md#tra-cứu-menu-và-tính-năng).

## Đầu việc

| Đầu việc | Task con |
|---|---|
| [Kết nối và giao việc có xác thực](001-authenticated-connection.md) | [CLI-001](001-authenticated-connection.md#cli-001) |
| [Quản lý tiến trình và artifact từng lần chạy](002-process-execution.md) | [CLI-002](002-process-execution.md#cli-002) |
| [Tray và phiên đăng nhập Windows](003-windows-desktop.md) | [CLI-003](003-windows-desktop.md#cli-003) |
| [CF Client desktop và Connect PC có hướng dẫn](004-desktop-onboarding.md) | [CLI-004](004-desktop-onboarding.md#cli-004) |

Trạng thái, nghiệm thu và bằng chứng nằm tại từng file đầu việc. Thêm tính năng/sửa lỗi tại đây theo [quy ước task](../README.md); chỉ đọc module khác khi có phụ thuộc.
