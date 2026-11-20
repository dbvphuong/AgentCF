# Chờ người dùng và Continue an toàn

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## REL-003

- [x] **REL-003 — Chờ người dùng và Continue an toàn** — Xong (2026-11-16) | Feature
  - Phụ thuộc: [RUN-007](../runs/004-skill-chain.md#run-007), [REL-001](002-recovery.md#rel-001).
  - Nghiệm thu: mở rộng domain/execution/contract trước khi thêm trạng thái chờ; chạy được tình huống 3/5 node đã đạt, người dùng xử lý và Continue đúng bước, giữ ba output, Continue trùng không chạy trùng. Phân biệt chờ tool cũ và tạo Attempt mới; không chuyển Run terminal ngược thành running.
  - Hiện thực:
    - Bổ sung migration `008_human_continue.sql`: thêm cột `waiting_for` và `attention_reason` vào `task_runs`; tạo bảng `human_decisions` với khóa chống trùng duy nhất (`decision_key`).
    - Cập nhật OpenAPI contract `openapi/openapi.yaml`: thêm endpoint `POST /v1/runs/{run_id}/continue` với operationId `continueRun`, scope `operator`, bắt buộc `Idempotency-Key` và schema `ContinueRunRequest`.
    - Server API & Repository: triển khai `continue_run` và `set_task_waiting_for_input`, bảo vệ trạng thái kết thúc (từ chối gọi continue trên run terminal với lỗi `409 ConflictError("run_terminal")`), lưu quyết định người dùng vào `human_decisions`, chuyển node chờ sang thành công/tiếp tục và kích hoạt các node phụ thuộc tiếp theo.
    - Web UI: tích hợp banner cảnh báo "Đang chờ người dùng", nút bấm "Tiếp tục (Continue)" trong chi tiết lượt chạy, hiển thị thông tin chờ trong bảng tasks và hàm gọi API `continueRun` kèm theo sinh khóa idempotency tự động.
  - Kiểm chứng:
    - `test_safe_human_continue_scenario_3_of_5_complete`: 3/5 node hoàn thành, node 4 tạm dừng chờ duyệt người dùng; gọi continue thành công, bảo toàn nguyên vẹn 3 output trước đó, node 4 và node 5 tiếp tục hoàn thành, toàn bộ run đạt `succeeded`.
    - `test_idempotent_continue_call`: gọi continue nhiều lần với cùng `Idempotency-Key` trả về cùng kết quả mà không tạo quyết định trùng lặp hay chạy lại task.
    - `test_continue_on_terminal_run_rejected`: từ chối gọi continue trên run đã kết thúc (`cancelled`/`succeeded`/`failed`).
    - Web unit tests: `continueRun constructs correct URL with escaping`, `runs API generates distinct idempotency keys`.
