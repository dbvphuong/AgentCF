# Agent giao việc, duyệt và yêu cầu sửa

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## AGN-001

- [x] **AGN-001 — Thiết kế tiêu chí duyệt và giới hạn yêu cầu sửa** — Xong | Design
  - Phụ thuộc: [RUN-006](../runs/003-skill0-web.md#run-006).
  - Nghiệm thu: nguồn spec ghi tiêu chí đạt/chưa đạt cho output, dữ liệu quyết định, số lần sửa và quyền của Agent; chỉ báo người dùng khi vượt khả năng/giới hạn. Làm rõ cách thực thi phần đánh giá, không tự thay bằng API provider khác.
  - Bằng chứng thực hiện:
    - Tạo đặc tả chuẩn tại `docs/architecture/review-criteria.md` bao gồm:
      - 5 nhóm tiêu chí chất lượng: định mức độ dài (Part và toàn bài), ngôi kể & điểm nhìn POV ("Bạn"), cấu trúc bẫy tranh luận (comment hook), khử mùi AI & giọng trần thuật sắc lạnh, chuẩn định dạng ElevenLabs TTS (zero-clutter, max 500 ký tự/dòng).
      - Cấu trúc dữ liệu quyết định chuẩn `ReviewDecision` (id, task_run_id, attempt_id, reviewer_agent_id, revision_round, decision, score, feedback, violations, decision_key, created_at).
      - Cơ chế giới hạn số lần sửa (`max_revisions`, mặc định 2), dừng lặp và leo thang (`escalated`) báo người vận hành, bảo toàn checkpoint artifacts và chặn lỗi hạ nguồn.

## AGN-002

- [x] **AGN-002 — Vòng Agent giao việc, duyệt và yêu cầu sửa** — Xong | Feature
  - Phụ thuộc: [AGN-001](001-agent-review.md#agn-001), [RUN-006](../runs/003-skill0-web.md#run-006), [CLI-002](../client/002-process-execution.md#cli-002).
  - Nghiệm thu: Agent đánh giá output thật, gửi chỉ đạo đúng phiên, lưu bằng chứng và quyết định; không tự duyệt chỉ vì runtime exit 0 hoặc lặp vô hạn. Có test đạt, yêu cầu sửa, hết giới hạn và khử trùng quyết định.
  - Bằng chứng thực hiện:
    - Migration SQLite `apps/server/migrations/007_agent_reviews.sql` khởi tạo bảng `review_decisions` với ràng buộc STRICT, FK, và UNIQUE(decision_key).
    - Triển khai `ReviewRepository` tại `apps/server/src/agent_cf_server/infrastructure/agents/review_repository.py` với logic `evaluate_content` và `record_decision` khử trùng idempotent.
    - Triển khai API router tại `apps/server/src/agent_cf_server/api/reviews.py` (`POST /v1/task-runs/{id}/reviews`, `GET /v1/task-runs/{id}/reviews`, `POST /v1/evaluate-content`).
    - Cập nhật hợp đồng OpenAPI `openapi/openapi.yaml` với 58 schemas, 27 paths, 31 operations.
    - Test kiểm chứng: `test_agn001_agn002_review_criteria_and_deduplication` trong `apps/server/tests/integration/runs/test_skill_chain_review.py` đạt 100%.
