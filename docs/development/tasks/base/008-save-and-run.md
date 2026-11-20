# Lưu và dùng ngay

[Module](README.md) · [ADR 0011](../../../architecture/decisions/0011-save-and-run-current-configuration.md)

## BASE-009

- [x] **BASE-009 — Lưu và dùng ngay** — Xong trong phạm vi local dưới đây.
- Phạm vi: bỏ thao tác Draft/Version/Publish ở Skill/Process/Run/Schedule; Robot giữ version, form Lưu tạo bản sẵn dùng.
- Phụ thuộc: SKL-005, PROC-005, RUN-010; bảo toàn quyền, nguồn Skill local và snapshot lịch sử.
- Triển khai: migration 022 lưu cấu hình Process hiện tại và chế độ lịch theo cấu hình. GET/PUT configuration có token chống ghi đè; POST Process/runs tự tạo snapshot bất biến cùng transaction, khử trùng trước khi chụp. Team và clone dùng cấu hình hiện tại. API lifecycle cũ giữ tương thích.
- Nghiệm thu: Skill chưa Publish vẫn dùng được; sửa Skill ảnh hưởng Run mới, không sửa Run cũ; lưu đồng thời bị chặn; lịch nhận cấu hình mới; Robot Lưu dùng ngay; Web không còn các bước thủ công này.
- Kiểm chứng: `.venv\Scripts\python.exe -m pytest -q` đạt **281 passed, 1 skipped**; `npm.cmd --prefix apps/web test` đạt **22 passed**; `npm.cmd --prefix apps/web run build` đạt TypeScript/Vite. `node runtime/design-review/check_contract.cjs` đạt **97 schemas / 80 paths / 105 operations** sau đồng bộ bằng `node openapi/sync-local-ui.cjs`.
- Test mới: `apps/server/tests/integration/projects/test_current_configuration.py` kiểm Skill chưa Publish, nguồn local lưu từ form, snapshot/receipt/CAS, rollback khi input lỗi, lịch theo cấu hình mới, Team/clone/tham chiếu và Robot lưu sẵn dùng. Web test `current-run.test.mjs` gọi đúng API theo Process, truyền chủ đề và báo lỗi Server.
- Trình duyệt: `node runtime/simple-config-ui.cjs` đạt với API fixture riêng trong tab, không sửa dữ liệu thật hoặc chạy model; kiểm Lưu, Skill Global không cần Publish, form Chạy không chọn version, catalog bỏ Versions và không gọi N+1 Skill versions. Bằng chứng `runtime/simple-config-ui.json`, `runtime/simple-run-ui.png`. Server local `/healthz` trả schema 22; Client 0.3.0 vẫn online và gửi CPU/RAM thật sau restart.
- Giới hạn: không thay adapter/runtime, không chứng minh vòng Agent API tổng quát, Temporal/restart hoặc mapping nâng cao đã hoàn thiện. Không chạy model thật trong test.
