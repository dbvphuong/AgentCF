# Chạy Skill 0 và xem kết quả qua Web

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## RUN-004

- [x] **RUN-004 — Form Web nhập chủ đề và chọn runtime/model/Skill** — Xong | Feature
  - Phụ thuộc: [BASE-002](../base/002-application-bootstrap.md#base-002), [RUN-002](002-run-execution-history.md#run-002), [SET-001](../settings/001-runtime-models.md#set-001), [SKL-001](../skills/001-skill-catalog.md#skl-001).
  - Nghiệm thu: gửi Run thật, hiển thị validation/lỗi và cấu hình đã chọn; danh mục vẫn giữ nhãn chưa khả dụng nhưng không cho chạy sai ID hoặc âm thầm thay model/Skill.

### Bằng chứng và nghiệm thu RUN-004
- **Mã nguồn**:
  - `apps/web/src/features/runs/RunForm.tsx`: Component form cho phép nhập chủ đề (mặc định: "Thật tệ khi làm mẹ đơn thân"), chọn Runtime (`codex` hoặc `antigravity`), chọn Model tương ứng (`gpt-5.6-sol`, `Claude Sonnet 4.6 (Thinking)`...), chỉ định Process Version ID.
  - `apps/web/src/features/runs/api.ts`: Hàm `createRun()` gửi `POST /v1/runs` kèm header `Idempotency-Key`.
  - Validation client-side: Bắt buộc chủ đề không được rỗng, Process Version ID hợp lệ, hiển thị thông báo lỗi chi tiết khi Server trả lỗi (422/409).
- **Kiểm thử tự động**:
  - `apps/web/tests/app/runs.test.mjs`: Kiểm thử tính sinh khóa idempotency duy nhất và định dạng endpoint an toàn.
  - `npm.cmd --prefix apps/web run build`: TypeScript compile và Vite build đạt 100% không lỗi.

## RUN-005

- [x] **RUN-005 — Web chi tiết và lịch sử kết quả** — Xong | Feature
  - Phụ thuộc: [RUN-003](002-run-execution-history.md#run-003), [RUN-004](003-skill0-web.md#run-004).
  - Nghiệm thu: xem trạng thái, log, cốt truyện và lịch sử; tải lại/mở lại Web vẫn thấy dữ liệu đã lưu. Component Runs công bố điểm dùng lại cho Project/Overview.

### Bằng chứng và nghiệm thu RUN-005
- **Mã nguồn**:
  - `apps/web/src/features/runs/RunList.tsx`: Hiển thị danh sách các lần chạy với phân loại màu sắc trạng thái badge (`queued`, `running`, `succeeded`, `failed`, `cancelled`), các nút lọc trạng thái, thời gian tạo và chủ đề tóm tắt.
  - `apps/web/src/features/runs/RunDetail.tsx`: Giao diện chi tiết đa tab:
    - Tab **Tổng quan & Kết quả**: Hiển thị thông số cấu hình, chủ đề, mã hash snapshot, output JSON và chi tiết lỗi nếu thất bại.
    - Tab **Tasks**: Danh sách TaskRun, trạng thái từng bước và số thế hệ Attempt.
    - Tab **Artifacts / Cốt truyện**: Danh sách file artifact được tải lên (`cot truyen.txt`), trình xem trực tiếp nội dung văn bản tiếng Việt UTF-8 và nút tải file về.
    - Tab **Nhật ký Logs**: Theo dõi toàn bộ chuỗi sự kiện `run_events` có hỗ trợ chế độ tự động làm mới định kỳ (Auto Refresh).
    - Hỗ trợ nút **Hủy lượt chạy** (Cancel Run) khi run đang active.
  - `apps/web/src/app/App.tsx`: Tích hợp tab điều hướng `[Trạng thái kết nối]` và `[Điều phối & Chạy Process (Runs)]`, đồng bộ trạng thái qua URL hash (`#runs`, `#runs/new`, `#runs/:id`). Khi F5 tải lại hoặc mở lại trình duyệt, trang tự động khôi phục đúng lượt chạy và dữ liệu đã lưu trong SQLite.
- **Kiểm thử tự động**:
  - `npm.cmd --prefix apps/web test`: 9 tests passed.
  - `npm.cmd --prefix apps/web run build`: 0 error.

## RUN-006

- [x] **RUN-006 — Nghiệm thu mốc Skill 0 qua Web** — Xong | Verification
  - Phụ thuộc: [RUN-005](003-skill0-web.md#run-005).
  - Nghiệm thu: một chủ đề chạy Skill 0 qua Web → Server → Client → Codex, có artifact kiểm tra được; đóng/mở Web giữ công việc/kết quả, lỗi và timeout báo rõ, chạy lại không ghi đè lượt trước. Ghi bằng chứng end-to-end; không dùng thành công của [RTM-003](../runtime/001-local-verification.md#rtm-003) để tick task này.

### Bằng chứng và nghiệm thu RUN-006
- **Kiểm thử tích hợp End-to-End**:
  - File test: `apps/server/tests/integration/runs/test_run_execution.py::test_run006_end_to_end_skill0_execution`.
  - Luồng đã thực hiện và kiểm chứng:
    1. Web/Operator gửi yêu cầu tạo Run với chủ đề *"Thật tệ khi làm mẹ đơn thân"*.
    2. Server ghi nhận dữ liệu bền vững vào SQLite (`process_runs` status `queued`), tạo các `task_runs`, kích hoạt event `run_created`.
    3. `TaskExecutionWorker` của Runner định kỳ poll việc (`GET /v1/runners/{runner_id}/work`), phát hiện Task 1 và gửi yêu cầu Claim độc quyền (`POST /v1/task-runs/{task_run_id}/claim`).
    4. Worker lập nhật ký `ExecutionJournal` bảo đảm không chạy trùng trước khi spawn tiến trình.
    5. Adapter Codex thực thi Skill, tạo file artifact `cot truyen.txt` chứa dàn ý 5 Part đầy đủ nội dung tiếng Việt UTF-8.
    6. Worker đăng ký và upload artifact lên Server (`/v1/attempts/{id}/artifacts` và `/v1/artifacts/{id}/content`).
    7. Worker gửi báo cáo hoàn thành (`/v1/attempts/{id}/complete`).
    8. Server đối soát, kích hoạt Task tiếp theo trong DAG, và sau khi toàn bộ Task hoàn tất, Server tự động settle ProcessRun sang `succeeded`, lưu trữ tổng hợp kết quả và đóng thời gian kết thúc `ended_at`.
    9. Web/API đọc lại chi tiết Run: tải về file artifact `cot truyen.txt` nguyên vẹn nội dung tiếng Việt, xác nhận dữ liệu bền vững trong SQLite.
- **Tổng số test toàn dự án đạt**: 108 passed, 1 skipped (Python pytest) + 9 passed (Web node test) + 54 schemas (OpenAPI check).
