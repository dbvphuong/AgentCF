# HTTP và hợp đồng giao việc Client

[Kế hoạch tổng](../../implementation-plan.md) · [Quy ước task](../README.md)

Vị trí: `openapi/`, các module `api/` của Server; giao thức Client là hợp đồng riêng. Spec: [execution model](../../../architecture/execution-model.md), [runtime node](../../../product/requirements.md#cấu-hình-node-dùng-runtime-local).

Vị trí code/test và quy tắc phụ thuộc module: [project structure](../../project-structure.md#tra-cứu-menu-và-tính-năng).

## Đầu việc

| Đầu việc | Task con |
|---|---|
| [Hợp đồng Run và giao việc Client](001-run-client-contract.md) | [API-001](001-run-client-contract.md#api-001) |

Trạng thái, nghiệm thu và bằng chứng nằm tại từng file đầu việc. Thêm tính năng/sửa lỗi tại đây theo [quy ước task](../README.md); chỉ đọc module khác khi có phụ thuộc.
