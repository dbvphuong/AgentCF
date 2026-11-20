# Thiết kế quyền thực thi và chống trùng tối thiểu

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

## REL-004

- [x] **REL-004 — Thiết kế quyền thực thi và chống trùng tối thiểu** — Xong | Design
  - Phụ thuộc: [BASE-001](../base/001-foundation-design.md#base-001), [PROC-001](../projects/processes/001-process-definition.md#proc-001).
  - Nghiệm thu: Chốt Runner/session/Attempt/generation/token/expiry, claim/renew CAS, journal trước spawn, receipt và kết quả muộn; có bảng tình huống duplicate/expire/revoke/timeout/cancel/reconnect. Unknown giữ reconciling, không tự giao lại; không nghiệm thu recovery đầy đủ.
  - Bằng chứng 2026-11-16: [Execution — quyền](../../../architecture/execution-model.md#quyền-nhận-việc-và-chống-chạy-trùng), [contract Client](../../../architecture/client-protocol.md), [ADR 0005](../../../architecture/decisions/0005-versioned-process-execution.md). [Review chéo và kết quả kiểm tra](../../../reports/foundation-design-review.md).
  - Kiểm tra đã chạy: `node openapi/check-contract.cjs` — OpenAPI hợp lệ, 51 schema biên dịch được, 20 ca schema và 5 ca graph đạt; đây là kiểm tra contract/tài liệu, không phải test ứng dụng. Kiểm tra liên kết/task tại báo cáo review.
  - Giới hạn: không scaffold, không tạo DB/migration, không chạy Temporal/Client/CLI/Skill, không hoàn tất menu hoặc mốc sử dụng. Chi tiết triển khai và kiểm thử tích hợp vẫn theo các task phụ thuộc.
