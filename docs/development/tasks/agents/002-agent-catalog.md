# Menu quản lý Agent

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## AGN-003

- [x] **AGN-003 — Menu quản lý Agent** — Xong | Feature
  - Phụ thuộc: [DATA-001](../data/001-sqlite-persistence.md#data-001), [SET-002](../settings/002-general-configuration.md#set-002).
  - Nghiệm thu: CRUD/archive, Role/model/Skill/allowed Tool theo spec; giữ identity và snapshot đang được Run dùng. Tách task nhỏ trước khi giao; không bịa token usage hoặc chất lượng.
  - Bằng chứng 2026-11-16: `AgentRepository` (`apps/server/src/agent_cf_server/infrastructure/agents/repository.py`), API router `/v1/agents`. Hỗ trợ CRUD Agent, liên kết Role/Model/Skills/Allowed Tools; kiểm tra chặt chẽ quy tắc nghiệp vụ: Agent không được gán Skill đòi hỏi Tool nằm ngoài danh sách Allowed Tools của Agent. Hỗ trợ tạo Agent Snapshot bất biến với SHA-256 phục vụ Run, Archive/Restore Agent. Đã kiểm thử tự động tại `test_settings_skills_agents.py`.
