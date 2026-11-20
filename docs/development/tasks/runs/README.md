# Chạy, Logs, artifact và lịch sử

[Kế hoạch tổng](../../implementation-plan.md) · [Quy ước task](../README.md)

Vị trí: `web/src/features/runs/`, các lớp Server `runs/`. Spec: [khởi chạy/theo dõi](../../../product/requirements.md#khởi-chạy-và-theo-dõi), [execution](../../../architecture/execution-model.md), [Runs và Logs](../../../product/requirements.md#runs-và-logs).

Vị trí code/test và quy tắc phụ thuộc module: [project structure](../../project-structure.md#tra-cứu-menu-và-tính-năng).

## Đầu việc

| Đầu việc | Task con |
|---|---|
| [Thiết kế lần chạy dùng chung](001-skill0-run-design.md) | [RUN-001](001-skill0-run-design.md#run-001) |
| [Điều phối và API lịch sử chạy](002-run-execution-history.md) | [RUN-002](002-run-execution-history.md#run-002), [RUN-003](002-run-execution-history.md#run-003) |
| [Chạy Skill 0 và xem kết quả qua Web](003-skill0-web.md) | [RUN-004](003-skill0-web.md#run-004), [RUN-005](003-skill0-web.md#run-005), [RUN-006](003-skill0-web.md#run-006) |
| [Luồng Skill 0 → 1 → 2](004-skill-chain.md) | [RUN-007](004-skill-chain.md#run-007) |
| [Input mapping tại runtime](005-runtime-input-mapping.md) | [RUN-008](005-runtime-input-mapping.md#run-008) |
| [Form tổng quát và lọc Runs](006-generic-web-form.md) | [RUN-009](006-generic-web-form.md#run-009) |
| [Chạy theo thư mục chủ đề có sẵn](007-topic-directory-launch.md) | [RUN-010](007-topic-directory-launch.md#run-010) |

Trạng thái, nghiệm thu và bằng chứng nằm tại từng file đầu việc. Thêm tính năng/sửa lỗi tại đây theo [quy ước task](../README.md); chỉ đọc module khác khi có phụ thuộc.
