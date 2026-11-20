# Settings và model runtime

[Kế hoạch tổng](../../implementation-plan.md) · [Quy ước task](../README.md)

Vị trí: `features/settings/`, các lớp Server `settings/`; adapter Client xác thực khả năng runtime, không phụ thuộc UI. Spec: [Settings](../../../product/requirements.md#settings-và-cấu-hình-model), [node runtime](../../../product/requirements.md#cấu-hình-node-dùng-runtime-local).

Vị trí code/test và quy tắc phụ thuộc module: [project structure](../../project-structure.md#tra-cứu-menu-và-tính-năng).

## Đầu việc

| Đầu việc | Task con |
|---|---|
| [Secret store provider](004-provider-secret-store.md) | [SET-004](004-provider-secret-store.md#set-004) |
| [Runtime, model và khả dụng trên máy](001-runtime-models.md) | [SET-001](001-runtime-models.md#set-001) |
| [Providers, Models, Roles và General (Backend)](002-general-configuration.md) | [SET-002](002-general-configuration.md#set-002) |
| [Giao diện Web cài đặt hệ thống](003-settings-web.md) | [SET-003](003-settings-web.md#set-003) |
| [Agent điều phối và danh mục model công cụ AI trên PC](005-ai-tool-models.md) | [SET-005](005-ai-tool-models.md#set-005) |

Trạng thái, nghiệm thu và bằng chứng nằm tại từng file đầu việc. Thêm tính năng/sửa lỗi tại đây theo [quy ước task](../README.md); chỉ đọc module khác khi có phụ thuộc.
