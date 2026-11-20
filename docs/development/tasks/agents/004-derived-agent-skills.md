# Bỏ gán cứng Skill cho Agent và hiển thị Skill đang dùng

> Last updated: 2026-11-19

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

## AGN-005

- [x] **AGN-005 — Bỏ gán cứng Skill cho Agent; Cột Skills ở Agent điều phối hiển thị các Skill đang được dùng từ Process; Bỏ chặn Validate/Publish Process** — Xong | Behavior/UX
  - Theo yêu cầu: Agent là một người (nhân sự) có thể làm nhiều việc; Skill là một việc. Trong một Process, việc chọn Agent A và Skill X nghĩa là Agent A làm việc X trong Process đó; ở Process khác có thể phân công Agent A làm Skill khác.
  - Không gán cứng Skill vào Agent ở cấp catalog; bỏ ô chọn `Skills` trong form tạo/sửa Agent tại menu **Agent điều phối**.
  - Cột `Skills` trên bảng Agent điều phối chuyển thành view hiển thị (chỉ đọc) các Skill mà Agent đó đang phụ trách trong phiên bản mới nhất đã lưu của các Process.
  - Phía Server: Bỏ kiểm tra `Skill chưa được gán cho Agent` khi Validate và Publish Process. Mọi Agent active đều có thể nhận bất kỳ Skill hợp lệ nào trong phạm vi Project/Global.
  - Backend `list_agents` và `get_agent` tự động trích xuất các `skill_ids` đang được sử dụng từ `tasks` của phiên bản Process mới nhất, hợp nhất tương thích với dữ liệu cũ nếu có.
  - Gợi ý trong `NodeForm` của Process bỏ câu nhắc gán Skill cho Agent.
  - Kiểm chứng 2026-11-19:
    - `npm.cmd --prefix apps/web test`: **21 passed**.
    - `npm.cmd --prefix apps/web run build`: TypeScript/Vite build thành công.
    - `.venv\Scripts\pytest.exe apps/server/tests/integration/settings_skills_agents/`: **11 passed**.
    - `.venv\Scripts\pytest.exe apps/server/tests/integration/projects/`: **69 passed**.
    - `node openapi/check-contract.cjs`: **94 schemas, 76 paths, 100 operations** hợp lệ.
