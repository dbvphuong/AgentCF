# Định nghĩa/version cho Process động

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../../README.md) · [Kế hoạch tổng](../../../implementation-plan.md)

## PROC-001

- [x] **PROC-001 — Định nghĩa/version cho Process động** — Xong | Design
  - Phụ thuộc: [BASE-001](../../base/001-foundation-design.md#base-001).
  - Nghiệm thu: Project sở hữu Process; graph DAG bất kỳ, identity/version, schema/mapping và snapshot Agent/runtime/model/Skill/Tool/Robot bất biến có nguồn chuẩn; publish nguyên tử và revision CAS. Skill 0–1–2 chỉ là fixture, không là loại Task hoặc graph hard-code.
  - Bằng chứng 2026-11-16: [Domain — Process động/snapshot](../../../../architecture/domain-model.md#định-nghĩa-process-động-và-snapshot), [ADR 0005](../../../../architecture/decisions/0005-versioned-process-execution.md). [Review chéo và kết quả kiểm tra](../../../../reports/foundation-design-review.md).
  - Kiểm tra đã chạy: `node openapi/check-contract.cjs` — OpenAPI hợp lệ, 51 schema biên dịch được, 20 ca schema và 5 ca graph đạt; đây là kiểm tra contract/tài liệu, không phải test ứng dụng. Kiểm tra liên kết/task tại báo cáo review.
  - Giới hạn: không scaffold, không tạo DB/migration, không chạy Temporal/Client/CLI/Skill, không hoàn tất menu hoặc mốc sử dụng. Chi tiết triển khai và kiểm thử tích hợp vẫn theo các task phụ thuộc.
