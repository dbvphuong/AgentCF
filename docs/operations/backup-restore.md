# Hướng Dẫn Vận Hành Sao Lưu và Phục Hồi (DATA-002)

Tài liệu này hướng dẫn chi tiết quy trình sao lưu (backup), kiểm tra tính toàn vẹn (verify), và phục hồi dữ liệu kèm đối soát sau sự cố (restore & reconciliation) cho hệ thống Agent CF theo kiến trúc chuẩn SQLite nghiệp vụ cục bộ (ADR 0004).

---

## 1. Cơ chế sao lưu Online Snapshot

Agent CF sử dụng SQLite ở chế độ Write-Ahead Logging (`PRAGMA journal_mode = WAL;`) với ràng buộc khóa ngoại nghiêm ngặt (`PRAGMA foreign_keys = ON;`). 

Khi thực hiện sao lưu:
- Cơ chế `sqlite3.Connection.backup()` của SQLite C-API sao chép dữ liệu từng trang (page-by-page) từ cơ sở dữ liệu nguồn sang tệp snapshot đích một cách nhất quán (consistent point-in-time snapshot).
- Không khóa cứng bảng, không làm gián đoạn luồng đọc ghi hiện thời của server và worker client.
- Kiểm tra tính toàn vẹn trang vật lý của snapshot độc lập bằng `PRAGMA integrity_check`.
- Thu thập tất cả các file artifact vật lý đã đăng ký thành công (`availability = 'available'`), đối soát mã băm SHA-256 từng file với bản ghi metadata trong cơ sở dữ liệu.
- Đóng gói toàn bộ cơ sở dữ liệu SQLite, các tệp artifacts tương ứng và tệp kê khai `manifest.json` vào tệp nén duy nhất định dạng `.tar.gz`.

### Cấu trúc gói sao lưu (.tar.gz)
```
backup_bundle.tar.gz
├── manifest.json            # Thông tin phiên bản schema, thời gian, SHA-256 DB & artifacts
├── database.sqlite          # Bản sao lưu SQLite nhất quán
└── artifacts/               # Cây thư mục artifact thực tế
    └── <attempt_id>/
        └── <filename>
```

---

## 2. Công cụ dòng lệnh (CLI Utility)

Tiện ích CLI được tích hợp sẵn tại `apps/server/scripts/backup_restore.py`.

### 2.1. Lệnh tạo bản sao lưu (`backup`)
Tạo snapshot nhất quán của cơ sở dữ liệu và đóng gói artifacts:

```bash
python apps/server/scripts/backup_restore.py backup \
  --db-path ./data/agent_cf.sqlite \
  --artifacts-dir ./data/artifacts \
  -o ./backups/agent_cf_backup_$(date +%Y%m%d_%H%M%S).tar.gz
```

**Đầu ra mẫu (JSON):**
```json
{
  "status": "success",
  "backup_file": "/absolute/path/to/backups/agent_cf_backup_20261116_105611.tar.gz"
}
```

### 2.2. Lệnh kiểm tra tính toàn vẹn bản sao lưu (`verify`)
Kiểm tra archive độc lập trong môi trường tạm thời mà không đụng chạm đến cơ sở dữ liệu đang chạy:

```bash
python apps/server/scripts/backup_restore.py verify \
  -i ./backups/agent_cf_backup_20261116_105611.tar.gz
```

**Đầu ra mẫu (JSON):**
```json
{
  "status": "valid",
  "details": {
    "valid": true,
    "manifest_version": "1.0",
    "created_at": "2026-11-16T10:56:11.040527Z",
    "schema_version": 9,
    "db_size_bytes": 548864,
    "total_artifacts": 12
  }
}
```

Nếu archive bị sửa đổi trái phép (sai khác SHA-256 cơ sở dữ liệu, thiếu file artifact, hoặc hỏng trang SQLite), lệnh trả về mã lỗi `1` kèm thông tin chi tiết:
```json
{
  "status": "error",
  "error": "BackupIntegrityError",
  "message": "Database checksum mismatch: expected ..., got ..."
}
```

### 2.3. Lệnh phục hồi dữ liệu (`restore`)
Phục hồi cơ sở dữ liệu và kho artifacts sang thư mục đích, tự động kích hoạt quy trình đối soát sau phục hồi (reconciliation):

```bash
python apps/server/scripts/backup_restore.py restore \
  -i ./backups/agent_cf_backup_20261116_105611.tar.gz \
  --target-db ./data/agent_cf.sqlite \
  --target-artifacts ./data/artifacts \
  --overwrite
```

