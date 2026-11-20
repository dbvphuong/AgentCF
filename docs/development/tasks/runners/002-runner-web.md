# Giao diện Web quản lý danh sách PC và ghép nối Runner

> Last updated: 2026-11-17

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## PC-002

- [ ] **PC-002 — Giao diện Web quản lý danh sách PC và ghép nối Runner (PC View)** — Đang làm (UI đã có, còn telemetry) | Feature
  - Phụ thuộc: [PC-001](001-runner-registration.md#pc-001).
  - Nghiệm thu: Bảng danh sách PC hiển thị tên, hệ điều hành, trạng thái (online, offline, busy, disabled), Last seen; máy offline không hiển thị số đo cũ như tải hiện tại; modal Connect sinh và hiển thị mã ghép nối một lần có thời hạn; hành động Sửa/Xóa theo [PC-003](003-edit-remove.md); xem chi tiết TaskRun đang chạy trên PC được chọn.
  - Đã đạt 2026-11-17: `features/runners/`, Connect code 10 phút, hạn giờ Việt Nam/RFC3339; bảng heartbeat/tải, display_status từ độ mới heartbeat và Attempt đang thực thi; link Current Run, modal TaskRun, Disable/Enable/Revoke có xác nhận. Browser smoke pairing/Disable và desktop/mobile đạt; regression timestamp pairing. [Báo cáo](../../../reports/ui-completion-check.md).
  - Còn lại: Client chưa báo OS và thông số phần cứng chi tiết (RAM tuyệt đối), UI hiển thị `—` khi thiếu, không đoán từ fingerprint. Cần bổ sung telemetry và nghiệm thu PC busy/mất kết nối với Client thật trước khi tích toàn menu PC.


Ngày 2026-11-18: PC-003 thay Disable/Enable/Revoke bằng Sửa/Xóa trên Web. Bằng chứng 2026-11-17 ở trên phản ánh UI cũ; telemetry còn lại không đổi.
