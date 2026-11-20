# Hướng dẫn chạy runtime local

> Type: Guide  
> Last updated: 2026-11-16

Cách gọi CLI được rút ra từ thử nghiệm local; chưa phải lệnh chạy ứng dụng Agent CF. Các giới hạn và kết quả đo được giữ ở [báo cáo runtime](../reports/local-runtime-check.md) và [báo cáo Skill 0](../reports/local-skill0-check.md).

## Cách chạy lại bằng CLI

Đây là công thức tái lập cách đã thành công, dùng tại **root repository trong Windows PowerShell**. Chỉ chạy khi người dùng đã yêu cầu tạo nội dung; lệnh gửi yêu cầu model thật. Ví dụ dùng lại đường dẫn test hiện có nên sẽ **dừng nếu file đã tồn tại**; khi thử lượt mới, chọn thư mục mới đã được người dùng chỉ định, không xóa output cũ để chạy lại.

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$skillPath = (Resolve-Path -LiteralPath 'tests/.agents/skills/0.tao_cot_truyen/SKILL.md').Path
$topicDirectory = (Resolve-Path -LiteralPath 'tests/3.Thật tệ khi làm mẹ đơn thân').Path
$outputPath = Join-Path $topicDirectory 'cot truyen.txt'
if (Test-Path -LiteralPath $outputPath) { throw 'File da ton tai; khong ghi de.' }

$logDirectory = Join-Path (Get-Location).Path ('runtime/skill-runs/' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$skillText = Get-Content -Raw -Encoding UTF8 -LiteralPath $skillPath
$taskPrompt = @"
Tạo dàn ý cốt truyện cho chủ đề: Thật tệ khi làm mẹ đơn thân.
Áp dụng Skill bên dưới: nhân vật, bốn điểm tương tác và đủ 5 Part có tình tiết cụ thể.
Chỉ tạo dàn ý; 2.800–3.500 từ là độ dài bài hoàn chỉnh tương lai, không phải yêu cầu viết bài ở lượt này.
Trả TOÀN BỘ nội dung file trong phản hồi cuối, không bọc code block, không chỉ báo đường dẫn.
CLI sẽ lưu phản hồi đó qua --output-last-message. Không gọi tool, tự ghi file, delegate hoặc chạy Skill 1/2.

$skillText
"@
$taskPrompt | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $logDirectory 'prompt.txt')

$cliArguments = @(
    '-a', 'never', '-s', 'read-only', '-c', 'model_reasoning_effort="low"',
    'exec', '--ignore-user-config', '--json', '-m', 'gpt-5.6-sol',
    '-C', $topicDirectory, '--output-last-message', $outputPath, '-'
)
$events = @($taskPrompt | & codex.cmd @cliArguments 2> (Join-Path $logDirectory 'stderr.log'))
$runtimeExitCode = $LASTEXITCODE
$events | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $logDirectory 'events.jsonl')
if ($runtimeExitCode -ne 0) { throw "Codex exit code: $runtimeExitCode" }

