# Tổng quan từ dữ liệu thật

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## OVW-001

- [x] **OVW-001 — Tổng quan từ dữ liệu thật** — Xong (2026-11-16) | Feature
  - Phụ thuộc: [RUN-006](../runs/003-skill0-web.md#run-006), [PROJ-002](../projects/002-team-targets.md#proj-002), [AGN-003](../agents/002-agent-catalog.md#agn-003).
  - Nghiệm thu: cảnh báo chưa xử lý, tiến độ Project/Target, token có nguồn thì hiển thị; thiếu dữ liệu thì thể hiện chưa có, không bịa số. Dùng quy tắc từ module sở hữu, đánh dấu xử lý lỗi không đổi status Run.
  - Hiện thực:
    - Bổ sung bảng `project_targets`, `run_error_acknowledgments` và `agent_token_usage` trong migration `009_schedules_and_overview.sql`.
    - Khối cảnh báo lỗi: hiển thị danh sách các lượt chạy thất bại (`failed`) chưa được đánh dấu xử lý, liên kết trực tiếp tới chi tiết lượt chạy.
    - Đánh dấu xử lý lỗi: endpoint `POST /v1/runs/{run_id}/acknowledge-error` ghi nhận xác nhận của người vận hành mà không làm thay đổi trạng thái gốc của lượt chạy (vẫn giữ nguyên `status = 'failed'`).
    - Tiến độ Projects & Targets: liên kết trực tiếp với dữ liệu thực tế trong cơ sở dữ liệu. Dự án chưa cấu hình mục tiêu hiển thị dấu `"—"`, không bịa đặt tỷ lệ 0/0 hoặc phỏng đoán "On track".
    - Thống kê Token Agents: sắp xếp theo tổng số token tiêu thụ thực tế từ cao xuống thấp; các Agent chưa có dữ liệu token được hiển thị rõ ràng `"— (Chưa có dữ liệu)"`.
    - Giao diện Frontend: màn hình `Overview.tsx` kết nối API tổng quan, có nút xử lý cảnh báo, bảng tiến độ và bảng token, tích hợp trực tiếp vào thanh điều hướng của Web App.
  - Kiểm chứng:
    - `test_overview_unresolved_errors_and_acknowledgment`
    - `test_overview_project_progress_with_and_without_targets`
    - `test_overview_agent_token_usage_ranked_and_no_fabricated_data`
    - Web unit tests: `overview acknowledgeRunError constructs correct URL with escaping`, `overview API generates distinct idempotency keys`, `overview displays dash for missing targets and does not fabricate 0/0 or On track`, `overview displays dash and explicit label for missing token usage`.
