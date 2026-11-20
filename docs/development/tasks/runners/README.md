# Menu PC và Runner

[Kế hoạch tổng](../../implementation-plan.md) · [Quy ước task](../README.md)

Vị trí: `features/runners/`, các lớp Server `runners/`; không dùng thư mục `pcs/` trái glossary. Spec: [quản lý PC](../../../product/requirements.md#quản-lý-pc), [Runner Client](../../../product/requirements.md#runner-client).

Vị trí code/test và quy tắc phụ thuộc module: [project structure](../../project-structure.md#tra-cứu-menu-và-tính-năng).

## Đầu việc

| Đầu việc | Task con |
|---|---|
| [Đăng ký, heartbeat và trạng thái PC (Backend)](001-runner-registration.md) | [PC-001](001-runner-registration.md#pc-001) |
| [Giao diện Web quản lý danh sách PC và ghép nối](002-runner-web.md) | [PC-002](002-runner-web.md#pc-002) |
| [Sửa và xóa kết nối PC](003-edit-remove.md) | [PC-003](003-edit-remove.md#pc-003) |
| [Định danh máy, kết nối lại và CPU/RAM](004-device-reconnect-metrics.md) | [PC-004](004-device-reconnect-metrics.md#pc-004) |
| [Connect PC mở/cài CF Client và theo dõi heartbeat](../client/004-desktop-onboarding.md) | [CLI-004](../client/004-desktop-onboarding.md#cli-004) |

Trạng thái, nghiệm thu và bằng chứng nằm tại từng file đầu việc. Thêm tính năng/sửa lỗi tại đây theo [quy ước task](../README.md); chỉ đọc module khác khi có phụ thuộc.
