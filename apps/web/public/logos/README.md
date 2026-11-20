# Kho Icon & Brand Assets - Agent CF

Thư mục lưu trữ bộ nhận diện thương hiệu và các concept logo / icon cho Agent CF.

## 1. Nhận diện đang dùng ở sidebar (BASE-010)

- Biểu tượng CF phẳng: SVG inline tại `src/shared/BrandIdentity.tsx`, màu tím trầm, không glow hoặc video.
- Wordmark: `agent-cf-wordmark.svg`, chữ Agent và CF có tỷ trọng riêng, outline từ Bahnschrift/Bahnschrift SemiBold. Không tải font ngoài và không cần cài font để xem Web.
- Nguồn dựng: `apps/web/scripts/build-wordmark.ps1`; chạy từ root bằng `powershell.exe -NoProfile -ExecutionPolicy Bypass -File apps/web/scripts/build-wordmark.ps1` trên Windows có hai font trên. Chỉnh nguồn rồi dựng lại, không sửa trực tiếp artifact SVG được sinh.
- Favicon và các file logo/concept cũ giữ nguyên. Phạm vi/bằng chứng: [BASE-010](../../../../docs/development/tasks/base/009-sidebar-identity.md).

## Nhận diện Ribbon trước BASE-010 (lưu lịch sử)
- **Concept 2: Continuous Ribbon Flow (Nguyên bản chuẩn chữ CF)**
  - File icon active: `/logo-ribbon.png` (256x256, **nền trong suốt PNG siêu sạch**)
  - Favicon active: `/favicon.png` (64x64, **nền trong suốt PNG**)
  - Hình khối: Giữ nguyên vẹn 100% hình khối chữ **C** (Cyan neon) và **F** (Magenta neon) nguyên bản mà người dùng đã chọn từ Concept 2.
  - Xử lý tách nền: Bóc sạch toàn bộ nền tối, khói tím lem xung quanh và dòng chữ AGENT CF ở dưới bằng thuật toán bóc tách màu chính xác kết hợp khử viền (de-fringing) và anti-aliasing.
  - Hiển thị trên sidebar: Nền trong suốt tự nhiên, sắc nét từng góc cạnh.

## 2. Kho tài nguyên (Asset Library)

### Concept 2: Continuous Ribbon Flow
- **Bản Ribbon CF gốc tách nền trong suốt**:
  - Web App Icon: `/logo-ribbon.png` (256x256)
  - Full HD Transparent: `concept2-ribbon-transparent.png` (512x512)
  - Favicon: `/favicon.png` (64x64)
- **Bản gốc đầy đủ cả nền và chữ (1024x1024)**: `concept2-ribbon.jpg`

### Concept 1: Precision Minimalist (Linear / Raycast Style)
- **Bản trong suốt (Transparent PNG 512x512)**: `concept1-precision-transparent.png` (alias: `/logo-precision.png`)
- **Icon vuông có nền tối (512x512)**: `concept1-precision-icon.png` (alias: `concept1-icon.png`)
- **Poster đầy đủ (1024x1024)**: `concept1-precision.jpg`

### Concept 3: Cybernetic Hexagon
- **Poster đầy đủ (1024x1024)**: `concept3-hexagon.jpg`
