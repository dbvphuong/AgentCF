# File Markdown chính trong form Thêm/Sửa Skill

[Module](README.md) · [Requirements](../../../product/requirements.md#giữ-quy-trình-và-output-trên-pc) · [ADR 0006](../../../architecture/decisions/0006-local-skill-paths-and-pc-outputs.md)

## SKL-005

- [x] **SKL-005 — Nhập đường dẫn hoặc chọn file .md chính khi Thêm/Sửa Skill** — Xong | Feature
  - Phụ thuộc: SKL-003, SKL-004, chế độ Skill local tại ADR 0006.
  - Nghiệm thu: form chính và tạo Skill từ Process editor có PC chứa file, đường dẫn tuyệt đối và Chọn file; chỉ chọn file .md chính, không upload nội dung/ref. Lưu tham chiếu, runtime đọc file gốc; relative ref dựa trên thư mục chứa file chính. Không bắt buộc tên `SKILL.md`.
  - Lưu metadata và tham chiếu draft nguyên tử trong API Skill create/update. Giữ version đã publish; đổi nguồn từ bản published tạo draft kế tiếp, không tự publish hoặc sửa Process đang chạy. Các Skill nội dung cũ tiếp tục tương thích.
  - File chooser gửi yêu cầu ngắn hạn qua heartbeat tới đúng Client, chỉ đọc danh sách thư mục/.md. Server không duyệt đĩa thay PC, không nhận nội dung file. Client cần chạy bản mới; không phản hồi sẽ báo lỗi và vẫn có thể dán đường dẫn. Browse không tạo ProcessRun hay gọi model.
  - Request ở bộ nhớ Server: hết hạn sau 60 giây hoặc restart, tối đa 128 request; mỗi lần gửi tối đa 8, mỗi thư mục tối đa 500 mục. Kết quả cần credential và session hiện hành của đúng PC; từ chối PC bị xóa/disabled, sai session, sai PC và kết quả quá lớn. Không dùng queue thực thi Process cho việc chọn file.

### Code và kiểm chứng 2026-11-18

- Web: `features/skills/SkillFileField.tsx`, `Skills.tsx`, `NewProjectSkill.tsx`; `shared/ui.tsx` hỗ trợ render trường tùy biến. Versions dùng chung trường đường dẫn/chọn file.
- Server: API Skill, SkillRepository lưu nguồn vào draft; domain nhận file `.md`; `api/runners.py` và `infrastructure/runners/file_browser.py` chuyển metadata chooser qua heartbeat. Không đổi schema/migration.
- Client: `connection/skill_files.py`, `client_session.py`; `execution/local_skill.py` gọi file .md gốc với ref theo thư mục gốc.
- `.venv/Scripts/python.exe -m pytest -q`: **213 passed, 1 skipped**; integration tại `integration/runners/test_skill_files.py` kiểm tra lưu nguyên tử/rollback, published bất biến, Client heartbeat thực hiện browse, scope/session/credential và TTL/giới hạn. Test local Skill chạy cả `SKILL.md` lẫn `main.md`.
- `npm.cmd test`: **19 passed**; `npm.cmd run build`: TypeScript/Vite đạt. `node openapi/check-contract.cjs`: **85 schemas, 62 paths, 80 operations** đạt.
- `apps/web/tests/browser/skill-file.cjs`: **passed** với Server DB riêng port 18088, Web 5188, Edge CDP 9350 và Client heartbeat thật. Tạo Skill bằng chọn `main.md`, lưu đường dẫn/PC, mở Sửa và dán đường dẫn khác. Không gọi model, không sửa Skill/ref nghiệp vụ của người dùng.
- Server 8000 và Client demo hiện có đã nạp bản mới. Browse thử thư mục Skill 0 trả đường dẫn `SKILL.md` thật; kiểm tra tên/identity PC và danh sách Run không đổi, không tạo/chỉnh Skill hay cấu hình Project thật. Client được khởi động từ manifest hiện có, không chạy lại setup hoặc gọi model.
- Giới hạn: thử UI trên Windows local; không coi đây là kiểm chứng chạy model hoặc kết nối qua mạng giữa nhiều máy. Kiểm tra file tồn tại/UTF-8 và quyền runtime diễn ra tại PC khi thực thi; việc dán đường dẫn không đọc file trên Server.
