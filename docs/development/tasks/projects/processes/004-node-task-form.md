# Form node, Nhiệm vụ và Model theo Runtime

Phần gán Runtime trên model API và lấy model CLI mặc định từ Agent của PROC-005 được thay bằng [SET-005](../../settings/005-ai-tool-models.md) và ADR 0007: Agent dùng Model API, công cụ AI dùng danh mục CLI riêng. Bằng chứng dưới đây giữ theo thời điểm triển khai ban đầu, không mô tả lựa chọn model hiện tại.

[Module](README.md) · [Requirements](../../../../product/requirements.md#cấu-hình-node-dùng-runtime-local)

## PROC-005

Phần quản lý Team thủ công đã bỏ tại [PROJ-009](../009-derived-team.md). Node chọn Agent trực tiếp, Team tự tổng hợp; bằng chứng bên dưới giữ theo thời điểm triển khai ban đầu.

- [x] **PROC-005 — Form node cho luồng nhập prompt ngôn ngữ tự nhiên** — Xong | Feature
  - Phụ thuộc: PROC-002/003, SET-001/002, SKL-005.
  - Form chính: Tên bước, Agent thuộc Team, Skill, Runtime, Model, Nhiệm vụ, PC và thư mục làm việc. Task key tự sinh bằng ID node và giữ nguyên khi sửa; trường kỹ thuật vào Cấu hình nâng cao mặc định đóng.
  - Nhiệm vụ vẫn lưu bằng `instructions`, truyền nguyên văn tới CLI; không tạo DSL, parser prompt hay điều kiện thành công dựa trên từ `done`. Đã có trên đường chạy Skill local; bổ sung vào request của nhánh Skill 0 inline cũ để không bỏ mất prompt.
  - Quản lý Team ngay trong modal, liệt kê Agent active; chỉ thay Team sau khi người dùng Lưu, không tự thêm Agent ngoài Team. Giữ quy tắc không bỏ PM/Agent đã được gán. Editor đọc Team mới sau khi lưu, không chỉ dùng prop cũ.
  - Migration 014 thêm `models.runtime_adapter` nullable. Settings Models có trường/cột Runtime; để trống tương thích model cũ. Không đoán từ tên hoặc dùng inventory tham chiếu làm bảo đảm quyền tài khoản. UI lọc theo Runtime đã gán, hiện nhãn model chưa gán; đổi Runtime xóa lựa chọn Model cũ để chọn lại.
  - Node lưu catalog_model_id và exact model_id; Server kiểm active Model/provider và runtime binding, giữ model mặc định Agent. Graph cũ không có catalog_model_id tiếp tục dùng mặc định Agent. Published snapshot không đổi khi sửa catalog.
  - PC mặc định từ version Skill published, không lấy source của draft mới. Bảo vệ PC/Workspace/Skill/Tool tại Server giữ nguyên. Việc chọn Model không tự cài CLI hay kiểm chứng mọi Model trên tài khoản.

### Code và kiểm chứng 2026-11-18

- Web: `features/projects/processes/NodeForm.tsx`, `ProcessEditor.tsx`, Settings Models; shared EntityForm hỗ trợ options động, cập nhật giá trị phụ thuộc và phần nâng cao.
- Server: API/repository Settings, migration 014, validation graph và snapshot trong ProjectManagement. Client: đưa Nhiệm vụ vào request Skill 0 inline, test Skill local cũng kiểm prompt nguyên văn.
- `.venv/Scripts/python.exe -m pytest -q`: **220 passed, 1 skipped**. Regression mới tại `integration/projects/test_node_task_form.py`: override model không sửa Agent, prompt `done`, published bất biến, từ chối runtime/identifier sai hoặc Model/provider tắt, preserve/clear runtime binding. Migration/persistence đạt.
- `npm.cmd test`: **19 passed**; `npm.cmd run build`: TypeScript và Vite đạt. `node openapi/check-contract.cjs`: **87 schemas, 64 paths, 85 operations** đạt.
- `apps/web/tests/browser/node-task.cjs`: **passed** trên DB riêng Server 18089/Web 5189/Edge CDP 9351. Thêm Writer ngoài PM vào Team, nhận mặc định Model từ Agent, chọn Skill tự điền PC, đổi Runtime sang Antigravity lọc/reset Model, nhập `done`, lưu/validate/publish; sửa draft giữ task key/Model, đổi Timeout nâng cao, version published giữ nguyên. Không tạo Run hay gọi model.
- Smoke tổng cập nhật Tên bước và bỏ nhập Task key; không chạy lại toàn bộ browser smoke trong task này. Test browser hiện tại và Python dùng fixture; không coi là nghiệm thu mọi Model/CLI thực tế.
- Server local 8000 đã nạp migration 014, health đạt; Client demo hiện có được nạp lại code từ manifest cũ, không chạy setup/model. Kiểm tra trước/sau giữ identity/model mặc định Agent, Model identifier, PC và Run history; model cũ có runtime_adapter null, không tự gán Runtime.
