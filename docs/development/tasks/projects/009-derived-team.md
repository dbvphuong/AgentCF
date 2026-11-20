# Team chỉ hiển thị theo PM và phân công node

[Module](README.md) · [Requirements](../../../product/requirements.md#projects-team-và-targets)

## PROJ-009

- [x] **PROJ-009 — Tự tổng hợp Team, bỏ quản lý thành viên thủ công** — Xong | Behavior/UX
  - Theo yêu cầu: PM chọn khi tạo/sửa Project; nhân viên chọn khi tạo node. Team chỉ hiển thị để nắm phân công, không cần thao tác thêm thành viên.
  - Nguồn Team: PM hiện tại hợp với `agent_id` trong node của phiên bản mới nhất đã lưu của từng Process, khử trùng theo ID. Draft mới nhất nếu có, nếu không là published mới nhất. Đổi/xóa node, đổi PM hoặc xóa Process phản ánh khi tải lại, không lấy membership cũ hoặc toàn bộ version lịch sử. Clone tự tổng hợp từ PM/Process bản sao, không chép membership thủ công.
  - Web bỏ Manage team ở tab Team và Quản lý Team/modal ở node. Node AI/Robot chọn mọi Agent active từ catalog; vẫn giữ kiểm Skill/model/tool/runtime. Editor quay về Project làm mới dữ liệu, không giữ Team cũ.
  - Server publish kiểm Agent tồn tại/active và catalog/quyền liên quan, không bắt thuộc Team trước. GET Project trả view Team; PUT Team cũ deprecated trả 422 giải thích nguồn tự động. Giữ bảng `project_team` cũ cho tương thích dữ liệu, không dùng làm nguồn, không có migration hoặc sửa snapshot/history.
  - Code: `infrastructure/projects/management.py`, API Projects và generator OpenAPI, `Projects.tsx`, `ProcessEditor.tsx`, `NodeForm.tsx`. Nguồn chuẩn requirements/domain cập nhật cùng thay đổi; thay quy tắc quản lý Team tại PROJ-002/PROC-005.
  - Kiểm chứng 2026-11-19:
    - `.venv/Scripts/python.exe -m pytest -q`: **252 passed, 1 skipped**. Regression mới kiểm PM-only, chọn Agent chưa có Team và publish, lặp nhiều node/Process, đổi/xóa phân công, PM mới, clone độc lập, draft mới so với version lịch sử và từ chối sửa Team thủ công. Regression clone dùng phân công node thật thay membership fixture.
    - `npm.cmd --prefix apps/web test`: **21 passed**; `npm.cmd --prefix apps/web run build`: TypeScript/Vite đạt.
    - `node apps/web/tests/browser/project-feedback.cjs`: **passed**, dùng fixture API, kiểm tab Team chỉ đọc, không còn nút quản lý, dropdown node có Agent ngoài Team hiển thị, điều hướng và toast. Không tạo/xóa Run hoặc gọi model thật. Script `node-task.cjs` được đồng bộ bỏ bước quản lý Team; không chạy lại toàn bộ probe đó trong task này.
    - `node openapi/sync-local-ui.cjs`, `node openapi/check-contract.cjs`: **94 schemas, 74 paths, 98 operations** đạt.
    - Đã nạp Server local khi không có Run chưa kết thúc; health schema 18 đạt, GET Project thật trả Team khử trùng. Không thay cấu hình node/PM hoặc tạo Run trên dữ liệu người dùng.
  - Giới hạn: thay đổi graph chưa Lưu draft chưa phải phân công trên Server. Việc xóa Agent vẫn kiểm mọi ProcessVersion còn tham chiếu để giữ cấu hình lịch sử, độc lập với Team hiện tại.
