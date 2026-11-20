# Runtime, model và khả dụng trên máy

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## SET-001

- [x] **SET-001 — Danh mục runtime/model và khả dụng trên máy** — Xong | Feature
  - Phụ thuộc: [BASE-001](../base/001-foundation-design.md#base-001), [API-001](../api/001-run-client-contract.md#api-001), [RTM-004](../runtime/001-local-verification.md#rtm-004).
  - Nghiệm thu: tách nhãn, ID runtime, effort khi hỗ trợ và quyền/khả dụng; làm mới khi đổi máy/tài khoản, giữ đủ nhãn người dùng muốn. ID chưa biết không được đoán; UI thấy lựa chọn không đồng nghĩa đã chạy được. Inventory JSON hiện tại chỉ là nguồn tham chiếu.
  - Bằng chứng 2026-11-16: Module `agent_cf_server.infrastructure.settings.inventory` và endpoint `GET /v1/settings/runtime-inventory`. Nạp dữ liệu từ `local-runtime-models.json`, giữ nguyên nhãn Antigravity/Codex, không đoán ID chưa xác định (giữ `None`), có trạng thái truy cập và UI status. Đã kiểm thử tự động tại `test_settings_skills_agents.py`.
