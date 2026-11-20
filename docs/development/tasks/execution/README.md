# Độ tin cậy, audit và can thiệp

[Kế hoạch tổng](../../implementation-plan.md) · [Quy ước task](../README.md)

Vị trí: module sở hữu execution/persistence; không tạo một lớp business logic gom chung tên `reliability`. Spec: [execution](../../../architecture/execution-model.md), [yêu cầu chất lượng](../../../product/requirements.md#yêu-cầu-chất-lượng), [audit](../../../product/requirements.md#audit-và-lịch-sử).

Vị trí code/test và quy tắc phụ thuộc module: [project structure](../../project-structure.md#tra-cứu-menu-và-tính-năng).

## Đầu việc

| Đầu việc | Task con |
|---|---|
| [Quyền thực thi và chống trùng tối thiểu](001-execution-permissions.md) | [REL-004](001-execution-permissions.md#rel-004) |
| [Đối soát khi Client/Server gián đoạn](002-recovery.md) | [REL-001](002-recovery.md#rel-001) |
| [Audit và kiểm thử quyền xuyên luồng](003-audit.md) | [REL-002](003-audit.md#rel-002) |
| [Chờ người dùng và Continue an toàn](004-human-continue.md) | [REL-003](004-human-continue.md#rel-003) |

Đây là nhóm tài liệu về trách nhiệm xuyên Server/Client, không phải module code mới. Thực hiện thay đổi trong module sở hữu theo [project structure](../../project-structure.md).

Trạng thái, nghiệm thu và bằng chứng nằm tại từng file đầu việc. Thêm tính năng/sửa lỗi tại đây theo [quy ước task](../README.md); chỉ đọc module khác khi có phụ thuộc.
