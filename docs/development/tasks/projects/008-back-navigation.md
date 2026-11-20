# Đưa quay lại Projects về dòng mô tả/PM

[Module](README.md) · [Requirements](../../../product/requirements.md#quản-lý-project-và-process-qua-giao-diện)

## PROJ-008

- [x] **PROJ-008 — Quay lại thuận tay, không thêm hàng** — Xong | UX
  - Đưa liên kết ← Projects từ góc phải tiêu đề sang đầu dòng mô tả/PM hiện có ngay dưới tiêu đề. Giữ menu ⋯ bên phải; không thay route/API hoặc editor Process.
  - Code: `Projects.tsx`, `projects.css`. Browser fixture `project-feedback.cjs` kiểm vào chi tiết, liên kết và PM cùng hàng, tiêu đề không còn nút back và quay về danh sách được.
  - Kiểm chứng 2026-11-19: `node apps/web/tests/browser/project-feedback.cjs`: **passed**, gồm kiểm vị trí cùng hàng và điều hướng vào/ra. `npm.cmd --prefix apps/web test`: **21 passed**; TypeScript/Vite build đạt. Không thay dữ liệu thật.
