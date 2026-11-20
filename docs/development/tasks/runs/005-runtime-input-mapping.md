# Giải quyết mapping của graph tại runtime

[Module](README.md) · [Bằng chứng review](../../../reports/ui-completion-check.md#giới-hạn-nghiệm-thu)

## RUN-008

- [ ] **RUN-008 — Áp dụng input mapping và JSON Schema trước giao TaskRun** — Chưa làm | Fix
  - Nguồn: [mapping](../../../architecture/domain-model.md#định-nghĩa-process-động-và-snapshot), [execution](../../../architecture/execution-model.md), `Binding` trong OpenAPI.
  - Phụ thuộc: PROC-003, RUN-002.
  - Phát hiện: `RunRepository.claim_task_run` hiện lấy `task_runs.input_json` hoặc toàn bộ `run_input_json`, chưa giải quyết đầy đủ binding từ literal/run_input/task_output trong graph do editor lưu.
  - Nghiệm thu: RFC6901 gồm escape và null tồn tại, missing pointer là lỗi, chỉ lấy output tổ tiên, input required/default và schema validation, artifact reference được phép; test graph nhiều nhánh, không giao runtime khi input sai, giữ nguyên snapshot/Run cũ. Không đánh dấu xong bằng việc Web lưu JSON thành công.
