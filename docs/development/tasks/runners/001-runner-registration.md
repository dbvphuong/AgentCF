# Đăng ký, heartbeat và trạng thái PC

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## PC-001

- [x] **PC-001 — Đăng ký, heartbeat và trạng thái PC** — Xong | Feature
  - Phụ thuộc: [CLI-001](../client/001-authenticated-connection.md#cli-001), [DATA-001](../data/001-sqlite-persistence.md#data-001).
  - Nghiệm thu: ghép nối/thu hồi, trạng thái có nguồn thật, disable ngừng nhận việc mới nhưng không tự hủy việc đang chạy; không giao lại task chỉ vì mất heartbeat. Tách giao diện/đăng ký/heartbeat thành task nhỏ trước khi làm; kết nối local tối thiểu không đồng nghĩa menu PC hoàn chỉnh.
  - Bằng chứng 2026-11-16: Migration 005 (`005_runner_pairing.sql`), `RunnerRepository` và API routes `/v1/pairing-codes`, `/v1/runners/pair`, `/v1/runners`, `/v1/runners/{runner_id}/sessions`, `/v1/runners/{runner_id}/heartbeat`, `/v1/runners/{runner_id}/disable`, `/v1/runners/{runner_id}/enable`, `/v1/runners/{runner_id}/revoke`. Đã kiểm chứng ghép nối mã một lần, thu hồi token, vô hiệu hóa runner ngừng nhận việc và phản ánh đúng trạng thái `stop_requested`. Đã kiểm thử tự động tại `test_client_execution.py`.
