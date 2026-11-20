---
name: 2.review_noi_dung
description: Đọc, rà soát, khử mùi AI và tối ưu hóa file <Tên chủ đề>/noi dung.txt thành kịch bản đọc hoàn hảo cho ElevenLabs (tự động tra cứu từ lóng & trend mới trên mạng, ngắt dòng dưới 500 ký tự, dấu câu biểu cảm châm biếm cà khịa, nói lái né từ kiểm duyệt, giữ trọn câu hỏi kích nổ comment), đồng thời xuất báo cáo nghiệm thu chi tiết có chấm điểm trước và sau khi sửa.
---

# Kỹ năng: 2.review_noi_dung

Kỹ năng này chịu trách nhiệm "độ xe" và đánh bóng toàn diện file **`<Tên chủ đề>/noi dung.txt`**. 

Nhiệm vụ cốt lõi: **Chủ động tra cứu (Search Web)** các từ lóng đặc thù của chính ngành nghề đó và các hot trend mới nhất trên mạng, sau đó thay thế vào bài để biến văn bản thô thành một kịch bản đậm chất đường phố, sạch bóng mùi văn mẫu AI, ngắt nhịp chuẩn xác cho **ElevenLabs** phát âm giàu biểu cảm, và cuối cùng xuất bản **Báo cáo Nghiệm thu Trước/Sau**.

---

## 1. Quy trình thực hiện chuẩn 5 bước

### BƯỚC 0: ĐI THỰC TẾ TRÊN MẠNG (BẮT BUỘC TRA CỨU TỪ LÓNG & TREND)
Trước khi chỉnh sửa văn bản, Agent bắt buộc phải sử dụng công cụ tìm kiếm web (`search_web`) để tra cứu:
1. `Tiếng lóng / từ lóng + [tên chủ đề hoặc nghề nghiệp trong bài]` (Ví dụ: *từ lóng tài xỉu*, *từ lóng giới xăm mình*, *tiếng lóng dân bay lắc*, *tiếng lóng bất động sản*...).
2. `Hot trend meme mạng xã hội giới trẻ mới nhất` (để cập nhật các câu cảm thán, trào lưu đang sốt).
👉 Thu hoạch ít nhất **5 đến 10 từ lóng và cụm từ thực chiến đắt giá** để sẵn sàng đưa vào bài.

---

### BƯỚC 1: XÓA SẠCH TẠP CHẤT (ZERO-CLUTTER FOR TTS)
ElevenLabs sẽ đọc to mọi ký tự nhìn thấy trên màn hình. Do đó, loại bỏ hoàn toàn:
- Các tiêu đề: `TIÊU ĐỀ: ...`, `Chủ đề: ...`.
- Các vạch ngăn cách: `====================`, `--------------------`.
- Các thẻ phân đoạn: `PART 1: ...`, `--- PART 2 ---`.
- Bảng tổng kết số từ, thời lượng ước tính ở đầu/cuối file.
- **Chỉ giữ lại duy nhất:** Văn bản lời đọc thuần túy từ câu đầu tiên đến câu hỏi kích nổ bình luận cuối cùng.

---

### BƯỚC 2: KHỬ MÙI AI & THAY THẾ TỪ LÓNG THỰC CHIẾN
1. **Khử mùi AI (Anti-AI):**
   - Quét sạch các câu triết lý sáo rỗng, sến sẩm (*"Mọi thứ bắt đầu khi..."*, *"Đó là bài học đắt giá..."*).
   - Thay bằng giọng trần thuật sắc lạnh, xấc xược, mỉa mai, mang hơi thở đường phố.
2. **Thay thế bằng từ lóng vừa tra cứu:**
   - Đưa các từ lóng đặc thù ngành vừa search ở Bước 0 vào đúng ngữ cảnh để câu chuyện có "mùi đời".
   - Chuẩn hóa từ lóng tiền tệ: Bắt buộc dùng `tỏi`, `lốp`, `củ`, `cắt phế`, `bắn cọc`, `ting ting` thay cho từ đếm sách vở (tỷ, triệu).
3. **Nói lái & Biến âm né kiểm duyệt (Bypass Filter):**
   - Thay các từ nhạy cảm dễ bị nền tảng "bóp tương tác" bằng cách nói lái hoặc từ lóng tếu táo:
     - Tình dục / Bán thân $\to$ *bán trôn, đi khách kín, chăm sóc tới bến, lên giường đổi cọc, phục vụ từ A đến Z...*
     - Bạo lực / Đánh ghen $\to$ *tẩn ghen, xé đầm xé áo, ăn đòn hội đồng, dằn mặt...*
     - Chất cấm / Cờ bạc $\to$ *lên mây, cắn kẹo, đồ chơi, đỏ đen...*

