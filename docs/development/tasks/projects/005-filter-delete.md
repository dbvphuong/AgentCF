# Bộ lọc Tất cả và xóa Project có Skill liên kết

[Module](README.md) · [Requirements](../../../product/requirements.md#quản-lý-project-và-process-qua-giao-diện)

## PROJ-005

Quy tắc Delete có published/lịch sử được thay bởi [PROJ-007](007-permanent-deletion.md). Nội dung dưới ghi bằng chứng tại thời điểm sửa lỗi liên kết Skill.

- [x] **PROJ-005 — Thêm Tất cả và sửa lỗi khóa ngoại khi xóa Project** — Xong | Bug/Feature
  - Phụ thuộc: PROJ-003, SKL-004. Thêm Tất cả vào bộ lọc, giữ mặc định Đang hoạt động; tìm kiếm kết hợp cả ba lựa chọn.
  - Nguyên nhân: `skill_projects.project_id` chặn xóa Project chưa có lịch sử. Gỡ membership trong transaction xóa; không xóa Skill/version/file, không mở rộng thành Global và không gỡ liên kết với Project khác. Skill không còn Project được gán lại qua form sửa. Project có version published/Run vẫn giữ quy tắc bảo toàn lịch sử; Run chưa kết thúc vẫn chặn xóa.
  - Code: `ProjectList.tsx`, `filterProjects.ts`, `infrastructure/projects/management.py`; không đổi API/schema/migration và không xóa Project thật để thử.
  - Kiểm chứng 2026-11-19: `.venv/Scripts/python.exe -m pytest apps/server/tests/integration/projects -q`: **42 passed**; `npm.cmd --prefix apps/web test`: **21 passed**; `npm.cmd --prefix apps/web run build`: TypeScript/Vite đạt. Regression backend kiểm Project có Skill riêng/chung, giữ version Skill và phạm vi, gán lại Skill và giữ membership khi Project chỉ chuyển Không hoạt động.