**Đầu ra mẫu (JSON):**
```json
{
  "status": "restored",
  "report": {
    "restored_at": "2026-11-16T10:56:22.113859Z",
    "manifest_version": "1.0",
    "schema_version": 9,
    "integrity_check": "ok",
    "counts": {
      "workspaces": 2,
      "projects": 3,
      "processes": 5,
      "tasks": 14,
      "process_runs": 8,
      "task_runs": 22,
      "attempts": 25,
      "artifacts": 12,
      "audit_events": 48
    },
    "verification": {
      "valid": true,
      "manifest_version": "1.0",
      "created_at": "2026-11-16T10:56:11.040527Z",
      "schema_version": 9,
      "db_size_bytes": 548864,
      "total_artifacts": 12
    }
  }
}
```

---

## 3. Quy trình Đối Soát Sau Phục Hồi (Post-Restore Reconciliation)

Trong quá trình phục hồi, `BackupManager.restore_backup()` thực hiện 4 bước kiểm tra nghiêm ngặt:

1. **Archive Pre-verification**: Giải nén vào phân vùng tạm và xác thực toàn bộ checksum SHA-256 cùng `manifest.json`. Nếu lỗi, quy trình dừng ngay trước khi ghi đè dữ liệu đích.
2. **Atomic Deployment**: Sao chép tệp SQLite và đồng bộ thư mục artifacts.
3. **Database Integrity & FK Check**:
   - `PRAGMA integrity_check`: Đảm bảo cấu trúc B-Tree không bị tổn hại.
   - `PRAGMA foreign_key_check`: Xác thực không có bất kỳ vi phạm khóa ngoại nào trên toàn bộ 9 migration schemas.
4. **Orphan Run Detection**:
   - Kiểm tra `task_runs` không mồ côi (tất cả đều có `process_runs` hợp lệ).
   - Kiểm tra `attempts` không mồ côi (tất cả đều có `task_runs` hợp lệ).
   - Kiểm tra `artifacts` không mồ côi (tất cả đều liên kết với `attempts` hợp lệ).

---

## 4. Lịch sao lưu khuyến nghị (Backup Rotation Schedule)

Để đảm bảo an toàn vận hành, thiết lập định kỳ tự động (cron/Task Scheduler):

| Tần suất | Loại sao lưu | Thời gian lưu trữ | Mục đích |
|---|---|---|---|
| **Mỗi 1 giờ** | Snapshot online (.tar.gz) | 24 giờ | RPO <= 1 giờ khi gặp sự cố phần cứng hoặc crash |
| **Mỗi ngày (00:00)** | Full backup | 7 ngày | Điểm khôi phục ngày ổn định |
| **Mỗi tuần (Chủ nhật)** | Archive backup | 4 tuần | Lưu trữ lịch sử audit & artifacts kiểm toán |

---

## 5. Khác biệt và Kế hoạch Chuyển Đổi sang PostgreSQL (ADR 0004)

Theo quyết định kiến trúc tại **ADR 0004**, hệ thống Agent CF hiện tại sử dụng SQLite file-based phục vụ trọn vẹn quy mô local/single-server. Khi mở rộng sang cụm phân tán và PostgreSQL, cần lưu ý các điểm khác biệt trọng yếu sau:

| Tiêu chí | SQLite Hiện Tại (ADR 0004) | PostgreSQL (Phân tán trong tương lai) |
|---|---|---|
| **Cơ chế sao lưu** | `sqlite3.backup()` API + đóng gói tar.gz | `pg_dump -Fc`, `pg_basebackup` hoặc WAL archiving liên tục (`pg_receivewal` / Barman / pgBackRest) |
| **Quản lý Artifacts** | Thư mục cục bộ (`artifacts_dir`), băm SHA-256 | Object Storage tương thích S3 (MinIO / AWS S3 / GCS) với presigned URLs và IAM roles |
| **Ràng buộc khóa ngoại** | Phải bật thủ công qua connection hook `PRAGMA foreign_keys = ON;` | Khóa ngoại được kích hoạt và kiểm tra tự động liên tục ở mức database engine |
| **Audit Immutability Triggers** | Trigger SQLite `immutable_audit_events` chặn `UPDATE`/`DELETE` qua `RAISE(ABORT, 'audit_immutable')` | Trigger PostgreSQL PL/pgSQL trả về `RAISE EXCEPTION` hoặc gán quyền `REVOKE UPDATE, DELETE ON audit_events FROM PUBLIC` |
| **Mức độ cô lập giao dịch** | WAL mode: Single writer - Multiple concurrent readers | Multi-Version Concurrency Control (MVCC): Nhiều writer đồng thời với `SERIALIZABLE` hoặc `READ COMMITTED` |
| **Tính tương thích Migration** | File SQL tuân thủ SQLite `STRICT` mode, kiểu dữ liệu linh hoạt | Chuyển đổi cú pháp DDL: `STRICT` -> kiểu native Postgres (`VARCHAR`, `TIMESTAMPTZ`, `JSONB`), index JSON qua `jsonb_path_ops` |
