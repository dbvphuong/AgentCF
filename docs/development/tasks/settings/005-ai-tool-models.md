# Agent điều phối và model công cụ AI trên PC

[Module](README.md) · [Glossary](../../../product/glossary.md#agent) · [Requirements](../../../product/requirements.md#settings-và-cấu-hình-model) · [ADR 0007](../../../architecture/decisions/0007-orchestration-agents-and-ai-tools.md)

## SET-005

- [x] **SET-005 — Tách tên gọi và model API/CLI** — Xong | Feature/Fix
  - Nguồn: người dùng chốt Agent API chỉ giao việc cho Codex/Antigravity và kiểm tra tiến độ, lỗi, kết quả thay người. CLI trực tiếp làm Skill/tool/file trên PC. Cần Settings sửa danh sách model thường dùng của từng công cụ.
  - UI: Agent điều phối / Công cụ AI thực thi / Model thực thi. Settings tách Providers & Models API (hai tab Providers API, Models API) và Công cụ AI trên PC. Bảng quản lý gom gọn chính xác 2 dòng tương ứng với 2 công cụ thực thi trên PC (`Codex CLI` và `Antigravity`), không hiển thị tràn lan hàng chục dòng model làm rối người dùng. Bấm "Chọn model" mở modal checklist đa chọn (multi-select) danh sách toàn bộ model của công cụ; có nút "Chọn tất cả" / "Bỏ chọn tất cả", tìm kiếm nhanh và thêm model tùy biến. Tích chọn model nào thì chỉ model đó xuất hiện trong dropdown cấu hình node ở Process Editor (`status = 'active'`), các model không tích sẽ được ẩn đi (`status = 'disabled'`), giúp giao diện thiết kế quy trình luôn gọn gàng và tiện lợi. Bảng chính hiển thị rõ tóm tắt số lượng và danh sách model đang được bật.
  - Bổ sung model đầy đủ và đồng bộ tiện lợi:
    - Bổ sung toàn bộ dòng GPT-6 series (`gpt-6.1-sol`, `gpt-6.1-terra`, `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`) và GPT-5 series cho Codex CLI, Claude Sonnet/Opus 4.6 (Thinking), Gemini 4 series cho Antigravity.
    - Cung cấp API cấu hình hàng loạt `/v1/settings/ai-tool-models/configure` lưu nguyên tử trạng thái kích hoạt/vô hiệu hóa các model được tích chọn.
    - Nút "Cập nhật model mới nhất" gọi API `/v1/settings/ai-tool-models/sync`, một chạm cập nhật và nạp toàn bộ danh mục model mới nhất (bao gồm tự động phát hiện model từ cache local của Codex `~/.codex/models_cache.json`) mà không phải sửa tay.
    - Nút "Kiểm tra công cụ PC" gọi API `/v1/settings/ai-tool-models/check`, chẩn đoán kiểm tra trực tiếp trạng thái cài đặt, phiên bản và mức độ sẵn sàng của Codex CLI và Antigravity trên PC.
  - Migration 015 & 016: ai_tool_models độc lập, mỗi tool + Model ID duy nhất. Khởi tạo và nạp đầy đủ danh mục 20+ model cho Codex CLI và Antigravity.
  - API CRUD `/v1/settings/ai-tool-models`, batch configure `/v1/settings/ai-tool-models/configure`, sync `/v1/settings/ai-tool-models/sync`, check `/v1/settings/ai-tool-models/check`. Lọc tool/status, validation, audit. Không chuyển model sang công cụ khác; xóa model đang được version tham chiếu bị chặn, tắt sử dụng vẫn giữ lịch sử.
  - Publish kiểm tool_model_id/adapter/exact identifier và active; lưu tool_model_snapshot. Graph cũ resolve exact ID trong chính catalog CLI hoặc lỗi rõ, không fallback API. Tắt model chặn Run mới. Published snapshot giữ model cũ khi sửa catalog.
  - CF Client chọn adapter đúng theo cấu hình; AntigravityAdapter ánh xạ đầy đủ định danh các model Claude và Gemini.

### Kiểm chứng 2026-11-18

- Code: `api/ai_tool_models.py`, `infrastructure/settings/ai_tool_models.py`, migrations 015 & 016, ProjectManagement/RunRepository; Web `AiTools.tsx`, NodeForm/ProcessEditor; Client `antigravity_adapter.py`.
- `.venv/Scripts/python.exe -m pytest -q`: **226 passed, 1 skipped**.
- Kiểm tra thực tế trên PC:
  - Codex CLI: `codex-cli 0.147.0` phát hiện sẵn sàng; chạy thử thực tế (smoke test) với `gpt-5.6-sol` và `gpt-5.6-terra` đều đạt 100% cả lượt chạy Skill và lượt phục hồi ngữ cảnh resume turn.
  - Antigravity: `agy.exe 1.0.6` phát hiện sẵn sàng; danh mục model và mapping đã được đồng bộ chuẩn xác.
- Web: `npm.cmd test`: **19 passed**; `npm.cmd run build`: Vite & TypeScript build thành công 0 lỗi.
- Hợp đồng OpenAPI: `node openapi/check-contract.cjs`: **90 schemas, 69 paths, 93 operations** đạt chuẩn.
- Database local: Đã chạy migration 016 trên `runtime/server/agent_cf.sqlite3`, nạp đầy đủ model cho cả hai công cụ.

### Giới hạn phạm vi

SET-005 là thay đổi cấu hình, danh mục model và ranh giới model công cụ thực thi trên PC. Worker hiện truyền instruction sang CLI và review có bộ tiêu chí xác định; chưa có vòng LLM API điều phối tổng quát tự giao việc/kiểm tra/ra chỉ đạo sửa. Không dùng kết quả trên để đóng RTM-008 hoặc tuyên bố Agent API đã điều khiển CLI thật. Khoảng trống được ghi ở [RTM-008](../runtime/005-generic-snapshot-execution.md).
