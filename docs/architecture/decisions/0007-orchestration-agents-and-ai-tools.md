# 0007 - Tách Agent điều phối API và công cụ AI thực thi trên PC

- Status: Accepted
- Date: 2026-11-18

## Context

Người dùng chốt hai vai trò: Agent API thay người giao việc và kiểm tra tiến độ/lỗi/chất lượng; Codex CLI và Antigravity trực tiếp thực hiện Skill trên PC. Dùng chung từ Agent và danh mục model khiến form chọn Antigravity hiện model API/Codex. Trường runtime_adapter trên model API ở migration 014 không mô tả đúng hai vai trò này.

## Decision

- Tên giao diện: **Agent điều phối**, **Công cụ AI thực thi**, **Model thực thi**. Settings tách **Providers & Models API** và **Công cụ AI trên PC**. Tên kỹ thuật Agent/runtime/adapter và ID/API cũ giữ tương thích.
- Agent tham chiếu `models`/`providers` để cấu hình model API điều phối. Mỗi node giữ công cụ thực thi (`runtime.adapter`) và lựa chọn model CLI riêng (`runtime.tool_model_id`, `runtime.model_id`). Không suy model CLI từ Agent/model API/provider hoặc tên model.
- Migration 015 tạo `ai_tool_models` riêng, ràng buộc công cụ Codex/Antigravity, tên, Model ID và bật/tắt. Mỗi công cụ chỉ hiện model đã bật thuộc nó. Model ID trùng giữa hai công cụ vẫn là hai cấu hình độc lập. Không tự sao chép model API sang CLI.
- Publish kiểm tool/model/identifier và đóng băng tên/ID trong snapshot. Sửa catalog không sửa snapshot cũ; tắt model chặn publish/Run mới liên quan, không hủy run đang chạy. Model đã được Process tham chiếu không bị xóa.
- Graph cũ chỉ có exact model_id có thể resolve trong catalog CLI của chính adapter; không dùng API làm fallback. Nếu chưa có model CLI tương ứng phải thêm/chọn lại trước publish mới. Published version/lịch sử đã có không bị viết lại.
- Migration 014 và API field runtime_adapter cũ giữ tương thích, đánh dấu deprecated, bỏ khỏi UI API model và không dùng để chọn model thực thi.
- Khởi tạo một model cho mỗi công cụ từ cấu hình adapter đã kiểm chứng trong repo: Codex GPT-5.6-Sol, Antigravity Claude Sonnet 4.6 (Thinking). Đây là mặc định có thể sửa/tắt; không bảo đảm entitlement hoặc CLI đã cài trên PC bất kỳ. Không nhập các ID chưa xác định từ inventory tham chiếu.

## Consequences

- Người dùng thêm/sửa danh sách model thường dùng trong Settings, không sửa code hoặc cấu hình Agent API để thay model CLI.
- Đổi Agent điều phối không đổi công cụ/model CLI. CF Client chọn adapter chính xác theo cấu hình, không suy từ chữ Gemini/provider.
- Quy trình Skill và file/ref/output trên PC giữ nguyên theo ADR 0006.
- Task SET-005 triển khai tên gọi, catalog, UI, validation và dispatch adapter. Không chứng minh hoặc bổ sung vòng LLM gọi API tự giao việc/duyệt. Review hiện có tiêu chí xác định; việc gọi model API để điều phối tổng quát còn cần triển khai/kiểm chứng riêng. Không dùng catalog hoặc test fixture để tuyên bố vòng đó đã chạy thật.

## Alternatives considered

- Chung model API và CLI kèm trường Runtime nullable: đã gây lẫn loại model, không dùng tiếp cho lựa chọn mới.
- Tự suy model/công cụ từ tên Agent/provider: không đáng tin và có thể gọi sai công cụ.
- Đưa toàn bộ inventory vào lựa chọn: có ID chưa biết và model không dùng thường xuyên; chọn catalog nhỏ do người vận hành quản lý.
