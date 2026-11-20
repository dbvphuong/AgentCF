# Giao diện quản trị theo prototype

[Module](README.md) · [Báo cáo](../../../reports/ui-completion-check.md)

## BASE-004

- [x] **BASE-004 — Layout quản trị, điều hướng tám menu và kiểm tra responsive** — Xong | Feature
  - Nguồn: [requirements theo màn hình](../../../product/requirements.md#yêu-cầu-theo-màn-hình), [prototype](../../../../demo/agent-cf-prototype/README.md).
  - Phụ thuộc: BASE-002 và các task UI tương ứng từng module.
  - Nghiệm thu: sidebar tím, menu mobile, deep link/hash, Ctrl/Cmd+K, focus/Escape cho modal, loading/empty/error, xác nhận thao tác và bảng cuộn ngang; giữ code theo features và dùng API thật, không copy dữ liệu mẫu vào sản phẩm.
  - Bằng chứng 2026-11-17: `apps/web/src/app/`, `shared/` và public index từng feature; `tests/browser/smoke.cjs` kiểm tra 8 menu ở hai viewport và editor mobile (17 checks), ảnh `runtime/ui-review/`. Browser smoke qua đầy đủ catalog → Project → editor/publish/reload → Schedule → Run/cancel và pairing/Disable PC, không có lỗi JavaScript. Web unit tests 19 passed; build/typecheck đạt. Phạm vi từng menu và giới hạn backend ở báo cáo; không tự đánh dấu tất cả menu đã nghiệm thu.
