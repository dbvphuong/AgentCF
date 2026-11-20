# Skill theo nhiều Project hoặc Global

[Module](README.md) · [Requirements](../../../product/requirements.md#quản-lý-agents-skills-và-tools-qua-giao-diện)

## SKL-004

- [x] **SKL-004 — Phạm vi Skill theo Project/Global** — Xong | Feature
  - Người dùng chốt không tạo nhóm Skill. Một Skill được dùng tại nhiều Project hoặc Global; tạo/sửa dùng tích chọn nhiều, Global loại trừ các lựa chọn Project cụ thể. Bắt buộc ít nhất một lựa chọn.
  - Phụ thuộc: SKL-001/003, PROJ-001, PROC-003.
  - Phạm vi: migration quan hệ nhiều-nhiều, CRUD/list API, cột/lọc Project trong Skills, danh sách Skill của Process chỉ có Skill thuộc Project và Global, backend kiểm publish/start. Tạo Skill trong node editor chọn sẵn Project hiện tại.
  - Skill trước migration giữ Global để tương thích dữ liệu cũ; không sửa version hoặc lịch sử. Scope là cấu hình sử dụng hiện tại; thu hẹp scope chặn publish/Run mới, không sửa Run đã có. Nhân bản Project thêm liên kết với Skill riêng của nguồn, không nhân đôi Skill/version.
  - Nghiệm thu: tạo một Skill cho A/B, C không chọn được; Global dùng mọi Project; Global không trộn Project, không cho lựa chọn rỗng/Project không tồn tại; edit/read/restart giữ liên kết; publish/Run không vượt scope; UI tích chọn không cần Ctrl; lịch sử và dữ liệu cũ giữ nguyên.

### Bàn giao 2026-11-18

- Code: migration 012, `domain/skills/project_scope.py`, API/repository/access của Skills; publish/clone trong Projects, start trong Runs; `Skills.tsx`, `projectScope.ts`, `NewProjectSkill.tsx`, ProcessEditor và checklist/extension của shared EntityForm/Catalog. Không thay cách thực thi Skill hoặc output trên PC.
- Scope được lưu dạng `is_global` + bảng `skill_projects`; API create và import yêu cầu chọn rõ phạm vi. PATCH có thể bỏ scope để giữ nguyên khi chỉ đổi tên/mô tả. Thay scope có audit; Project còn Skill tham chiếu không xóa vật lý được trước khi chuyển phạm vi.
- `.venv/Scripts/python.exe -m pytest -q`: **194 passed, 1 skipped**, hai cảnh báo deprecation FastAPI/Starlette. Sau bổ sung regression nâng cấp Skill cũ, chạy riêng `test_sqlite_foundation.py`: **25 passed**. Test `test_skill_project_scope.py` kiểm chọn nhiều, Global, scope rỗng/trộn/Project không tồn tại, rollback, filter, chặn publish/Run mới, lịch sử không đổi và clone không nhân đôi Skill.
- Web `typecheck`, `test` (**19 passed**) và `build` đạt. OpenAPI: **80 schemas, 58 paths, 74 operations**, 20 schema cases/5 graph cases đạt; thêm/cập nhật CRUD/filter/import và Skill scope response.
- Edge headless/CDP trên **DB/Server/Vite thử riêng**, không gọi runtime: checkbox nhiều lựa chọn/Global loại trừ, bắt buộc chọn, lưu/sửa và đọc lại hai Project, cột Project, filter, dropdown Skill trong editor và form tạo từ Project chọn sẵn đều đạt; không JavaScript exception. Ảnh/kết quả local tại `runtime/skill-project-scope/{scope-checkboxes.png,scope-column.png,project-default.png,ui-result.json}`.
- Đã restart Server local, áp dụng schema 12 và đối chiếu danh sách Skill/lịch sử Run trước/sau: ID/count giữ nguyên, Skill cũ là Global, trạng thái Run không đổi. Bằng chứng `live-before.json`/`live-after.json` ngoài Git. PC demo được mở lại, không tạo lượt chạy/model call mới.

### Giới hạn

Phạm vi là cấu hình dùng Skill trong Project, không thay thế xác thực operator từ xa. Global không tự chuyển file Skill hoặc môi trường/tool giữa PC. Đường dẫn Skill vẫn thuộc version local đã chọn; task này không di chuyển cấu hình file từ form Versions sang form metadata.
