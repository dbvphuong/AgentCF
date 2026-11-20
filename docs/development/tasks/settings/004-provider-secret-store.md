# Bảo vệ credential provider tại rest

[Module](README.md) · [Bằng chứng review](../../../reports/ui-completion-check.md#giới-hạn-nghiệm-thu)

## SET-004

- [ ] **SET-004 — Secret store cho API key provider** — Chưa làm | Fix
  - Nguồn: REQ-TOOL-02 và [Settings](../../../product/requirements.md#settings-và-cấu-hình-model).
  - Phụ thuộc: SET-002; quyết định cơ chế khóa/mã hóa cần được review trước triển khai.
  - Phát hiện: `SettingsRepository.create_provider/update_provider` lưu trực tiếp API key vào cột `api_key_ciphertext`; tên cột không chứng minh mã hóa. GET chỉ mask dữ liệu, không phải secret store.
  - Nghiệm thu: khóa không xuất hiện plaintext trong DB/backup/log/UI; có migration chuyển credential cũ an toàn, rotation/thu hồi, lỗi khi thiếu khóa giải mã; Test API đọc credential qua interface tin cậy. Giữ nguyên semantics “để trống khi sửa để giữ khóa”. Không dùng secret thật làm fixture.
