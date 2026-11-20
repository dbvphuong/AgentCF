# Môi trường local

> Last updated: 2026-11-16

[Module](README.md) · [Quy ước task](../README.md) · [Kế hoạch tổng](../../implementation-plan.md)

Nguồn yêu cầu, ADR và vị trí code/test nằm trong README của module. Các task con dưới đây giữ mã riêng để giao việc, theo dõi phụ thuộc và nghiệm thu; trạng thái chỉ cập nhật tại file này.

## BASE-000

- [x] **BASE-000 — Chuẩn bị môi trường local** — Xong | Infrastructure
  - Phụ thuộc: Không. Phạm vi: Python 3.14, dependency Web/Server/Client, lockfile và Git ignore; không phải scaffold ứng dụng.
  - Bằng chứng: [setup và kết quả kiểm tra](../../setup.md#kiểm-tra-môi-trường); manifest trong `apps/`, `.python-version`, `.gitignore`. Giới hạn môi trường đã ghi trong setup.
