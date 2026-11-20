# Giao diện Web cài đặt hệ thống (Settings View)

> Last updated: 2026-11-17

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## SET-003

- [x] **SET-003 — Giao diện Web cài đặt hệ thống (Settings View)** — Xong | Feature
  - Phụ thuộc: [SET-001](001-runtime-models.md#set-001), [SET-002](002-general-configuration.md#set-002).
  - Nghiệm thu: Giao diện Web gồm 4 tab theo spec: Providers & API, Models, Roles, General. Quản lý cấu hình LLM providers, model identifiers, roles & duties; cấu hình timeouts và log line limits ở General; bảo vệ API keys/secrets không bao giờ render plaintext hoặc lưu log client; gọi backend test connection thật an toàn.
  - Bằng chứng 2026-11-17: `features/settings/Settings.tsx`, bốn tab nối API thật, input password luôn rỗng khi sửa, không lưu localStorage; Test API chạy ở Server, không redirect hoặc trả response body provider. Regression mock HTTP 401 chứng minh không lộ khóa/body; kết quả HTTP không được coi là bằng chứng chạy từng model. [Báo cáo](../../../reports/ui-completion-check.md).
  - Giới hạn quan trọng: bảo vệ hiển thị trên Web không thay thế secret store; vấn đề lưu credential của backend hiện có được ghi riêng [SET-004](004-provider-secret-store.md).
