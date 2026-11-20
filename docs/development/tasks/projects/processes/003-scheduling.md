# Schedule và lựa chọn PC

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../../README.md) · [Kế hoạch tổng](../../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## PROC-004

- [x] **PROC-004 — Schedule và lựa chọn PC** — Xong (2026-11-16) | Feature
  - Phụ thuộc: [PROC-003](002-process-editor.md#proc-003), [PC-001](../../runners/001-runner-registration.md#pc-001), [RUN-006](../../runs/003-skill0-web.md#run-006); policy PC và khóa lịch trùng theo [execution model](../../../../architecture/execution-model.md#kích-hoạt-theo-lịch).
  - Nghiệm thu: Start/Stop khác Manual Run/Cancel, không tạo trùng lượt, không tự đổi version của lịch; test lịch đến hạn khi lượt cũ chưa xong.
  - Hiện thực:
    - Bổ sung bảng `schedules` và `schedule_ticks` trong migration `009_schedules_and_overview.sql`.
    - Quy tắc Save không Start: tạo/lưu lịch luôn khởi tạo ở trạng thái `is_active = 0` và không sinh run.
    - Quy tắc Start không Run ngay: kích hoạt lịch chuyển `is_active = 1` và tính toán `next_run_at`, không kích hoạt run ngay lập tức.
    - Quy tắc Stop không Cancel: dừng lịch chuyển `is_active = 0`, không làm gián đoạn hay hủy các lần chạy đang thực hiện.
    - Quy tắc Cancel không Stop: hủy một ProcessRun riêng lẻ không ảnh hưởng đến trạng thái hoạt động của lịch.
    - Version được ghim: `process_version_id` được ghim chặt chẽ vào version published tại thời điểm tạo lịch; việc phát hành ProcessVersion mới không làm thay đổi version của lịch.
    - Chống tạo trùng lượt: ràng buộc duy nhất trên `(schedule_id, scheduled_for)` loại trừ khả năng kích hoạt trùng lặp cùng một mốc thời gian.
    - Xử lý lịch đến hạn khi lượt cũ chưa xong: kiểm tra trạng thái lượt chạy trước đó (`last_run_id`), ghi nhận tick dạng `skipped_busy` và từ chối tạo lượt chạy chồng chéo (`ConflictError("schedule_busy")`).
    - Ràng buộc PC Runner: nếu chỉ định Runner cụ thể, kiểm tra trạng thái hoạt động và phiên kết nối; từ chối thực thi khi máy offline hoặc bị vô hiệu hóa (`runner_offline`).
  - Kiểm chứng:
    - `test_save_schedule_does_not_start_and_does_not_run`
    - `test_start_schedule_does_not_run_immediately`
    - `test_stop_schedule_does_not_cancel_active_runs`
    - `test_cancel_run_does_not_stop_schedule`
    - `test_pinned_version_immutable_when_new_version_published`
    - `test_schedule_deduplication_by_scheduled_for`
    - `test_schedule_busy_skips_when_previous_run_active`
    - `test_schedule_pc_selection_policy_offline_disabled`
