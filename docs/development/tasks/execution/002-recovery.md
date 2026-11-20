# Đối soát khi Client/Server gián đoạn

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## REL-001

- [x] **REL-001 — Reconcile khi Client/Server gián đoạn** — Xong (2026-11-16) | Feature
  - Phụ thuộc: [RUN-006](../runs/003-skill0-web.md#run-006), [CLI-001](../client/001-authenticated-connection.md#cli-001), [CLI-002](../client/002-process-execution.md#cli-002), [REL-004](001-execution-permissions.md#rel-004).
  - Nghiệm thu: mở rộng cơ chế bảo vệ của [REL-004](001-execution-permissions.md#rel-004) thành đối soát trạng thái sau restart/reconnect; xác định tiến trình cũ, quyền thực thi và kết quả đến muộn, không gây chạy trùng hoặc ghi đè terminal state. Bổ sung ADR nếu thay policy đã chốt; không mặc định retry mọi side effect. Quyền nhận việc và chống trùng tối thiểu đã bắt buộc trước [RUN-006](../runs/003-skill0-web.md#run-006), không hoãn đến task này.
  - Hiện thực:
    - Bổ sung kiểm tra hạn cấp quyền thực thi (`expires_at < at`) và thu hồi (`revoked_at IS NOT NULL`) trên bảng `execution_grants`, trả về mã lỗi `409 ConflictError("stale_execution")` khi kết quả đến muộn hoặc phiên cũ bị thu hồi.
    - Bảo vệ tính bất biến của trạng thái kết thúc (`succeeded`, `failed`, `cancelled`), từ chối mọi yêu cầu ghi đè trạng thái đã chốt.
    - Triển khai endpoint `POST /v1/attempts/{attempt_id}/observations` theo đúng đặc tả OpenAPI, cho phép Runner gửi bằng chứng/chẩn đoán hậu kỳ (post-mortem evidence) mà không cấp quyền thực thi mới hay sửa đổi kết quả đã chốt.
    - Đối soát bền vững sau restart Server: phục hồi toàn bộ trạng thái ProcessRun, TaskRun, Attempt từ SQLite mà không mất mát dữ liệu.
  - Kiểm chứng:
    - `test_expired_lease_rejects_late_complete_attempt`: từ chối hoàn thành khi hết hạn lease.
    - `test_revoked_grant_rejects_complete_attempt`: từ chối hoàn thành khi grant bị thu hồi.
    - `test_terminal_state_protection_and_post_mortem_observation`: cấm ghi đè trạng thái kết thúc và ghi nhận observation an toàn.
    - `test_server_restart_preserves_consistent_state`: khôi phục trạng thái nhất quán sau khi khởi động lại server.
