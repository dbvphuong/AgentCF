# Sửa tên và xóa kết nối PC

[Module](README.md) · [Yêu cầu](../../../product/requirements.md#quản-lý-pc)

## PC-003

Reconnect PC còn tồn tại đã đổi theo [PC-004](004-device-reconnect-metrics.md): giữ identity và thêm Kết nối/Hủy kết nối ở cột thao tác. Xóa vẫn là thao tác riêng; ghi nhận dưới đây giữ theo thời điểm triển khai ban đầu.

- [x] **PC-003 — Connect PC phía trên, Sửa/Xóa tại mỗi dòng** — Xong | Feature
  - Phụ thuộc: [PC-001](001-runner-registration.md#pc-001), phần bảng/ghép nối của [PC-002](002-runner-web.md#pc-002).
  - Nghiệm thu: giữ Connect PC; dòng chỉ có Sửa/Xóa; sửa tên giữ identity/kết nối; xóa có xác nhận, ẩn PC và thu hồi kết nối, giữ file và lịch sử; chặn xóa khi liên quan run chưa kết thúc. Ghép nối lại tạo identity mới.
  - Server: PATCH/DELETE `/v1/runners/{runner_id}`, validation tên, audit; migration 013 thêm `deleted_at` để giữ khóa ngoại lịch sử. Xóa tắt Schedule chọn PC hoặc có node ghim PC đó; Enable cũ không phục hồi PC đã xóa. Run mới từ version ghim PC đã xóa bị từ chối.
  - Web: `features/runners/Runners.tsx`; form Sửa tên, xác nhận Xóa, lỗi từ Server hiển thị trong modal. Connect và trang chi tiết giữ nguyên.

### Kiểm chứng 2026-11-18

- `.venv/Scripts/python.exe -m pytest -q`: **198 passed, 1 skipped** (Temporal opt-in); có ba integration test mới tại `apps/server/tests/integration/runners/test_runner_actions.py`. Kiểm tra đổi tên, validation, credential sau đổi tên/xóa, idempotent delete, không phục hồi bằng Enable, chặn queued run ghim PC, lịch sử giữ nguyên và lịch bị tắt.
- `npm.cmd test`, `npm.cmd run build` tại `apps/web`: **19 passed**, TypeScript và Vite build đạt. PowerShell chặn `npm.ps1`; dùng `npm.cmd` thành công.
- `node openapi/check-contract.cjs`: **81 schemas, 59 paths, 77 operations** đạt.
- `apps/web/tests/browser/pc-actions.cjs` với Server DB riêng port 18088, Web 5188, Edge CDP 9350: **passed**; Connect mở modal, chỉ có Sửa/Xóa, đổi tên giữ qua reload và Xóa gỡ dòng. Không chạy model hoặc xóa PC thật. Smoke tổng được cập nhật thao tác mới nhưng không chạy lại toàn bộ trong task này.
- Server local 8000 đã khởi động lại để áp dụng migration/API; kiểm tra không có run chưa terminal trước khi dừng, health đạt và toàn bộ tên/identity PC hiện có giữ nguyên.
- Không bổ sung telemetry hay bộ cài; phần PC-002 còn lại vẫn chưa nghiệm thu.
