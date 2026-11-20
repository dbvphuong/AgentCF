# Thông báo kết quả thao tác Project

[Module](README.md) · [Requirements](../../../product/requirements.md#quản-lý-project-và-process-qua-giao-diện)

## PROJ-006

Quy tắc cảnh báo Chưa xóa do lịch sử được thay bởi [PROJ-007](007-permanent-deletion.md); Delete hiện xóa hẳn, chỉ chặn Run chưa kết thúc. Bằng chứng dưới ghi hành vi ở thời điểm triển khai toast ban đầu.

- [x] **PROJ-006 — Hiển thị kết quả thao tác ở góc phải** — Xong | UX/Bug
  - Phụ thuộc: PROJ-003/005. Thay Notice kết quả khó thấy bằng Toast góc trên bên phải, tự đóng sau 6 giây, có đóng thủ công; phân biệt thành công/cảnh báo/lỗi bằng nhãn và màu.
  - Xóa cứng báo thành công. `{deleted:false,status:archived}` báo rõ Chưa xóa vì lịch sử/phiên bản published, Project được giữ Không hoạt động. API thất bại báo lỗi ở toast và trong modal; giữ modal để thử lại. Ngừng hoạt động/Kích hoạt lại và nhân bản thành công dùng cùng thông báo. Không thay quy tắc xóa/bảo toàn lịch sử và không mở rộng sang mọi màn hình.
  - Code: `shared/Toast.tsx`, `toast.css`, callback `Confirm.onError` tùy chọn trong `shared/ui.tsx`, tích hợp `features/projects/Projects.tsx`. Error toast nằm trong native dialog để không bị backdrop che và nút đóng nhận tương tác được.
  - Kiểm chứng 2026-11-19: `node apps/web/tests/browser/project-feedback.cjs`: **passed** — chặn API Project bằng fixture trên trình duyệt, kiểm warning/error/success, retry sau lỗi, tự đóng/đóng thủ công, vị trí desktop/mobile và nút đóng nằm trên backdrop. Không gửi mutation tới Server thật. `npm.cmd --prefix apps/web test`: **21 passed**; `npm.cmd --prefix apps/web run build`: TypeScript/Vite đạt.
