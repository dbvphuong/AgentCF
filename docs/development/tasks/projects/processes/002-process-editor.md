# Editor, validate và publish Process

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../../README.md) · [Kế hoạch tổng](../../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## PROC-002

- [x] **PROC-002 — Editor kéo thả và cấu hình từng node** — Xong (local UI/API) | Feature
  - Phụ thuộc: [PROC-001](001-process-definition.md#proc-001), [RUN-006](../../runs/003-skill0-web.md#run-006), [SET-001](../../settings/001-runtime-models.md#set-001), [SKL-001](../../skills/001-skill-catalog.md#skl-001).
  - Nghiệm thu: thêm/nối/sửa node, chọn Agent/runtime/model/Skill/input; lưu draft và báo cấu hình chưa hợp lệ. Không mặc nhiên mở menu Processes độc lập.
  - Bằng chứng 2026-11-17: `features/projects/processes/ProcessEditor.tsx`, API draft và migration 010. Palette Agent/Robot, kéo node, dependency tùy ý, inspector, cấu hình model từ Agent (không đoán ID), Skill/RobotVersion/PC, schema/mapping JSON. Lưu draft CAS, cảnh báo thay đổi chưa lưu. Browser smoke tạo node, kéo/lưu/publish/reload; kiểm tra editor mobile không tràn trang. [Báo cáo](../../../../reports/ui-completion-check.md).

## PROC-003

- [ ] **PROC-003 — Validate, publish và version hóa thay đổi graph** — Đang làm (đã có UI/API, chưa đủ thiết kế nền) | Feature
  - Phụ thuộc: [PROC-002](002-process-editor.md#proc-002).
  - Nghiệm thu: kiểm tra dependency/cycle, quyền và cấu hình; version published bất biến, sửa tạo draft, Run cũ giữ snapshot; có test version và graph không hợp lệ.
  - Đã đạt 2026-11-17: UI Validate/Publish và API transactional; kiểm tra ID/key/dependency/cycle, Agent thuộc Team, model exact, Skill/Tool active và allowlist, RobotVersion published/PC, mapping lấy từ tổ tiên; đóng băng snapshot và trigger published bất biến, draft tiếp theo không đổi version cũ. Regression graph sai/CAS/model/team/mapping và Run ghim version đã chạy đạt.
  - Chưa đạt: kiểm chứng đầy đủ JSON Schema, canonical fingerprint RFC8785 và bundle delivery/verification theo ADR 0005; remote operator auth/idempotency tạo mới chưa hoàn tất. Mapping runtime và worker generic theo RUN-008/RTM-008. Không đánh dấu toàn bộ task/menu xong chỉ vì UI publish đã hoạt động. [Báo cáo và lệnh](../../../../reports/ui-completion-check.md).
