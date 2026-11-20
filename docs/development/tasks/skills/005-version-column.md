# Cột Version trong danh mục Skills

[Module](README.md) · [Requirements](../../../product/requirements.md#quản-lý-agents-skills-và-tools-qua-giao-diện)

## SKL-006

- [x] **SKL-006 — Hiển thị bản Published và draft ngay trong bảng** — Xong | UX
  - Theo yêu cầu sau khi Skill Global không hiện trong node vì chỉ có draft: thêm cột Version, không đổi quy tắc Publish hoặc tự publish Skill.
  - Không có version: Chưa có version. Chỉ có draft: Chưa Publish và Draft vN. Có published: vN · Published; nếu có draft mới hơn, hiển thị Draft vM riêng. Đây là bản sẵn dùng khi cấu hình Process mới, không khẳng định mọi Process/Run cũ dùng cùng bản.
  - Server bổ sung metadata nullable `published_version_number`, `latest_version_number`, `latest_version_status` vào Skill list/detail qua `_scope`, giữ source_path/source_runner_id hiện hành. Không migration, không đọc/upload file Skill. OpenAPI description và generator đồng bộ.
  - Versions modal gọi reload danh mục sau khi lưu/publish, cột cập nhật ngay, giữ component tìm kiếm/bộ lọc hiện tại.
  - Code: SkillRepository, Skills API, `Skills.tsx`, `sync-local-ui.cjs`. Regression: `test_skill_version_summary.py`, `tests/browser/skill-versions.cjs`.
  - Kiểm chứng 2026-11-19: suite summary + settings/skills/agents + project scope + skill file API: **22 passed**. Web **21 passed**, TypeScript/Vite build đạt. Browser Skill versions: **passed**, đủ bốn trạng thái và tự reload sau Publish bằng fixture API; không publish Skill thật. OpenAPI **94 schemas, 74 paths, 98 operations** đạt.

> Cập nhật 2026-11-19: yêu cầu cột Version trên Skill được thay bằng luồng Lưu dùng ngay của [BASE-009](../base/008-save-and-run.md); nội dung phía trên là bằng chứng triển khai trước đó.
