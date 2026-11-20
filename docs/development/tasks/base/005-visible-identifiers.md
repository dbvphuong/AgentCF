# Tên dễ đọc và ID trong chi tiết kỹ thuật

[Module](README.md) · [Requirements](../../../product/requirements.md#yêu-cầu-theo-màn-hình)

## BASE-006

- [x] **BASE-006 — Giảm ID kỹ thuật trên giao diện thường dùng** — Xong | Fix
  - Yêu cầu: bảng/form hiển thị tên thay UUID; ID cần tra lỗi nằm trong phần Chi tiết kỹ thuật mặc định đóng, có sao chép. Không xóa ID khỏi dữ liệu, URL, request hoặc thay cách tham chiếu thực thi.
  - Phạm vi: Catalog dùng chung, Skill version, Runs/detail/form, Overview, PC, Process editor và Schedule; Model ID thực dùng để cấu hình runtime, mã ghép nối, đường dẫn Skill/output và số version vẫn hiển thị khi cần thao tác.
  - Nghiệm thu: không có UUID hệ thống ở bảng/form/trang chi tiết mặc định; tên Role/Model/Agent/PC/bước lấy từ catalog hoặc execution snapshot đúng version, thiếu tên thì nhãn rõ thay vì fallback UUID. Mở Chi tiết kỹ thuật xem/sao chép được ID; tìm theo ID và deep link vẫn dùng; form Run vẫn gửi ProcessVersion ID thật dù ô hiển thị số version.

### Bàn giao 2026-11-18

- `shared/TechnicalDetails.tsx` dùng disclosure native mặc định đóng, cho xem/sao chép nguyên ID. Catalog và Skill versions bỏ ID trực tiếp dưới tên. Settings/Agents/Process editor bỏ fallback ID thành tên hiển thị khi thiếu catalog; Model ID runtime trong Settings được giữ.
- Runs list dùng tên Process và chủ đề/thời gian để phân biệt lượt; chi tiết Run dùng tên Process, số version và tên bước từ đúng published version. PC hiển thị tên thay Runner ID; Run/Task IDs, digest và output JSON vào Chi tiết kỹ thuật. Form Run từ Project nhận số version làm nhãn, vẫn giữ ID trong state/request. Tra cứu theo ID giữ nguyên khả năng sẵn có, không đổi thành tìm kiếm tên ở backend.
- Overview lấy tên Role/Model từ catalog; cảnh báo giữ ID trong disclosure. PC detail hiển thị tên Workspace/Agent và thông tin vận hành; ID, machine fingerprint chuyển vào disclosure. Schedule hiển thị số version; editor vẫn cho cấu hình runtime Model ID và input mapping khi cần.
- Không đổi schema/migration, API hoặc dữ liệu; không sửa Skill nguồn, file output, credential hoặc hành vi chạy. Không lược bỏ ID trong log/lỗi nghiệp vụ hay đường dẫn file thực tế.
- Web `typecheck`, `test` (**19 passed**) và `build` đạt. Không chạy lại bộ Python vì thay đổi chỉ ở Web/tài liệu.
- `node apps/web/tests/browser/identifiers.cjs`: đạt trên Edge headless/CDP, dữ liệu local hiện có. Kiểm tra catalog ID mặc định ẩn, mở/sao chép đúng chuỗi đầy đủ (mock clipboard trong tab thử, không ghi clipboard người dùng); Run/detail/Task/version IDs ẩn, số version trong form đúng; request vẫn chứa ID thật. POST tạo Run được CDP chặn và trả phản hồi thử, **không tạo Run/gọi model/thay dữ liệu**. Rà thêm PC, Agents, Overview, editor, Skill versions, Models và Robots; không JavaScript exception.
- Bằng chứng/ảnh local ở `runtime/visible-identifiers/result.json`, `run-default.png`, `run-form-version.png`, `catalog-technical-open.png`. Browser script nhận `BASE_URL`, `CDP_URL`, `ARTIFACT_DIR`; cần catalog Skill/Run/Process đã publish có sẵn, không tự seed dữ liệu.

### Giới hạn

Đây là quy tắc trình bày, không phải cơ chế che secret hay phân quyền dữ liệu. Người dùng vẫn có thể chủ động mở phần kỹ thuật, xem log/lỗi, URL và request. Nếu catalog không cung cấp tên, UI báo thiếu tên và giữ ID trong phần kỹ thuật để tra cứu.
