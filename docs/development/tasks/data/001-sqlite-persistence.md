# SQLite và lưu dữ liệu luồng đầu tiên

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## DATA-000

- [x] **DATA-000 — Chốt SQLite cho DB nghiệp vụ local** — Xong | Design
  - Phụ thuộc: Không. Bằng chứng: ADR 0004 đã Accepted theo quyết định chủ dự án.
  - Giới hạn: chưa có file DB ứng dụng, schema, migration, ORM hoặc persistence Temporal.

## DATA-001

- [x] **DATA-001 — Schema và migration tối thiểu cho luồng đầu tiên** — Xong | Infrastructure
  - Phụ thuộc: [BASE-001](../base/001-foundation-design.md#base-001), [PROC-001](../projects/processes/001-process-definition.md#proc-001), [RUN-001](../runs/001-skill0-run-design.md#run-001).
  - Nghiệm thu: tạo DB mới và nâng version schema được; lưu được định nghĩa/version, cấu hình thực thi đã cố định, Run/TaskRun và tham chiếu artifact cần thiết cho luồng, cùng execution grant/generation, session, receipt/inbox/outbox và event sequence theo ADR 0005. Lưu trạng thái reconciling khi chưa rõ kết quả; kiểm tra nguyên tử và khử trùng trong DB, không chỉ trong bộ nhớ. Kiểm tra ràng buộc và đọc lại sau mở kết nối mới; không giữ transaction trong lúc chờ runtime.

  - Bằng chứng 2026-11-16: migration 001–003 dưới `apps/server/migrations/`, runner `infrastructure/persistence/database.py`, repositories Processes/Runs (và dữ liệu Project tối thiểu), test persistence tại `apps/server/tests/integration/persistence/`. Schema hiện tại 3; checksum/transaction, WAL/FULL sync, FK, busy timeout, receipt/inbox/outbox, event sequence, immutable history và reconciling có kiểm tra thực tế.
  - Kiểm tra: tạo mới, nâng schema 1→3, mở kết nối mới/restart, rollback, concurrent idempotency/CAS và ràng buộc history đạt. Sau review đã thêm migration 003 thay vì sửa migration đã áp dụng; health đọc read-only, mất/thay DB trả 503 mà không tạo file rỗng. Số test/lệnh cuối tại [báo cáo nền tảng](../../../reports/foundation-bootstrap-check.md).
  - Giới hạn: đây là storage foundation, chưa phải Run HTTP/dispatch. Repository nhận snapshot/fingerprint đã được application validate; chưa triển khai publish/DAG/JSON Schema/RFC8785 validator hoặc authorization. Artifact mới có metadata/ref, chưa upload file; không coi kho DB là catalog/menu hoàn chỉnh. Cách migration/dữ liệu runtime tại [setup](../../setup.md#dữ-liệu-và-migration).
