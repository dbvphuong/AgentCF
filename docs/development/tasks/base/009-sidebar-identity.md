# Nhận diện và tương tác sidebar

[Module](README.md) · [Yêu cầu](../../../product/requirements.md#yêu-cầu-theo-màn-hình)

## BASE-010

- [x] **BASE-010 — Làm gọn nhận diện, icon và trạng thái tương tác sidebar** — Xong | Design/Feature
  - Yêu cầu: áp dụng hướng thiết kế người dùng đã duyệt trong trao đổi ngày 2026-11-20: wordmark riêng, CF phẳng, tím tiết chế, icon rõ và chuyển động ngắn, không nhún/xoay/phát sáng.
  - Phụ thuộc: [BASE-004](003-web-navigation.md#base-004); đối chiếu [BASE-008](007-input-scroll-responsiveness.md#base-008) để tránh đưa video/hiệu ứng nặng trở lại.
  - Phạm vi: `apps/web/src/app/{App.tsx,styles.css}`, `shared/BrandIdentity.tsx`, tám icon trong `shared/icons/`, `public/logos/agent-cf-wordmark.svg`; nguồn dựng wordmark `scripts/build-wordmark.ps1`. Giữ tên, thứ tự menu, hash/deep link, Ctrl/Cmd+K, guard thay đổi chưa lưu và nghiệp vụ/API. Logo/favicon cũ giữ nguyên file.
  - Nghiệm thu: logo/wordmark sắc ở kích thước sidebar, không cần tải font; chữ và tiêu đề nhóm có phân cấp; tám icon cùng nét 1.7, Skills khác Tổng quan. Hover 140 ms, nhấn 60 ms, nền chọn cố định; không đổi kích thước/vị trí. Focus rõ; mobile và chế độ giảm chuyển động hoạt động.
  - Kiểm chứng 2026-11-20:
    - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File apps/web/scripts/build-wordmark.ps1`: tạo lại SVG từ outline Bahnschrift/Bahnschrift SemiBold trên Windows; Web dùng SVG đã lưu nên không phụ thuộc font máy người dùng.
    - Trong `apps/web`: `npm.cmd run build` đạt (gồm TypeScript), `npm.cmd test`: **22 passed**. Package chưa định nghĩa lệnh lint riêng.
    - Từ root: `node apps/web/tests/browser/sidebar.cjs` với Vite `5173`, Edge headless CDP `9371`: đạt cả tám menu, route con, hover/nhấn không xê dịch, Tab/Enter/focus, command palette, tablet 800 px, mobile 390 px và Escape, reduced-motion; **0 lỗi JavaScript, 0 mutation API**. Fixture chặn mọi API, không dùng dữ liệu thật.
    - Đã xem ảnh `runtime/sidebar-review/{sidebar,desktop,mobile}.png`; report `runtime/sidebar-review/browser.json`. Artifacts kiểm chứng nằm trong thư mục runtime được ignore.
  - Giới hạn: kiểm chứng giao diện trên Edge tại máy này; không tuyên bố nghiệm thu mọi trình duyệt hoặc toàn bộ sản phẩm, không gán điểm UX khách quan từ test tự động. API/schema/runtime thực thi không đổi.

## Cập nhật mẫu logo sidebar ngày 2026-11-23

- Thay cụm logo đầu sidebar bằng SVG `apps/web/public/logos/agent-cf-sidebar.svg` theo mẫu người dùng chọn. C mở ôm F, có ô vuông tím và chữ Agent CF. Tám icon menu, favicon và đích liên kết Overview giữ nguyên.
- Trong `apps/web`, `npm.cmd run build` đạt (gồm TypeScript) và `npm.cmd test` đạt **28 tests**. `node apps/web/tests/browser/sidebar.cjs` từ root đạt trên Edge với fixture, kiểm tra SVG tải được, đích Overview, tám mục menu, tablet, mobile và reduced-motion. Báo cáo và ảnh nằm tại `runtime/sidebar-logo-review/`.
