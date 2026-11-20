# Projects, Team và Targets

[Kế hoạch tổng](../../implementation-plan.md) · [Quy ước task](../README.md)

Vị trí: `features/projects/`, `projects/team/`, `projects/targets/`, các lớp Server `projects/`. Spec: [Project](../../../product/requirements.md#project), [Team/Targets](../../../product/requirements.md#projects-team-và-targets).

Vị trí code/test và quy tắc phụ thuộc module: [project structure](../../project-structure.md#tra-cứu-menu-và-tính-năng).

## Đầu việc

| Đầu việc | Task con |
|---|---|
| [Quản lý Project và liên kết Process/Run](001-project-management.md) | [PROJ-001](001-project-management.md#proj-001) |
| [PM, Team và Targets](002-team-targets.md) | [PROJ-002](002-team-targets.md#proj-002) |
| [Bảng Projects, menu và nhân bản](003-project-table-actions.md) | [PROJ-003](003-project-table-actions.md#proj-003) |
| [Project test Skill 0 bằng Codex CLI](004-skill0-test-project.md) | [PROJ-004](004-skill0-test-project.md#proj-004) |
| [Bộ lọc Tất cả và xóa Project có Skill liên kết](005-filter-delete.md) | [PROJ-005](005-filter-delete.md#proj-005) |
| [Thông báo kết quả thao tác Project](006-action-feedback.md) | [PROJ-006](006-action-feedback.md#proj-006) |
| [Xóa vĩnh viễn Project và lịch sử](007-permanent-deletion.md) | [PROJ-007](007-permanent-deletion.md#proj-007) |
| [Quay lại Projects trên dòng mô tả/PM](008-back-navigation.md) | [PROJ-008](008-back-navigation.md#proj-008) |
| [Team tự tổng hợp, chỉ hiển thị](009-derived-team.md) | [PROJ-009](009-derived-team.md#proj-009) |

Process là phần con trong Project: xem [định nghĩa, editor và schedule](processes/README.md).

Root làm việc của Project và default root/PC khi publish node nằm trong luồng liên module [RUN-010](../runs/007-topic-directory-launch.md).

Trạng thái, nghiệm thu và bằng chứng nằm tại từng file đầu việc. Thêm tính năng/sửa lỗi tại đây theo [quy ước task](../README.md); chỉ đọc module khác khi có phụ thuộc.
