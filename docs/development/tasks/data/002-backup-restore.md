# Backup, restore và hướng chuyển DB

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## DATA-002

- [x] **DATA-002 — Quy trình backup/restore và nền chuyển DB** — Hoàn thành | Infrastructure
  - Phụ thuộc: [DATA-001](001-sqlite-persistence.md#data-001).
  - Nghiệm thu: khôi phục bản sao nhất quán và đối soát lịch sử/artifact reference; ghi các khác biệt cần xử lý khi chuyển PostgreSQL. Không tự triển khai PostgreSQL khi chưa được giao.
  - Mã nguồn triển khai:
    - `BackupManager` tại `apps/server/src/agent_cf_server/infrastructure/persistence/backup.py`:
      - Cơ chế SQLite Online Snapshot không khóa (`sqlite3.Connection.backup()`) an toàn trong chế độ WAL khi đang có transaction đọc/ghi.
      - Kiểm tra tính toàn vẹn vật lý qua `PRAGMA integrity_check`.
      - Quét và đối soát mã băm SHA-256 từng file artifact vật lý với bảng `artifacts`.
      - Đóng gói cơ sở dữ liệu, artifacts và metadata vào tệp nén `.tar.gz` kèm `manifest.json`.
      - Quy trình kiểm tra archive độc lập (`verify_backup`).
      - Quy trình khôi phục (`restore_backup`) tự động kích hoạt đối soát toàn diện: `PRAGMA foreign_key_check`, thống kê số lượng thực thể, phát hiện quan hệ mồ côi (`task_runs` thiếu `process_runs`, `attempts` thiếu `task_runs`, `artifacts` thiếu `attempts`).
    - Tiện ích CLI tại `apps/server/scripts/backup_restore.py` hỗ trợ đầy đủ các lệnh `backup`, `verify`, `restore`.
    - Tài liệu vận hành và bảng đối chiếu khác biệt kiến trúc khi chuyển PostgreSQL theo ADR 0004 tại `docs/operations/backup-restore.md`.
  - Kiểm chứng tự động:
    - `test_data002_backup_creation_and_online_snapshot_consistency`
    - `test_data002_backup_restore_and_consistency_reconciliation`
    - `test_data002_corrupted_backup_detection`
    - Kiểm chứng khép kín CLI script: `backup` -> `verify` -> `restore` thành công 100%.
