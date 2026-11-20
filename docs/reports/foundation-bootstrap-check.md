# Báo cáo kiểm tra và review nền tảng — 2026-11-16

## 1. Phạm vi và kết quả tổng quan

Đợt triển khai nền tảng gồm các mã công việc:
- **BASE-002 — Khung Web, Server, Client**: **Hoàn thành (`Done`)**
- **DATA-001 — Schema và migration SQLite tối thiểu cho luồng đầu tiên**: **Hoàn thành (`Done`)**
- **BASE-003 — Hạ tầng Temporal Service và worker local**: **Vướng kỹ thuật (`Blocked / Incomplete`)**

Toàn bộ mã nguồn khung ứng dụng Web (React/Vite), Server (FastAPI), Client CLI (Python), hệ thống SQLite migration (schema 1→3) và các cấu phần Temporal SDK/worker/probe đã được triển khai, review chéo và kiểm thử tự động. Điểm nghẽn duy nhất là việc tải và chạy file thực thi `temporal.exe` trên môi trường mạng máy hiện tại (bị chặn/timeout bởi proxy doanh nghiệp).

---

## 2. Kết quả review code cả nhóm

| Thành phần | Trách nhiệm | Kết quả review |
|---|---|---|
| **Web (`apps/web`)** | UI hiển thị trạng thái kết nối nền tảng | Scaffold React 19 + TypeScript + Vite. Triển khai proxy `/healthz` cùng origin tránh CORS. Giới hạn payload stream và kiểm tra schema health nghiêm ngặt; không hard-code menu/tính năng chưa có. |
| **Server (`apps/server`)** | API gateway & Điều phối nghiệp vụ | Entrypoint FastAPI có lifespan áp dụng migration tự động hoặc CLI `migrate`. Health routes: `/healthz` (trả metadata an toàn, schema version), `/readyz` (kiểm tra kết nối Service khi bật). Khóa cấu hình an toàn, chặn loopback bypass giả mạo. |
| **Client (`apps/client`)** | CF Client trên PC runner | CLI `agent_cf_client check` kiểm tra kết nối với Server qua HTTPX. Ràng buộc timeout từng I/O, giới hạn body 16KiB. Chưa thực thi task/tool hay nhận job khi chưa có pairing. |
| **Database (`apps/server/migrations`)** | Lưu trữ SQLite nghiệp vụ | 3 migration tuần tự (`001_definitions.sql`, `002_run_history.sql`, `003_integrity_guards.sql`). Bật WAL, synchronous FULL, foreign keys, busy timeout, atomic transaction, idempotency CAS, reconciling state và sequence chống ghi đè lịch sử. |
| **Temporal Worker (`apps/server/bootstrap`)** | Điều phối Workflow/Task durable | Cấu hình tách biệt khỏi DB nghiệp vụ. Worker độc lập chạy probe workflow không side effect (`AgentCFFoundationPersistenceProbeV1`). Launcher PowerShell Foreground `start-dev.ps1`. |

---

## 3. Các kiểm tra thực tế đã chạy thành công

1. **Python backend & Client tests (`pytest`)**:
   - Lệnh: `.venv/Scripts/python.exe -m pytest`
   - Kết quả: **77 passed, 1 skipped** (thời gian ~4.7s).
   - Test suites:
     - `apps/server/tests/integration/health/test_health.py`: 3 passed.
     - `apps/server/tests/integration/persistence/test_sqlite_foundation.py`: 24 passed (tạo mới, nâng schema 1→3, WAL, rollback, concurrency, CAS idempotency, immutable audit).
     - `apps/server/tests/unit/bootstrap/test_config.py`: 9 passed.
     - `apps/server/tests/unit/infrastructure/runs/temporal/test_foundation_compatibility.py`: 4 passed (Temporal SDK 1.36.1 compatibility, sandbox import, timeout handling trên Python 3.14).
     - `apps/client/tests/unit/adapters/test_local_runtime_probe.py`: 9 passed.
     - `apps/client/tests/unit/connection/test_client_health.py`: 28 passed.
     - *Phần skipped (1 test)*: `apps/server/tests/integration/temporal/test_foundation_probe.py` (yêu cầu Service Temporal đang chạy thực tế).

2. **Python dependencies verification (`pip check`)**:
   - Lệnh: `.venv/Scripts/python.exe -m pip check`
   - Kết quả: `No broken requirements found.`

3. **Web Frontend tests & build (`npm`)**:
   - Lệnh: `npm.cmd --prefix apps/web test`
   - Kết quả: **7/7 passed** (kiểm tra origin proxy, validate schema health, reject oversized stream, reject non-loopback HTTP).
   - Lệnh: `npm.cmd --prefix apps/web run build` (`tsc --noEmit && vite build`)
   - Kết quả: Build thành công bundle production không có cảnh báo kiểu hoặc lỗi biên dịch.

4. **Hợp đồng OpenAPI (`OpenAPI contract check`)**:
   - Lệnh: `node openapi/check-contract.cjs`
   - Kết quả: `{"openapi":"passed","schemas_compiled":54,"schema_cases":20,"graph_review_cases":5,"paths":25,"operations":28}`.

---

## 4. Chi tiết vướng mắc kỹ thuật tại BASE-003

- **Nguyên nhân**: Môi trường mạng nội bộ qua proxy `http://proxy.mbbank.com.vn:8080` chặn kết nối trực tiếp / ngắt kết nối (timeout/reset) tới các máy chủ phân phối binary của Temporal (`temporal.download` và GitHub release CDN).
- **Hệ quả**:
  - Không có file thực thi `temporal.exe` trong PATH hoặc repository.
  - Không thể khởi chạy process Temporal Development Server local.
  - Test integration `test_foundation_probe.py` bắt buộc phải `skip` do không có Service loopback port 7233.
  - Phép thử restart Service/worker giữ nguyên lịch sử workflow trên SQLite tách biệt chưa thể thực hiện tự động.
- **Ràng buộc tuân thủ (AGENTS.md)**: Không được dùng mock/sandbox để tự đánh dấu hoàn thành cho hạ tầng thực tế chưa kiểm chứng được.

---

## 5. Các bước hoàn tất BASE-003 khi có binary

Khi người dùng/quản trị viên cung cấp file `temporal.exe` (Windows x64):

1. **Đặt `temporal.exe`** vào PATH hệ thống hoặc đường dẫn chỉ định (ví dụ đặt tại `infra/temporal/temporal.exe`).
2. **Khởi động Temporal Service**:
   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra/temporal/start-dev.ps1 -TemporalBinary "infra/temporal/temporal.exe"
   ```
3. **Khởi động Worker (terminal 2)**:
   ```powershell
   $env:PYTHONPATH = 'apps/server/src'
   .venv/Scripts/python.exe -m agent_cf_server.bootstrap.worker
   ```
4. **Chạy test integration Temporal probe**:
   ```powershell
   $env:AGENT_CF_TEMPORAL_INTEGRATION = '1'
   $env:PYTHONPATH = 'apps/server/src'
   .venv/Scripts/python.exe -m pytest apps/server/tests/integration/temporal -q
   Remove-Item Env:AGENT_CF_TEMPORAL_INTEGRATION
   ```
5. **Thực hiện phép thử restart Service kiểm chứng persistence**:
   Theo quy trình probe trong [infra/temporal/README.md](../../infra/temporal/README.md#temporal-local-development).
6. **Cập nhật task**:
   Đánh dấu `[x]` cho BASE-003 trong `docs/development/tasks/base/002-application-bootstrap.md` và `docs/development/implementation-plan.md`.
