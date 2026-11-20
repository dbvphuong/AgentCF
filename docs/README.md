# Tài liệu Agent CF

**Bắt đầu ở đây.** Tài liệu chia theo mục đích; kiến trúc có một bản chính theo arc42. Trạng thái ứng dụng và công việc tiếp theo được theo dõi trong plan, không suy ra từ số lượng tài liệu hoặc prototype.

## Ba trang để nắm dự án

| Bạn muốn biết | Đọc trang nào |
|---|---|
| Sản phẩm cần làm gì, màn hình hoạt động ra sao? | [Yêu cầu sản phẩm](product/requirements.md) |
| Hệ thống được thiết kế như thế nào, đã chốt gì? | [Kiến trúc chính — arc42](architecture/overview.md) |
| Đã có gì, đang thiếu gì, tiếp theo làm phần nào? | [Tiến độ và kế hoạch](development/implementation-plan.md) |

Quy trình thật của người dùng nằm tại [use case YouTube](product/use-cases/youtube-video.md). Xem [prototype](../demo/agent-cf-prototype/README.md) để review giao diện; dữ liệu mẫu chưa phải chức năng chạy thật.

## Cấu trúc thư mục

```text
docs/
├── README.md                 # Bản đồ đọc tài liệu
├── product/                  # Mục tiêu, yêu cầu, thuật ngữ, quy trình thật
├── architecture/
│   ├── overview.md           # Kiến trúc chính, 12 mục arc42 trong một file
│   ├── domain-model.md       # Chi tiết quan hệ và vòng đời nghiệp vụ
│   ├── execution-model.md    # Chi tiết thực thi Process/Task
│   └── decisions/            # ADR: lý do và trạng thái từng quyết định
├── development/
│   ├── implementation-plan.md # Tiến độ tổng, thứ tự và bản đồ module
│   ├── tasks/                # Module → file đầu việc → task con
│   │   ├── agents/           # Agent duyệt, catalog
│   │   ├── projects/         # Project, Team/Targets và processes/
│   │   └── runs/             # Thiết kế, thực thi, Web và chuỗi Skill
│   └── ...                   # Cấu trúc code, hướng dẫn cài và CLI
└── reports/                  # Bằng chứng kiểm chứng theo thời điểm
```

