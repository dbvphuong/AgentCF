# Luồng Skill 0 → 1 → 2

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## RUN-007

- [x] **RUN-007 — Luồng cố định Skill 0 → 1 → 2** — Xong | Feature
  - Phụ thuộc: [RUN-006](003-skill0-web.md#run-006), [AGN-002](../agents/001-agent-review.md#agn-002), [RTM-007](../runtime/004-review-search.md#rtm-007).
  - Nghiệm thu: truyền đúng artifact; Skill 1 viết từng Part và chờ Agent duyệt trước khi tiếp; Skill 2 giữ bản trước/sau cùng báo cáo. Không cần đợi editor để thử mẫu có version; lỗi chặn đúng downstream, không tự chạy lại phần đã đạt.
  - Bằng chứng thực hiện:
    - `TaskExecutionWorker` trong `apps/client/src/agent_cf_client/execution/task_worker.py` điều phối chuỗi Skill 0 → Skill 1 → Skill 2:
      - Skill 0 (`0.tao_cot_truyen`): Tạo và upload `cot truyen.txt`.
      - Skill 1 (`1.tao_noi_dung`): Tải `cot truyen.txt` từ server, sinh nội dung, gọi review evaluation theo tiêu chí, lưu checkpoint artifact theo vòng (`noi dung_round_{round}.txt`), ghi nhận quyết định duyệt `POST /v1/task-runs/{id}/reviews`, xuất bản `noi dung.txt` khi đạt duyệt; nếu vượt `max_revisions` thì dừng ngay lập tức và đánh dấu thất bại.
      - Skill 2 (`2.review_noi_dung`): Tải `noi dung.txt`, thực hiện tra cứu web thực tế qua `ReviewSearchCapability` (RTM-007), làm sạch tạp chất (zero-clutter, loại bỏ phân đoạn), ngắt dòng chuẩn TTS ElevenLabs (≤ 500 ký tự/dòng), xuất bản `noi dung_reviewed.txt` và `audit_report.md` (chấm điểm trước/sau và nguồn trích dẫn), bảo toàn bản gốc `noi dung.txt`.
      - Chặn downstream (Failure Isolation): Khi Skill 1 thất bại, server tự động đánh dấu Skill 2 là `skipped`, bảo toàn nguyên vẹn kết quả và artifact của Skill 0.
    - Test kiểm chứng: 4/4 test trong `apps/server/tests/integration/runs/test_skill_chain_review.py` đạt pass 100%.
