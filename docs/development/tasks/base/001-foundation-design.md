# Thiết kế nền cho hệ thống quản lý tổng và Process động

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

## BASE-001

- [x] **BASE-001 — Thiết kế nền cho hệ thống quản lý tổng và Process động** — Xong | Design
  - Phụ thuộc: [BASE-000](000-local-environment.md#base-000), [DATA-000](../data/001-sqlite-persistence.md#data-000).
  - Nghiệm thu: ADR 0001–0003 hoàn thiện thiết kế stack/local topology, worker/relay/Client và persistence Temporal riêng; ADR 0005 chốt nguồn trạng thái, inbox/outbox và giao thức thực thi. Không đóng khung engine theo Skill 0; chưa triển khai ứng dụng.
  - Bằng chứng 2026-11-16: [ADR 0001](../../../architecture/decisions/0001-application-stack.md), [ADR 0002](../../../architecture/decisions/0002-cf-client-windows.md), [ADR 0003](../../../architecture/decisions/0003-process-engine-temporal.md), [ADR 0005](../../../architecture/decisions/0005-versioned-process-execution.md), [overview](../../../architecture/overview.md). [Review chéo và kết quả kiểm tra](../../../reports/foundation-design-review.md).
  - Kiểm tra đã chạy: `node openapi/check-contract.cjs` — OpenAPI hợp lệ, 51 schema biên dịch được, 20 ca schema và 5 ca graph đạt; đây là kiểm tra contract/tài liệu, không phải test ứng dụng. Kiểm tra liên kết/task tại báo cáo review.
  - Giới hạn: không scaffold, không tạo DB/migration, không chạy Temporal/Client/CLI/Skill, không hoàn tất menu hoặc mốc sử dụng. Chi tiết triển khai và kiểm thử tích hợp vẫn theo các task phụ thuộc.
