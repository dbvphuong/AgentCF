# SQLite và migration

[Kế hoạch tổng](../../implementation-plan.md) · [Quy ước task](../README.md)

Vị trí: Server infrastructure và migrations. Spec: [ADR SQLite — Accepted](../../../architecture/decisions/0004-sqlite-business-database.md), [domain model](../../../architecture/domain-model.md).

Vị trí code/test và quy tắc phụ thuộc module: [project structure](../../project-structure.md#tra-cứu-menu-và-tính-năng).

## Đầu việc

| Đầu việc | Task con |
|---|---|
| [SQLite và lưu dữ liệu luồng đầu tiên](001-sqlite-persistence.md) | [DATA-000](001-sqlite-persistence.md#data-000), [DATA-001](001-sqlite-persistence.md#data-001) |
| [Backup, restore và hướng chuyển DB](002-backup-restore.md) | [DATA-002](002-backup-restore.md#data-002) |

Trạng thái, nghiệm thu và bằng chứng nằm tại từng file đầu việc. Thêm tính năng/sửa lỗi tại đây theo [quy ước task](../README.md); chỉ đọc module khác khi có phụ thuộc.
