# Hợp đồng ProcessVersion, Run và giao việc Client

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

## API-001

- [x] **API-001 — Hợp đồng ProcessVersion, Run và giao việc Client** — Xong | Design
  - Phụ thuộc: [BASE-001](../base/001-foundation-design.md#base-001), [PROC-001](../projects/processes/001-process-definition.md#proc-001), [RUN-001](../runs/001-skill0-run-design.md#run-001), [REL-004](../execution/001-execution-permissions.md#rel-004).
  - Nghiệm thu: OpenAPI và contract Client xác định definition/config, input/output/error/artifact, Run/TaskRun/Attempt, quyền/session/generation, khử trùng, nội bộ worker và kết quả muộn. Validation ở phía tin cậy; không shell/path tùy ý từ Web; có ví dụ schema hợp lệ/bị từ chối. Chưa sinh client code hoặc handler.
  - Bằng chứng 2026-11-16: [OpenAPI](../../../../openapi/openapi.yaml), [contract Client](../../../architecture/client-protocol.md), [ví dụ thiết kế](../../../../openapi/examples/foundation-cases.json). [Review chéo và kết quả kiểm tra](../../../reports/foundation-design-review.md).
  - Kiểm tra đã chạy: `node openapi/check-contract.cjs` — OpenAPI hợp lệ, 51 schema biên dịch được, 20 ca schema và 5 ca graph đạt; đây là kiểm tra contract/tài liệu, không phải test ứng dụng. Kiểm tra liên kết/task tại báo cáo review.
  - Giới hạn: không scaffold, không tạo DB/migration, không chạy Temporal/Client/CLI/Skill, không hoàn tất menu hoặc mốc sử dụng. Chi tiết triển khai và kiểm thử tích hợp vẫn theo các task phụ thuộc.
