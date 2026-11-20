# Task triển khai theo module

[Kế hoạch tổng](../implementation-plan.md) · [Cấu trúc code](../project-structure.md)

## Cách tìm và cập nhật

1. Từ checklist menu hoặc nền tảng dùng chung trong kế hoạch tổng, mở README của module sở hữu tính năng.
2. Mở file đầu việc cần làm. Đọc task được giao, nguồn spec/ADR và các task phụ thuộc được liên kết; không cần đọc mọi task của dự án.
3. Thêm tính năng hoặc bug vào file đầu việc liên quan. Nếu là đầu việc độc lập, tạo file mới trong cùng module và thêm liên kết ở README module; không nối mọi nội dung vào một file lớn.
4. Mỗi task con có mã cố định. Nếu cần chia một task rộng, cấp mã mới, nêu quan hệ cha/con và phụ thuộc trong cùng file; giữ task cũ làm đầu mối, không tự đánh dấu hoàn tất khi mới tách tài liệu.
5. Cập nhật trạng thái, nghiệm thu, code/test và bàn giao tại file đầu việc. Cập nhật ô tích menu/mốc trong kế hoạch tổng khi toàn bộ phạm vi tương ứng đạt nghiệm thu; hoàn thành một task không tự hoàn thành menu. Ưu tiên và thứ tự liên module cũng cập nhật tại kế hoạch tổng khi thay đổi.

Mỗi file đầu việc chứa mục tiêu/phạm vi qua tên và các task con, nguồn chuẩn qua README module, phụ thuộc có liên kết, điều kiện nghiệm thu và bằng chứng/bàn giao khi có. Chỉ thêm checklist con khi đủ rõ để nghiệm thu; không tạo các bước giả hoặc tự đánh dấu bước đã làm từ một báo cáo chưa chứng minh.

Tên thư mục theo module sở hữu; `projects/processes/` tương ứng phần Process của Project. `base/`, `data/`, `api/` và `execution/` là nhóm trách nhiệm kỹ thuật, không tự tạo menu hoặc module code mới. Kiến trúc arc42 và requirements vẫn ở nguồn riêng; đây là kế hoạch công việc, không phải bộ spec thứ hai.

## Spec, task và code dùng thế nào

Không tạo thêm một bộ spec chép lại requirements. Dùng chuỗi truy vết sau:

**Yêu cầu trong nguồn chuẩn → mã task trong file đầu việc của module → code/test đúng module → bằng chứng nghiệm thu.**

| Cần tìm gì | Nguồn chuẩn |
|---|---|
| Hành vi, quy tắc, menu và phạm vi | [Requirements](../../product/requirements.md), [use case YouTube](../../product/use-cases/youtube-video.md) |
| Tên nghiệp vụ và quan hệ | [Glossary](../../product/glossary.md), [domain model](../../architecture/domain-model.md) |
| Trạng thái, dependency và thực thi | [Execution model](../../architecture/execution-model.md) |
| Quyết định công nghệ | [Architecture overview](../../architecture/overview.md) và ADR được liên kết ở đó |
| Vị trí code/test, ranh giới module | [Project structure](../project-structure.md) |
| Việc đã làm, còn thiếu, bị vướng | File đầu việc trong thư mục module tương ứng |
| Lệnh và bằng chứng thử nghiệm | [Setup](../setup.md), [hướng dẫn CLI](../local-runtime-cli.md), [báo cáo runtime](../../reports/local-runtime-check.md), [báo cáo Skill 0](../../reports/local-skill0-check.md) |

Nếu một task cần thêm thiết kế, bổ sung phần còn thiếu vào đúng nguồn chuẩn trước khi code. Hợp đồng kỹ thuật dùng OpenAPI/schema khi triển khai; lựa chọn kiến trúc cần ADR theo [AGENTS.md](../../../AGENTS.md). Không tự chốt điều chưa rõ chỉ để đánh dấu task.

### Quy ước task

- `[x]` chỉ dùng khi đúng phạm vi task đã đạt và có bằng chứng; `[ ]` là chưa hoàn thành.
- Trạng thái ghi rõ: **Chưa làm**, **Đang làm**, **Chờ quyết định**, **Vướng kỹ thuật**, **Để sau**, **Xong**. “Đã thử độc lập” là phạm vi của task thử nghiệm, không phải trạng thái hoàn thành feature ứng dụng.
- Mỗi task có mã cố định, vị trí code dự kiến qua nhóm module, nguồn spec, phụ thuộc và điều kiện nghiệm thu. Không đổi mã hoặc tái sử dụng mã cũ khi sắp xếp lại plan.
- Chỉ ghi **Đang làm** khi đã nhận task; khi dừng bàn giao, ghi phần đã đạt, phần còn thiếu và bước tiếp theo ngay dưới task đó. Không đánh dấu một task lớn xong khi mới tạo file hoặc màn hình.
- Mỗi thay đổi hành vi cần test phù hợp; khi hoàn tất ghi file/test liên quan, lệnh thực sự đã chạy, kết quả và giới hạn. Theo Definition of Done trong AGENTS.md.
- Các task backlog rộng phải tách nhỏ và làm rõ acceptance trước khi giao triển khai. Khi tách, cấp mã mới, giữ task cũ làm đầu mối và cập nhật phụ thuộc; không tick task cha trước khi task con đạt.

### Khi thêm tính năng hoặc sửa lỗi

1. Xác định module sở hữu và yêu cầu liên quan; nếu thiếu/mâu thuẫn, hỏi chủ dự án và cập nhật nguồn chuẩn trong phạm vi được giao.
2. Thêm task vào đúng thư mục module và file đầu việc với mã mới, loại **Feature**, **Fix**, **Design**, **Verification** hoặc **Infrastructure**. Không tự tạo feature/module mới từ một tên menu chưa được thống nhất.
3. Ghi tình huống đầu vào, hành vi mong muốn, đường dẫn dự kiến, phụ thuộc và cách kiểm tra. Task Fix cần tình huống tái hiện và regression test khi hạ tầng cho phép.
4. Làm thay đổi trong module sở hữu; nếu đổi hợp đồng chung thì liệt kê và cập nhật các nơi bị ảnh hưởng.
5. Cập nhật trạng thái và bằng chứng ngay trong file đầu việc; giữ báo cáo dài ở tài liệu liên quan rồi liên kết, không nối nhật ký vào đầu plan.

Mẫu thêm task, chưa phải task đã giao:

```markdown
## <MODULE>-<NNN>

- [ ] **<MODULE>-<NNN> — <Tên task>** — Chưa làm | Feature/Fix/Design/Verification/Infrastructure
  - Spec: <liên kết yêu cầu hoặc ADR>; vị trí code/test: <đường dẫn>.
  - Phụ thuộc: <mã task hoặc Không>.
  - Nghiệm thu: <đầu vào cụ thể → kết quả quan sát được và kiểm tra cần chạy>.
  - Bàn giao khi làm: <file đổi, lệnh/kết quả, giới hạn, việc tiếp theo>.
```
