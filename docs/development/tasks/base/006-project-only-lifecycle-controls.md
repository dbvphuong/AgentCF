# Bỏ Archive/Restore ngoài Project trên Web

[Module](README.md) · [Requirements](../../../product/requirements.md#quản-lý-agents-skills-và-tools-qua-giao-diện)

## BASE-007

- [x] **BASE-007 — Bỏ thao tác Archive/Restore ngoài Project** — Xong | Fix
  - Người dùng yêu cầu bỏ Archive/Restore vì không cần dùng; riêng Project giữ nguyên Ngừng hoạt động/Kích hoạt lại.
  - Phạm vi: bỏ nút và bộ lọc lưu trữ khỏi Skills, Tools, Agents, Robots, Roles, Process; không xóa dữ liệu cũ, tự khôi phục trạng thái hoặc thay cách xử lý version/lịch sử. Provider/Model enable-disable, PC disable, Schedule Start/Stop và Cancel Run là thao tác khác, giữ nguyên.
  - Nghiệm thu: không có thao tác/bộ lọc Archive/Restore ở các màn trên; thêm/sửa/xóa vẫn có; Project vẫn có trạng thái/bộ lọc và menu Ngừng hoạt động/Kích hoạt lại; đọc dữ liệu không phát sinh mutation.
  - Backend enum/API lịch sử giữ để tương thích. Dữ liệu đã archived từ trước không tự bật lại; danh sách thao tác thường dùng tiếp tục chỉ lấy mục chưa archived. Chính sách Delete bảo vệ lịch sử vẫn giữ như hiện có.

### Bàn giao 2026-11-18

- `shared/Catalog.tsx` bỏ chế độ/bộ lọc trạng thái và nút Archive/Restore, xác nhận Xóa không còn giới thiệu lưu trữ; Providers/Models bỏ prop không còn cần. Skills/Tools/Agents/Roles dùng Catalog chung nên cùng áp dụng.
- `RobotList.tsx` bỏ bộ lọc Active/Archived/All, handler/nút lưu trữ/khôi phục; chỉ lấy Robot active. Bỏ helper gọi Archive/Restore không còn dùng trong Web API module. Badge dữ liệu cũ trong detail dùng nhãn phù hợp, không tạo điều khiển khôi phục.
- Project → Processes bỏ nút Archive/Restore, không liệt kê Process archived cũ trong danh sách thao tác thường dùng. ProjectActions/ProjectList và luồng Ngừng hoạt động/Kích hoạt lại của Project giữ nguyên. Thao tác Xóa/bảo vệ version và lịch sử không đổi.
- Không đổi Server, migration, API contract hoặc dữ liệu. Không gọi model, không tự khôi phục bản ghi đã archived. Enum/endpoint cũ còn ở backend cho tương thích; phạm vi này là bỏ thao tác trên Web.
- Web `typecheck`, `test` (**19 passed**) và `build`: đạt. Không chạy lại Python vì không thay backend.
- `node apps/web/tests/browser/project-only-controls.cjs`: Edge headless/CDP kiểm Skills, Tools, Agents, Robots, Settings → Roles và Project → Process không có nút/option Archive/Restore. Menu Project vẫn có Ngừng hoạt động (hoặc Kích hoạt lại theo trạng thái) và bộ lọc Không hoạt động. **Không có mutation request hoặc JavaScript exception**; không thay trạng thái Project để thử. Bằng chứng `runtime/project-only-controls/result.json`, `project-menu.png`.
