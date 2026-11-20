# Khung ứng dụng và hạ tầng điều phối

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## BASE-002

- [x] **BASE-002 — Khung Web, Server, Client khởi động được** — Xong | Infrastructure
  - Phụ thuộc: [BASE-001](001-foundation-design.md#base-001).
  - Nghiệm thu: entrypoint, config schema/cấu hình mẫu và lệnh local/check có thật; Web/Server/Client kiểm tra kết nối được. Chưa tạo các menu/catalog không cần cho luồng đầu tiên.
  - Bằng chứng 2026-11-16: Web React/Vite, Server entrypoint/config/health, Client CLI check và `.env.example` từng app; live smoke Web proxy → Server SQLite schema 3 và Client → Server đạt. Lệnh/check và review chéo tại [báo cáo nền tảng](../../../reports/foundation-bootstrap-check.md), [setup](../../setup.md). Chưa triển khai `/v1` hoặc chạy Skill.
  - Kiểm tra: pytest root, Web test/typecheck/build, pip check đạt; số liệu cuối ở báo cáo. Health chỉ metadata an toàn; readyz kiểm tra Service khi bật, không tự báo worker đã sẵn sàng.

## BASE-003

- [ ] **BASE-003 — Hạ tầng Temporal Service và worker local** — Vướng kỹ thuật | Infrastructure
  - Spec: [ADR engine](../../../architecture/decisions/0003-process-engine-temporal.md); vị trí: `infra/`, `apps/server/src/agent_cf_server/bootstrap/` và test tích hợp Server, chỉ tạo nơi có nội dung thực tế.
  - Phụ thuộc: [BASE-001](001-foundation-design.md#base-001), [BASE-002](002-application-bootstrap.md#base-002).
  - Nghiệm thu: có cấu hình/lệnh chạy Service và worker theo topology/persistence đã chốt, độc lập HTTP; kiểm tra kết nối và một phép thử điều phối không side effect, restart Service/worker đọc lại được lịch sử phép thử. Ghi đường dẫn dữ liệu ngoài Git, giới hạn dev/production và cập nhật setup. Chưa phải giao việc Codex thật hoặc khôi phục tiến trình PC; [RUN-002](../runs/002-run-execution-history.md#run-002) và [REL-001](../execution/002-recovery.md#rel-001) nghiệm thu riêng.

  - Bàn giao 2026-11-16: đã có launcher `infra/temporal/start-dev.ps1`, worker process riêng, Workflow/probe không side effect và integration test opt-in. SDK 1.36.1 import/sandbox trên Python 3.14 đạt (4 unit test); cấu hình và lệnh tại [infra README](../../../../infra/temporal/README.md).
  - Vướng cụ thể: binary CLI chính thức chưa tải được qua mạng máy hiện tại (reset/certificate và archive không hợp lệ từ CDN). SDK cài được, nhưng chưa có Service để kiểm tra connect hoặc restart Service/worker với cùng DB. Không đánh Xong từ compile/sandbox/mock; test Temporal integration chưa chạy đạt.
  - Việc còn lại: cung cấp CLI binary hợp lệ, chạy launcher + worker, test opt-in và phép thử restart Service giữ run ID/marker/history theo hướng dẫn. [Báo cáo](../../../reports/foundation-bootstrap-check.md) ghi các phép thử đã chạy và giới hạn; chưa nghiệm thu RUN-002/REL-001.