Khung [arc42](https://arc42.org/overview/) áp dụng cho tài liệu kiến trúc. Yêu cầu sản phẩm, task triển khai, hướng dẫn thao tác và báo cáo có trách nhiệm riêng. Không tạo 12 file để đủ mẫu; phần chi tiết được liên kết từ bản kiến trúc chính.

## Tài liệu theo công việc

### Sản phẩm

| Tài liệu | Dùng để làm gì |
|---|---|
| [Vision](product/vision.md) | Mục tiêu và phạm vi sản phẩm |
| [Requirements](product/requirements.md) | Hành vi, quy tắc, menu và tiêu chí chấp nhận |
| [Glossary](product/glossary.md) | Nguồn chuẩn của thuật ngữ nghiệp vụ |
| [Use case YouTube](product/use-cases/youtube-video.md) | Nhu cầu thật, tool hiện có và quy trình người dùng |

### Kiến trúc

Bắt đầu ở [overview](architecture/overview.md). Các mục 5–6 dẫn tới [domain model](architecture/domain-model.md) và [execution model](architecture/execution-model.md); mục 9 là danh sách ADR với trạng thái riêng. Không cần đọc từng file quyết định để đoán kiến trúc tổng thể.

Nguồn của quyết định là ADR tương ứng. Việc đổi cách trình bày tài liệu không thay đổi lựa chọn công nghệ hoặc biến đề xuất thành quyết định đã chấp thuận.

Thiết kế nền local ngày 2026-11-16 đã hoàn tất chuỗi BASE-001 → PROC-001 → REL-004 → RUN-001 → API-001 cho Process động; chưa triển khai ứng dụng. HTTP tại [OpenAPI](../openapi/openapi.yaml), thứ tự giao tiếp/quyền tại [Client protocol](architecture/client-protocol.md), cách kiểm tra độc lập tại [contract README](../openapi/README.md).

### Triển khai và hướng dẫn

| Tài liệu | Dùng để làm gì |
|---|---|
| [Implementation plan](development/implementation-plan.md) | Checklist hoàn thành từng menu, các mốc sử dụng và thứ tự triển khai; liên kết đến module |
| [Tasks theo module](development/tasks/README.md) | Quy ước tìm/thêm task; mỗi module có README và file đầu việc chứa task con, phụ thuộc, nghiệm thu, bằng chứng |
| [Project structure](development/project-structure.md) | Tính năng nằm ở đâu trong code và test, ranh giới phụ thuộc |
| [Setup](development/setup.md) | Cài và kiểm tra môi trường hiện có |
| [Runtime CLI](development/local-runtime-cli.md) | Cách gọi Codex/Antigravity, UTF-8, xuất file, resume và giới hạn thao tác |

Khi được giao code, đọc [AGENTS.md](../AGENTS.md), mở đúng task và nguồn spec trước khi thực hiện. Hợp đồng máy như OpenAPI, schema/migration và config là nguồn thực thi khi được tạo; không chép chúng thành nhiều bảng Markdown.

### Báo cáo kiểm chứng

Đọc khi cần bằng chứng hoặc điều tra một giới hạn, không dùng làm hướng dẫn thao tác chính.

| Báo cáo / dữ liệu | Nội dung quan sát |
|---|---|
| [Runtime local — 2026-11-16](reports/local-runtime-check.md) | Các phép thử Codex và Antigravity, thành công và phần chưa xác minh |
| [Skill 0 — 2026-11-16](reports/local-skill0-check.md) | Input, file cốt truyện, cách điều phối đã thử và kết quả kiểm tra |
| [Review thiết kế nền — 2026-11-16](reports/foundation-design-review.md) | Đối chiếu ADR/domain/execution/contract, mâu thuẫn đã sửa và kiểm tra tĩnh; chưa phải kiểm chứng ứng dụng |
| [Model inventory — 2026-11-16](reports/local-runtime-models.json) | Snapshot nhãn/ID/model access quan sát được; không phải config ứng dụng |

Raw log, DB và artifact runtime cục bộ nằm ngoài Git theo cấu hình project. Báo cáo trong `reports/` giữ kết luận có ngày và liên kết bằng chứng phù hợp; không đưa credential hoặc phiên đăng nhập vào đó.

## Quy tắc duy trì tài liệu

- Mỗi thông tin có một nguồn chuẩn theo [AGENTS.md](../AGENTS.md#4-nguồn-chuẩn-duy-nhất). Trang khác tóm tắt và liên kết; không duy trì nhiều bản của cùng một trạng thái.
- Thêm/sửa hành vi: cập nhật requirements; đổi cấu trúc hoặc cách thực thi: cập nhật mục arc42 tương ứng và phần chi tiết bị ảnh hưởng; quyết định kiến trúc quan trọng ghi ADR.
- Tiến độ tổng nằm trong plan; trạng thái, nghiệm thu và bằng chứng của task nằm tại file đầu việc trong `development/tasks/<module>/`. Khi thêm tính năng/sửa lỗi, cập nhật đúng module/file; chỉ sửa plan tổng khi ảnh hưởng tiến độ hoặc ưu tiên. Hướng dẫn viết theo thao tác có thể dùng lại; kết quả từng lần kiểm chứng nằm trong reports.
- Tài liệu kiến trúc/yêu cầu dùng `Draft` khi còn cần duyệt. ADR dùng `Proposed`, `Accepted`, `Superseded` theo quy tắc riêng. Báo cáo ghi thời điểm quan sát; trạng thái quyết định và mức độ triển khai là hai thông tin khác nhau.
- Proposed ghi nhận phương án hiện có và phần cần hoàn thiện, không yêu cầu chọn lại công nghệ từ đầu. Khi giao task thiết kế, người triển khai dùng architecture/ADR làm cơ sở, hoàn thiện chi tiết và ghi căn cứ quyết định trong phạm vi task; chỉ hỏi khi nhu cầu chưa rõ hoặc có thay đổi/đánh đổi ảnh hưởng người dùng. Accepted không yêu cầu mọi feature tương lai đã kiểm chứng; từng task phải ghi bằng chứng và giới hạn riêng.
- Chỉ thêm file khi có nội dung cần dùng và nơi chịu trách nhiệm rõ. Không kê danh sách file rỗng hoặc đường dẫn Planned để tạo cảm giác đủ quy trình.
- Đổi tên/di chuyển tài liệu phải cập nhật liên kết và mục lục cùng thay đổi. Hướng dẫn cài máy mới tại setup; tài khoản, model, tool và đường dẫn phải kiểm tra lại trên máy đó.
