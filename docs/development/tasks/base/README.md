# Môi trường và khung ứng dụng

[Kế hoạch tổng](../../implementation-plan.md) · [Quy ước task](../README.md)

Spec: [setup](../../setup.md), [ADR stack](../../../architecture/decisions/0001-application-stack.md), [ADR Client](../../../architecture/decisions/0002-cf-client-windows.md), [ADR engine](../../../architecture/decisions/0003-process-engine-temporal.md).

Vị trí code/test và quy tắc phụ thuộc module: [project structure](../../project-structure.md#tra-cứu-menu-và-tính-năng).

## Đầu việc

| Đầu việc | Task con |
|---|---|
| [Môi trường local](000-local-environment.md) | [BASE-000](000-local-environment.md#base-000) |
| [Thiết kế nền cho hệ thống quản lý tổng và Process động](001-foundation-design.md) | [BASE-001](001-foundation-design.md#base-001) |
| [Khung ứng dụng và hạ tầng điều phối](002-application-bootstrap.md) | [BASE-002](002-application-bootstrap.md#base-002), [BASE-003](002-application-bootstrap.md#base-003) |
| [Layout quản trị và responsive](003-web-navigation.md) | [BASE-004](003-web-navigation.md#base-004) |
| [Launcher local trên Windows](004-local-launcher.md) | [BASE-005](004-local-launcher.md#base-005) |
| [Giảm ID kỹ thuật trên giao diện](005-visible-identifiers.md) | [BASE-006](005-visible-identifiers.md#base-006) |
| [Bỏ Archive/Restore ngoài Project](006-project-only-lifecycle-controls.md) | [BASE-007](006-project-only-lifecycle-controls.md#base-007) |
| [Giảm lag nhập liệu/cuộn hộp thoại](007-input-scroll-responsiveness.md) | [BASE-008](007-input-scroll-responsiveness.md#base-008) |
| [Lưu và dùng ngay](008-save-and-run.md) | [BASE-009](008-save-and-run.md#base-009) |
| [Nhận diện và tương tác sidebar](009-sidebar-identity.md) | [BASE-010](009-sidebar-identity.md#base-010) |
| [Thông báo khi bị chặn xóa](010-deletion-feedback.md) | [BASE-011](010-deletion-feedback.md#base-011) |

Trạng thái, nghiệm thu và bằng chứng nằm tại từng file đầu việc. Thêm tính năng/sửa lỗi tại đây theo [quy ước task](../README.md); chỉ đọc module khác khi có phụ thuộc.
