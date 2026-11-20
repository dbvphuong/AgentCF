# Skills và Tools

[Kế hoạch tổng](../../implementation-plan.md) · [Quy ước task](../README.md)

Vị trí: `features/skills/`, `features/skills/tools/`, các lớp Server `skills/`. Spec: [catalog Agent/Skill/Tool](../../../product/requirements.md#quản-lý-agents-skills-và-tools-qua-giao-diện), glossary.

Vị trí code/test và quy tắc phụ thuộc module: [project structure](../../project-structure.md#tra-cứu-menu-và-tính-năng).

## Đầu việc

| Đầu việc | Task con |
|---|---|
| [Danh mục, snapshot và quản lý Skill/Tool (Backend)](001-skill-catalog.md) | [SKL-001](001-skill-catalog.md#skl-001), [SKL-002](001-skill-catalog.md#skl-002) |
| [Giao diện Web quản lý Skills và Tools](002-skills-web.md) | [SKL-003](002-skills-web.md#skl-003) |
| [Skill theo nhiều Project hoặc Global](003-project-scope.md) | [SKL-004](003-project-scope.md#skl-004) |
| [File Markdown chính trong form Thêm/Sửa Skill](004-main-markdown-file.md) | [SKL-005](004-main-markdown-file.md#skl-005) |
| [Cột Version trong bảng Skills](005-version-column.md) | [SKL-006](005-version-column.md#skl-006) |

Trạng thái, nghiệm thu và bằng chứng nằm tại từng file đầu việc. Thêm tính năng/sửa lỗi tại đây theo [quy ước task](../README.md); chỉ đọc module khác khi có phụ thuộc.

Quy tắc xóa Skill khi không còn Process sử dụng và xóa version/membership thuộc task liên module [PROJ-007](../projects/007-permanent-deletion.md).