---

### BƯỚC 3: TỐI ƯU HÓA CHO GIỌNG ĐỌC ELEVENLABS
1. **Khống chế độ dài mỗi dòng (Max 500 ký tự / dòng):**
   - Mỗi đoạn/dòng lý tưởng từ **200 đến 450 ký tự** (tuyệt đối không dòng nào vượt quá **500 ký tự**).
   - Không ngắt dòng quá ngắn (dưới 50 ký tự) để tránh ElevenLabs mất ngữ cảnh trước/sau.
   - Luôn ngắt dòng ở cuối câu hoàn chỉnh.
2. **Cài cắm dấu câu điều khiển nhịp thở "Cà khịa / Mỉa mai":**
   - Thêm dấu `...` ở các đoạn ngập ngừng, chua chát, nén thở dài hoặc tạo khoảng lặng "troll" (drop beat).
   - Thêm dấu gạch ngang `—` cho các câu chêm xen bất ngờ.
   - Phiên âm các từ tiếng Anh và thuật ngữ để ElevenLabs đọc chuẩn tiếng Việt (ví dụ: `Lếch-xù`, `Kia Mo-ning`, `Mát-đa`, `tiêm phi-lơ`, `quy hoạch một phần năm trăm`...).
3. **Giữ trọn câu hỏi kích nổ Comment:**
   - Đảm bảo câu kết thúc bài viết giữ nguyên tính chất thách thức, chọc đúng vào "chỗ ngứa" của người xem để kích thích họ gõ phím tranh luận ngay lập tức.

---

### BƯỚC 4: CẬP NHẬT FILE & XUẤT BÁO CÁO NGHIỆM THU
Ghi đè nội dung sạch vào file **`<Tên chủ đề>/noi dung.txt`**, sau đó xuất bản báo cáo theo mẫu chuẩn dưới đây:

```markdown
### 📊 BÁO CÁO NGHIỆM THU NỘI DUNG (POST-REVIEW AUDIT)

#### 1. Bảng chấm điểm chất lượng (Thang điểm 10):
| Tiêu chí | Trước khi sửa | Sau khi sửa | Đánh giá & Nhận xét |
| :--- | :---: | :---: | :--- |
| **Khử mùi văn mẫu AI** | .../10 | **.../10** | [Đã sạch bóng sáo rỗng, dùng khẩu ngữ đường phố] |
| **Độ chạm & Đánh vào cảm xúc** | .../10 | **.../10** | [Tức tối, cay đắng, xót xa, rùng mình] |
| **Độ bắt Trend & Từ lóng** | .../10 | **.../10** | [Từ lóng thực chiến vừa search + meme cõi mạng] |
| **Chuẩn giọng đọc ElevenLabs** | .../10 | **.../10** | [Dưới 500 ký tự/dòng, cài dấu ngắt nhịp thở] |

#### 2. Chỉ số kỹ thuật cho giọng đọc TTS:
- **Tổng số dòng/đoạn:** [X] dòng
- **Độ dài dòng ngắn nhất:** [X] ký tự
- **Độ dài dòng dài nhất:** [X] ký tự *(Tuyệt đối không vượt quá 500 ký tự)*
- **Tổng số từ:** [X] từ (~[X] ký tự)
- **Thời lượng đọc ước tính:** ~[X] phút

#### 3. Danh mục Trend & Từ lóng thực tế (Đã tra cứu Web & Lồng ghép):
- **Từ khóa đã Search:** `[Các cụm từ đã tìm kiếm trên mạng]`
- **Từ lóng đặc thù ngành áp dụng:** [Liệt kê các từ lóng vừa tìm được và đã đưa vào]
- **Meme & Hot trend cõi mạng:** [Liệt kê các meme: flexing, phông bạt, kiếp nạn 82, chữa lành...]
- **Nói lái & Né từ kiểm duyệt:** [Liệt kê các từ: bán trôn, đi khách kín, tẩn ghen...]

#### 4. Minh họa lột xác (Before vs. After):
- **Trước khi sửa (Mùi AI / Sách vở):** 
  > *"[Trích dẫn câu cũ mang hơi hướng sáo rỗng hoặc hiền lành]"*
- **Sau khi sửa (Đời thực / Đậm chất đường phố):** 
  > *"[Trích dẫn câu mới sắc sảo, dùng từ lóng và trào phúng]"*

#### 5. Kiểm tra bẫy Comment (Comment Hook):
- **Câu hỏi chốt hạ cuối bài:**
  > *"[Trích nguyên văn câu kết kích nổ tranh luận]"*
```