$parsedEvents = @($events | ForEach-Object { $_ | ConvertFrom-Json })
if (@($parsedEvents | Where-Object { $_.type -in @('error', 'turn.failed') }).Count -gt 0) {
    throw 'Runtime bao loi; can kiem tra log.'
}
if (@($parsedEvents | Where-Object { $_.type -eq 'turn.completed' }).Count -eq 0) {
    throw 'Chua co turn.completed.'
}
if (-not (Test-Path -LiteralPath $outputPath)) { throw 'Chua co file ket qua.' }
$outline = Get-Content -Raw -Encoding UTF8 -LiteralPath $outputPath
if ([string]::IsNullOrWhiteSpace($outline)) { throw 'File ket qua rong.' }
$parts = [regex]::Matches($outline, '(?m)^--- PART ([1-5]):')
if ((($parts | ForEach-Object { $_.Groups[1].Value }) -join ',') -ne '1,2,3,4,5') {
    throw 'Can doc lai: chua dung cau truc 5 Part.'
}
Get-Item -LiteralPath $outputPath | Select-Object FullName, Length
```

Đoạn PowerShell là công thức tương đương với lần gọi từ Python đã thành công; đã kiểm tra cú pháp nhưng **chưa gọi model lại chỉ để thử đoạn tài liệu này**. Khi dùng cho lượt thật vẫn phải đọc nội dung, kiểm tra đúng chủ đề, nhân vật và bốn điểm tương tác; có đủ heading chưa chứng minh chất lượng bài.

Các lựa chọn cần giữ rõ:

| Thành phần | Cách dùng và ý nghĩa |
|---|---|
| `codex.cmd` | Wrapper native đã dùng trên Windows; không cần chạy `codex.ps1` hoặc đổi Execution Policy |
| `-m gpt-5.6-sol` | Model đã kiểm chứng trên máy tại thời điểm thử; kiểm tra lại catalog/quyền khi đổi máy hoặc tài khoản |
| `--ignore-user-config` | Bỏ config người dùng cho lần exec mới này; không xóa config hoặc đăng nhập. Không coi mọi cấu hình/MCP từ IDE sẽ được kế thừa |
| `-c model_reasoning_effort="low"` | Effort của lượt thử xuất file, không thay thiết lập global |
| `--json` | Lưu sự kiện vào log để kiểm tra thành công/lỗi, lấy thread ID khi cần |
| `--output-last-message <file>` | CLI lưu phản hồi cuối thành file. Phản hồi phải là nội dung artifact, không phải câu “đã làm xong” |
| `-` cuối lệnh | Đọc prompt từ stdin; đường truyền cần UTF-8 để giữ chủ đề và đường dẫn tiếng Việt |
| `-s read-only` | Giới hạn tool của model; việc CLI xuất file theo đường dẫn caller chỉ định là cơ chế khác |

File thường chỉ xuất hiện khi có phản hồi cuối; đây không phải cơ chế stream dần nội dung ra artifact. Nếu cần lưu từng Part hoặc checkpoint của Skill 1, bộ điều phối phải thiết kế riêng, không gộp cả bài vào một lượt và bỏ khâu duyệt.

### Tiếp tục phiên và Antigravity

- Codex: lấy `thread_id` từ sự kiện `thread.started` của đúng lượt chạy, rồi dùng `codex.cmd -a never -s read-only exec resume --json -m gpt-5.6-sol <thread-id> -` với prompt mới qua stdin. Nếu cần output mới, chỉ định thêm `--output-last-message <file-moi>`; không dùng `--last` hoặc tự ghi đè artifact cũ. Kiểm chứng resume hiện có là Skill thử nhỏ, không phải vòng duyệt bài hoàn chỉnh.
- Antigravity: mở CMD tại workspace đã chọn → gõ `agy` → xác nhận trust đúng thư mục nếu được hỏi → nhập yêu cầu Skill. `/model` chọn trong danh sách CLI thực tế. `/exit` in ra ID của phiên; mở lại bằng `agy --conversation=<id-do>`. Cách tương tác và resume đã đạt với Claude Sonnet 4.6 (Thinking); **print/pipe và lựa chọn Gemini vẫn chưa đạt** ở phép thử hiện tại. Không coi danh sách model trong IDE là bằng chứng CLI nhận cùng tên/ID.
- Bằng chứng và giới hạn runtime được giữ tại [báo cáo Chặng 1](../reports/local-runtime-check.md); không dùng cờ bypass permission để giải quyết vấn đề transport hoặc model.

### Khi chờ lâu hoặc chưa có file

Kiểm tra log có tiến triển, lỗi hoặc `turn.completed` hay chưa; chưa có file thì chưa báo xong. Hai lượt “yêu cầu model tự gọi tool ghi file” đã timeout, nhưng nguyên nhân gốc **chưa được xác định**; không kết luận Codex không có khả năng ghi file. Phương án xuất phản hồi cuối thành artifact ở trên là cách đã thành công cho Skill 0.

Muốn gửi chỉ đạo mới, phải quản lý đúng thread và trạng thái lượt hiện tại. `exec` một lần không phải kênh chat tương tác để cứ gửi thêm stdin giữa lượt. Không mở thêm lượt ghi cùng file khi lượt cũ có thể còn hoạt động. Nếu timeout, cần kiểm tra và dừng/đối soát đúng cây tiến trình trước khi thử lại; không kill tất cả tiến trình Codex của máy. Công thức PowerShell ở trên chờ lệnh kết thúc, **chưa cung cấp watchdog hoặc quản lý timeout/cây tiến trình**; phần đó vẫn phải triển khai trong Client.

