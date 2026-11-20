# 0001 - Stack ứng dụng và ranh giới thực thi

- Status: Accepted
- Date: 2026-11-13
- Last updated: 2026-11-16

## Context

Agent CF cần web quản trị, editor node, tác vụ dài chạy tại PC, tích hợp Codex/Antigravity và tool người dùng đã có. Repository chỉ có prototype HTML. Người dùng yêu cầu ghi lại lựa chọn công nghệ để tiếp tục ở máy khác; chưa có triển khai hoặc kết quả thử tích hợp thực tế.

## Decision

Chấp thuận stack cho hệ thống quản lý tổng và Process động trong phạm vi thiết kế được giao ngày 2026-11-16. Chưa triển khai ứng dụng:

| Phần | Lựa chọn |
|---|---|
| Frontend | React, TypeScript, Vite |
| UI | Tailwind CSS, shadcn/ui |
| Process editor | React Flow |
| Server API | Python, FastAPI |
| Engine điều phối Process | Temporal, Python SDK — xem ADR 0003 |
| Database nghiệp vụ | SQLite cho giai đoạn local — đã chốt riêng tại ADR 0004 |
| CF Client / adapter | Python, tách khỏi server và frontend |
| Kết nối | HTTPS và WebSocket có xác thực |
| HTTP contract | OpenAPI khi bắt đầu xây API |

Scaffold gồm React/TypeScript/Vite, FastAPI, worker Temporal riêng và CF Client Python trong phiên người dùng. Tailwind/shadcn phục vụ UI; React Flow dùng khi triển khai editor. Tray, ORM/migration library và bộ cài được chọn ở task triển khai liên quan.

Điều phối độc lập vòng đời HTTP. Topology local và persistence Temporal tại [ADR 0003](0003-process-engine-temporal.md); snapshot, inbox/outbox và quyền tại [ADR 0005](0005-versioned-process-execution.md). Chưa thêm Celery/Redis hoặc LangGraph cho cùng nhiệm vụ. HTTP là kênh lệnh/kết quả có xác thực; WebSocket chỉ thông báo. Môi trường và dependency tại [setup](../../development/setup.md), chưa nghiệm thu tích hợp.

ADR trước đây Proposed; BASE-001 hoàn thiện hướng đã có, không thay framework. Accepted ngày 2026-11-16 ghi nhận quyết định thiết kế trong phạm vi người dùng giao, không phải kết quả build/test. Skill 0–1–2 chỉ là bộ test của Process động; editor và catalog có task triển khai riêng. DB nghiệp vụ giữ quyết định SQLite tại ADR 0004.

## Consequences

- Web và execution có ranh giới rõ; đóng web không dừng công việc.
- Python là lớp gọi chương trình/tool, không bắt buộc viết lại tool bằng Python.
- Có thể giữ UI định hướng hiện tại nhưng không bê nguyên JS prototype thành domain production.
- Phải kiểm chứng adapter thật, task dài, hủy và reconnect trước khi mở rộng toàn bộ màn hình.
- Hai hệ sinh thái TypeScript/Python cần hợp đồng dữ liệu chung qua API.

## Alternatives considered

- Giữ HTML/JS prototype làm ứng dụng chính: nhanh ban đầu nhưng chưa có ranh giới domain và hạ tầng thực thi.
- Dùng TypeScript cho cả server/client: có thể làm, chưa thấy lợi ích đủ để ưu tiên hơn Python cho lớp tích hợp hiện tại.
- Chọn ngay một nền tảng điều phối/Agent toàn diện: chưa đủ thử nghiệm để biết phù hợp tool Windows, phiên người dùng và yêu cầu can thiệp.

## References

- [React Flow](https://reactflow.dev/)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [FastAPI về background tasks và tác vụ lớn](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Tổng quan kiến trúc](../overview.md)
- [Cấu trúc source code dự kiến](../../development/project-structure.md)
