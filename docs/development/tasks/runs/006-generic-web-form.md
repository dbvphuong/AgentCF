# Form chạy tổng quát và lọc lịch sử

[Module](README.md) · [Báo cáo](../../../reports/ui-completion-check.md)

## RUN-009

- [x] **RUN-009 — Chọn published version, input JSON và phân trang lịch sử Runs** — Xong | Feature
  - Nguồn: [runtime snapshot](../../../product/requirements.md#cấu-hình-node-dùng-runtime-local), [Runs/Logs](../../../product/requirements.md#runs-và-logs).
  - Phụ thuộc: RUN-004/005, PROJ-001, PROC-002.
  - Thay đổi: bỏ topic/model/runtime fixture hard-code khỏi RunForm; chọn Project/Process/published version hoặc mở từ Project với version đã ghim. Runtime/model/Skill lấy từ snapshot; request chỉ gửi version/input. Bổ sung lọc Project/Process/Run ID/status/ngày, 25/50/100 dòng, cursor Previous/Next, STT và tổng số từ DB. Ngày dùng Started, fallback Created khi chưa bắt đầu; múi giờ hiển thị Việt Nam.
  - Bằng chứng 2026-11-17: Web test 19 passed, typecheck/build; regression `test_run_list_filters_counts_and_cursor`; browser smoke tạo/hủy Run qua Web và kiểm tra menu Runs desktop/mobile. Không gọi runtime thật trong smoke; không dùng kết quả này đóng RUN-008.
