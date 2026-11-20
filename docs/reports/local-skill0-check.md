# Kiểm chứng Skill 0 bằng Codex — 2026-11-16

> Date: 2026-11-16 (Asia/Saigon)  
> Status: Đã tạo và kiểm tra file cốt truyện thật; chưa nối Web hoặc triển khai Process engine.

## Input và output

- Chủ đề người dùng chỉ định: **Thật tệ khi làm mẹ đơn thân**.
- Skill nguồn: [0.tao_cot_truyen](../../tests/.agents/skills/0.tao_cot_truyen/SKILL.md), giữ nguyên nội dung.
- Runtime: Codex CLI 0.147.0, model `gpt-5.6-sol` đã kiểm chứng ở Chặng 1.
- Output: [cot truyen.txt](<../../tests/3.Thật tệ khi làm mẹ đơn thân/cot truyen.txt>), nằm trực tiếp trong thư mục người dùng chọn, không tạo thêm thư mục chủ đề lồng bên trong.
- Chỉ chạy Skill 0; chưa chạy Skill 1/2, chưa có Agent duyệt tự động hoặc UI chạy Process.

## Kết quả đã kiểm tra

File UTF-8 dài **10.773 byte**, có hệ thống nhân vật, đủ bốn điểm tương tác và dàn ý theo thứ tự Part 1–5. Đã mở đọc toàn bộ và kiểm tra tự động 11 điều kiện: encoding, chủ đề, các khối bắt buộc, đủ năm Part, file khớp phản hồi Codex, có `turn.completed`, không lỗi turn, Skill nguồn không đổi và thư mục đích chỉ chứa output dự kiến.

File là **dàn ý**, không phải bài hoàn chỉnh 2.800–3.500 từ. Số đếm theo khoảng trắng là 1.731; đây không phải phép nghiệm thu độ dài bài viết ở Skill 1. Chưa đánh giá chất lượng sáng tạo bằng một Agent duyệt độc lập.

## Cách điều phối thực tế

1. Kiểm tra thư mục đích có sẵn và trống; chụp nội dung Skill cùng hash vào thư mục log cục bộ.
2. Lần gọi đầu yêu cầu runtime đọc Skill rồi tự ghi file: đã đọc Skill và kiểm tra file chưa tồn tại, nhưng hết 240 giây chưa ghi. Một lần thử trước đó cũng phát hiện đường dẫn tiếng Việt bị PowerShell chuyển thành dấu hỏi khi truyền qua pipe ASCII; đã sửa encoding trước khi gửi yêu cầu hợp lệ.
3. Theo yêu cầu người dùng, tiếp tục đúng thread với chỉ đạo ghi bản dàn ý có nội dung trước, hoàn thiện sau. Lượt này cũng hết 180 giây mà chưa ghi. Đã dừng đúng các tiến trình Codex thử bị treo trước khi đổi cách gọi, không để chúng ghi muộn đè kết quả.
4. Tạo một phiên mới, chỉ yêu cầu Codex trả toàn bộ dàn ý theo Skill được nạp từ nguồn UTF-8; dùng `--output-last-message` để **CLI lưu phản hồi cuối vào file đích**. Không yêu cầu model tự gọi shell ghi file trong lượt này.
5. Lượt xuất file hoàn thành sau **53,2 giây**, exit 0, có `turn.completed`; file khớp chính xác phản hồi cuối của Codex sau khi bỏ khoảng trắng đầu/cuối. Nội dung do Codex sinh, không phải nội dung agent điều phối tự viết thay.

Lượt thành công dùng sandbox `read-only` cho các tool của model (model được yêu cầu không gọi tool); đường dẫn output do caller cấp cho CLI, không phải lệnh ghi nằm trong sandbox của model. Có `--ignore-user-config`, model chỉ định rõ và reasoning `low` cho lần gọi này; không sửa cấu hình global hoặc credential.

Điều đã chứng minh: điều phối được một yêu cầu Skill thực tế, nhận nội dung từ Codex và lưu artifact thật bằng giao diện xuất file CLI. Điều **chưa** chứng minh: model tự gọi tool ghi file thành công, một Process engine tổng quát, hoặc tự phục hồi/hủy cây tiến trình production.

## Hướng dẫn thực hiện lại

Lệnh dùng lại và cách truyền UTF-8 được giữ riêng tại [hướng dẫn CLI](../development/local-runtime-cli.md#cách-chạy-lại-bằng-cli). Báo cáo này chỉ lưu điều kiện, kết quả và giới hạn của lần kiểm chứng.

## Log cục bộ và truy vết

Run ID: `skill0-58026e18a712`. Log tại `runtime/skill-runs/skill0-58026e18a712/`, đã được Git bỏ qua:

- `request.json`, `SKILL.snapshot.md`, `prompt.txt`: input và phiên bản Skill nguồn.
- `events.jsonl`, `result.json`: lượt đầu bị timeout.
- `steering-prompt.txt`, `steering-events.jsonl`, `steering-result.json`: chỉ đạo tiếp tục đúng phiên và kết quả timeout.
- `direct-output-prompt.txt`, `direct-output-events.jsonl`, `direct-output-result.json`: lượt thành công, nội dung và trạng thái thực tế.
- `validation.json`: 11 điều kiện đã đạt, kích thước và hash output.

SHA-256 của output: `89363909e589f59b25d4d41977557466eff06d3cca5489b82cd9e0d7a642603d`.

Không đưa raw log, credential hoặc phiên đăng nhập vào Git. Artifact cốt truyện trong thư mục test là kết quả sáng tạo phục vụ review của người dùng.

## Lưu ý cho phần triển khai tiếp

- PowerShell 5 mặc định có thể truyền pipeline dạng ASCII. Khi gửi prompt hoặc mã qua stdin có tiếng Việt, cần đặt `$OutputEncoding = [System.Text.UTF8Encoding]::new($false)` hoặc dùng đường truyền UTF-8 đã kiểm chứng; không chỉ đặt `PYTHONIOENCODING`.
- Phân biệt runtime đã nhận yêu cầu, nội dung đang sinh, file đang có và kết quả đã được kiểm tra. Không báo task hoàn tất chỉ vì Agent nói sẽ ghi file.
- Timeout của wrapper không bảo đảm dừng chương trình con trên Windows. Lần thử đã đối chiếu đúng PID/câu lệnh để dừng; bộ quản lý tiến trình và chính sách đối soát còn phải thiết kế trước production.
- Không chạy lại mù khi output đã có; kiểm tra và giữ kết quả trước khi nhận một lần thực thi mới.
- Antigravity/Gemini chưa được thử Skill 0 cho chủ đề này: vướng lựa chọn model được ghi tại [báo cáo Chặng 1](local-runtime-check.md#thử-lựa-chọn-gemini-38-flash-high-cho-skill-0).

Nguồn tham khảo giao diện CLI: [OpenAI non-interactive mode](https://developers.openai.com/codex/noninteractive). Đây là thử nghiệm cục bộ, chưa phải API hoặc adapter production.
