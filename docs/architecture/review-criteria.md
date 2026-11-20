# Đặc tả Tiêu chí Duyệt và Vòng lặp Yêu cầu Sửa (AGN-001)

> Trạng thái: Accepted · Ngày cập nhật: 2026-11-16
> Áp dụng: Toàn bộ hệ thống Agent CF (Module Agents, Runs, Execution)

---

## 1. Bối cảnh & Mục tiêu

Trong hệ thống Agent CF, một TaskRun thành công không chỉ đơn thuần là tiến trình runtime thoát với mã 0 (`exit code 0`). Để đảm bảo chất lượng tác phẩm nội dung (đặc biệt trong các thể loại storytelling, kịch bản video, hoặc tài liệu chuyên môn), hệ thống cần một **cơ chế Agent Review độc lập**:
- Đánh giá nội dung dựa trên bộ tiêu chí định lượng và định tính cụ thể.
- Đưa ra quyết định có cấu trúc: Duyệt (`approved`), Yêu cầu sửa (`revision_requested`), hoặc Leo thang cần can thiệp (`escalated`).
- Giới hạn số lần sửa chữa tối đa (`max_revisions`) để tránh lặp vô hạn và lãng phí token/quota.
- Bảo toàn mọi artifact trung gian (checkpoint) trước và sau mỗi vòng sửa.
- Khử trùng quyết định (idempotent decision recording).

---

## 2. Tiêu chí Đánh giá Chất lượng (Review Criteria)

Tiêu chí duyệt được cấu hình linh hoạt theo từng Task/Skill, bao gồm:

### A. Định mức độ dài (Word Count Thresholds)
- **Part-level:** Mỗi Part trong bài viết phải đạt khung từ nhất định (ví dụ: Part 1 từ 500 – 800 từ; bài thử nghiệm tối thiểu 300 từ).
- **Document-level:** Toàn bài hoàn thiện phải nằm trong định mức (ví dụ: 2.800 – 3.500 từ).

### B. Ngôi kể & Điểm nhìn nhân vật (POV & Voice)
- Bắt buộc thống nhất ngôi thứ hai (**"Bạn"**) trong thể loại POV Dark Storytelling.
- Không tự chuyển sang ngôi thứ nhất ("Tôi") hoặc ngôi thứ ba khách quan nếu đề bài yêu cầu "Bạn".

### C. Cấu trúc Bẫy tương tác (Debate & Comment Hooks)
- Cài cắm thế tiến thoái lưỡng nan (Dilemma - Đúng hay Sai).
- Điểm tiếc nuối / cơ hội quay đầu bị bỏ lỡ.
- Câu hỏi mở thách thức người nghe ở cuối bài.

### D. Khử mùi AI & Chuẩn hóa văn phong (Anti-AI & Tone)
- Không dùng các câu sáo rỗng kinh điển của AI (*"Mọi chuyện bắt đầu từ...", "Đó là bài học đắt giá...", "Cuộc sống như một bức tranh..."*).
- Thay bằng giọng trần thuật sắc sảo, đời thực, cài cắm từ lóng ngành thực chiến (đã được tra cứu qua web search).

### E. Quy chuẩn định dạng cho TTS (ElevenLabs Readiness - Skill 2)
- Loại bỏ toàn bộ tiêu đề phân đoạn, vạch phân cách `====`, `----`, bảng số từ.
- Mỗi dòng/đoạn đọc khống chế tối đa **500 ký tự** (lý tưởng 200 – 450 ký tự).
- Dấu câu ngắt nhịp: `...`, `—` tạo biểu cảm mỉa mai, cà khịa.

---

## 3. Cấu trúc Dữ liệu Quyết định Duyệt (`ReviewDecision`)

Mỗi lần Agent thực hiện đánh giá sẽ sinh ra một bản ghi quyết định với cấu trúc chuẩn:

```json
{
  "id": "rev-decision-uuid",
  "task_run_id": "tr-12345",
  "attempt_id": "att-67890",
  "reviewer_agent_id": "ag-critic-1",
  "revision_round": 1,
  "decision": "approved | revision_requested | escalated",
  "score": 8.5,
  "feedback": "Cần tăng độ dài Part 1 lên tối thiểu 500 từ và bổ sung từ lóng tiền tệ 'tỏi', 'củ'.",
  "violations": [
    "word_count_insufficient: Part 1 has 320 words (required >= 500)",
    "missing_slang: Required slang terms not found"
  ],
  "decision_key": "dec-tr-12345-round-1",
  "created_at": "2026-11-16T16:15:00.000000Z"
}
```

---

## 4. Giới hạn Sửa chữa & Checkpoint Bảo toàn Artifacts

1. **Giới hạn số lần sửa (`max_revisions`):**
   - Mặc định: `max_revisions = 2`.
   - Nếu ở vòng `revision_round < max_revisions` có vi phạm tiêu chí $\to$ Ra quyết định `revision_requested` kèm `feedback` chi tiết để chuyển vào prompt vòng sau.
   - Nếu ở vòng `revision_round >= max_revisions` vẫn còn vi phạm $\to$ **Dừng vòng lặp ngay lập tức**, ra quyết định `escalated`.
   - TaskRun bị đánh dấu `failed` với mã lỗi `revision_limit_exceeded` và ghi nhận `attention_reason` để báo người vận hành can thiệp thủ công. Tuyệt đối không tự động retry vô hạn.

2. **Checkpoint & Bảo toàn Artifact:**
   - Mỗi vòng sửa (attempt) sinh ra file nội dung đều được lưu trữ và đăng ký artifact riêng biệt (ví dụ: `noi dung_round_1.txt`, `noi dung_round_2.txt`).
   - File của vòng trước không bị ghi đè mất dấu vết.
   - Với Skill 2 (Review nội dung): Lưu cả 3 thành phần:
     1. Bản trước review: `noi dung.txt` (nhận từ Skill 1).
     2. Bản sau review: `noi dung_reviewed.txt` (sạch tạp chất, ngắt dòng TTS).
     3. Báo cáo nghiệm thu: `audit_report.md` (chấm điểm so sánh và thống kê từ lóng).

3. **Chặn lỗi Downstream (Failure Isolation):**
   - Nếu một node (ví dụ Skill 1) không đạt và chuyển trạng thái `failed`, các node phụ thuộc ở hạ nguồn (ví dụ Skill 2) lập tức bị chuyển thành `skipped`.
   - Các node thượng nguồn đã thành công (Skill 0) và artifact của chúng vẫn giữ nguyên vẹn trạng thái `succeeded`.

4. **Khử trùng quyết định (Deduplication):**
   - Quyết định mang `decision_key` duy nhất. Gửi lại cùng `decision_key` sẽ nhận lại kết quả cũ nguyên vẹn, không sinh attempt mới hoặc tăng biến đếm vòng sửa.
