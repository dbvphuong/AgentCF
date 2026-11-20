# Thiết kế ProcessRun, TaskRun và Attempt dùng chung

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

## RUN-001

- [x] **RUN-001 — Thiết kế ProcessRun, TaskRun và Attempt dùng chung** — Xong | Design
  - Phụ thuộc: [BASE-001](../base/001-foundation-design.md#base-001), [PROC-001](../projects/processes/001-process-definition.md#proc-001), [REL-004](../execution/001-execution-permissions.md#rel-004).
  - Nghiệm thu: Run input theo schema của ProcessVersion, trạng thái Run/TaskRun/Attempt, event/error/artifact, điều kiện thành công, timeout/hủy/unknown có nguồn chuẩn; không suy thành công từ lời model. Fixture chủ đề chỉ kiểm thử một định nghĩa trong hệ thống động.
  - Bằng chứng 2026-11-16: [Execution](../../../architecture/execution-model.md), [domain](../../../architecture/domain-model.md), [OpenAPI](../../../../openapi/openapi.yaml). [Review chéo và kết quả kiểm tra](../../../reports/foundation-design-review.md).
  - Kiểm tra đã chạy: `node openapi/check-contract.cjs` — OpenAPI hợp lệ, 51 schema biên dịch được, 20 ca schema và 5 ca graph đạt; đây là kiểm tra contract/tài liệu, không phải test ứng dụng. Kiểm tra liên kết/task tại báo cáo review.
  - Giới hạn: không scaffold, không tạo DB/migration, không chạy Temporal/Client/CLI/Skill, không hoàn tất menu hoặc mốc sử dụng. Chi tiết triển khai và kiểm thử tích hợp vẫn theo các task phụ thuộc.
