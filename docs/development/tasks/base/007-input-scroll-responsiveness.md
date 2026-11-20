# Giảm tải khi nhập liệu và cuộn hộp thoại

[Module](README.md)

## BASE-008

- [x] **BASE-008 — Giảm render nền trong hộp thoại** — Xong (phạm vi kiểm tra local) | Performance/UX
  - Người dùng báo lag khi gõ chữ/cuộn. Đo API local: median health ~14.9 ms, Projects ~8.25 ms, Skills ~6.25 ms, models/Agents ~5.9 ms; chưa thấy Server là nút thắt ở lượt đo này.
  - Logo video trước đó autoplay/loop trong khi backdrop toàn màn hình dùng blur. `BrandVideo.tsx` tạm dừng khi có modal, tab bị ẩn hoặc prefers-reduced-motion; resume khi trở lại phù hợp. Modal phát sự kiện vòng đời, không polling mỗi lần gõ. Bỏ backdrop-filter blur, giữ overlay; giữ video/logo và file gốc.
  - Kiểm chứng: `topic-run.cjs` kiểm pause trong modal, resume sau đóng, backdrop không blur, gõ không phát sinh request API. Đợt gần nhất **25 mẫu**, input→frame p95 **19.5 ms**, frame cuộn tối đa **16.8 ms**; report `runtime/topic-ui-check/browser.json`. TypeScript/Vite build và **21 Web tests** đạt.
  - Giới hạn: đo trong Edge headless trên máy này, không chứng minh mọi lần lag của trình duyệt/GPU người dùng đã hết. Không quy kết video/blur là nguyên nhân duy nhất; không thay hiệu ứng/logo do người dùng thêm ngoài phạm vi giảm tải.
