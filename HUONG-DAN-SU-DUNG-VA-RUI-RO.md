# Hướng Dẫn Sử Dụng `tool_data_labelling` — Tối Ưu, Rủi Ro & Khắc Phục

**Đối tượng:** Intern annotation Vivipedia (Vòng 2)  

---

## 1. Tool này dùng để làm gì?

`tool_data_labelling` **không thay** vai trò fact-check của intern, mà **thay phần việc máy móc** trong quy trình onboarding:

- Trích claim từ PDF  
- Trích URL từ Ref PDF  
- Gửi prompt + URL cho Claude  
- Ghi Excel chuẩn (không paste tay) — sheet **Annotation** (18 cột) + **Article Evaluation** (Rel/Comp)  
- Pre-label SF/SQ/TXT + gợi ý draft SC/HR  
- Validate `sub_domain_id` theo bảng 69 sub-domain (file tham chiếu Vivipedia TA v13.5)  

Intern vẫn làm **đúng phần mục 2.2 onboarding**: điền **G, H, J, K** và cập nhật **Notes SC/HR** — nhưng bắt đầu từ file đã có sẵn khung, không từ file trống.

---

## 2. Tối ưu gì hơn quy trình onboarding?

### 2.1 Ánh xạ 9 bước onboarding → dùng tool

| Bước onboarding | Thủ công (báo cáo) | Với `tool_data_labelling` |
|-----------------|-------------------|---------------------------|
| **1** Nhận bài → PDF | Intern lưu PDF | Giữ nguyên — kéo PDF vào GUI |
| **2** Chuẩn bị prompt + template | Mở nhiều file | Tool load `rule_prelabel.md` (Pre-label) hoặc `prompt.md` (Full) — rubric v10 khớp TA 13.5 |
| **3** Extract URL (`pdf_url_extractor`) | Chạy script riêng | **Tự động** trong pipeline + verify URL |
| **4** Gửi AI (upload prompt + PDF + URL) | Thao tác tay ChatGPT/Claude | **Một nút RUN PRE-LABEL** |
| **5** AI xử lý 3–6 phút | Chờ + tải .xlsx | Chờ trong GUI, log từng stage |
| **6** Merge Excel (Paste Special) | **Rủi ro lệch dòng cao** | **Bỏ hẳn** — ghi thẳng `outputs/annotation_output.xlsx` |
| **7** Fact-check G/H/J/K + Notes | 15–20 phút/claim | **8–15 phút/claim** (review + sửa draft, không setup lại) |
| **8** Review trong template | Checklist 10 mục tay | Thêm `validator.py --strict` |
| **9** Nộp batch | Lưu + Slack | Giữ nguyên |

### 2.2 Giải quyết từng “bất cập” trong báo cáo onboarding (mục 4)

| Bất cập onboarding | Tool giúp thế nào |
|---------------------|-------------------|
| **4.1** Fact-check tốn 15–20 phút/claim | Bớt setup; có SF/SQ/TXT + `DRAFT_SC`/`DRAFT_HR` làm baseline; intern tập trung mở URL và chốt G/H/J/K |
| **4.2** Merge Excel dễ lệch | Không còn bước paste; **chặn ghi file** nếu số claim script ≠ Claude |
| **4.3** SC/HR = 0.00, không baseline | Pre-label có draft trong Notes; cột P (Evidence) gợi ý đoạn nguồn |
| **4.4** Format Notes dễ sai | `notes_formatter` chuẩn hóa **5 dòng** `SF=`/`SC=`/`HR=`/`SQ=`/`TXT=`; validator báo thiếu key |
| **4.7** Sub-domain / domain sai ID | AI chọn nhầm `law_03` vs tên hiển thị | `domain_registry` + cảnh báo khi `sub_domain_id` lệch bảng |
| **4.8** Rel/Comp chỉ trong đầu | Thiếu sheet Article Evaluation | Tool ghi thêm sheet **Article Evaluation** (Rel, band, lý do 3–5 câu) |
| **4.5** Không phản hồi sớm | `validator.py` báo lỗi **ngay sau khi làm xong**, trước QA |
| **4.6** URL index/404 không ổn định | `url_verifier` báo `document` / `index` / `error` trước khi intern mở tay |

### 2.3 Ước lượng tiết kiệm thời gian (bài ~15 claim)

| Khâu | Onboarding thủ công | Với tool |
|------|---------------------|----------|
| Setup + extract + gửi AI + merge Excel | ~45–90 phút | ~10–15 phút (+ chờ Claude) |
| Fact-check / claim | ~15–20 phút × 15 | ~8–15 phút × 15 (review draft) |
| Sửa lỗi paste / format | Khó ước tính | Giảm mạnh |
| **Tổng/bài** | **~4–5 giờ** | **~2.5–4 giờ** (tùy độ khó bài) |

> Tool tiết kiệm chủ yếu ở **bước 2–6**, không loại bỏ **bước 7** (trách nhiệm Vòng 2).

### 2.4 Vẫn đúng mô hình 3 vòng Vivipedia

```
Vòng 1 (AI)     →  RUN PRE-LABEL  →  SF/SQ/TXT + draft, G = placeholder
Vòng 2 (Intern) →  Fact-check     →  G/H/J/K, P/Q/R, Notes SC/HR
Vòng 3 (QA)     →  Spot-check 20% →  Không đổi
```

Chế độ **Pre-label** (mặc định) được thiết kế **khớp onboarding**: cột G luôn là `[INTERN: chưa fact-check]` cho đến khi intern điền.

---

## 3. Quy trình sử dụng chuẩn (SOP)

### Bước 0 — Cài đặt (một lần)

```bash
cd tool_data_labelling
pip install -r requirements.txt
playwright install chromium
```

### Bước 1 — Mở Chrome + login Claude

```bash
python login_claude.py
```

Đăng nhập [claude.ai](https://claude.ai). **Không đóng Chrome** trong phiên làm việc.

### Bước 2 — Chạy Pre-label

```bash
python main.py
```

1. Kéo **PDF bài viết** (trái) + **PDF Ref** (phải)  
2. Chọn **Chế độ: Pre-label (Vòng 1)**  
3. Điền **Annotator ID** (vd. `ANT-01`)  
4. Bấm **▶ RUN PRE-LABEL**  
5. Kết quả: `outputs/annotation_output.xlsx` gồm:
   - **Annotation** — claim từng dòng (cột A–O theo template v10; **P–R** là cột review của tool)
   - **Article Evaluation** — 1 dòng/bài: Rel, Rel Band, nhận xét; Comp, Comp Band, nhận xét (band tự tính nếu AI thiếu)

> File tham chiếu TA (Domain list, Scoring Guide, …) nên giữ trong thư mục tool để `domain_registry` load đúng 69 sub-domain.

### Bước 3 — Intern fact-check (Vòng 2)

Mở Excel, **từng claim**:

| Cột | Việc cần làm |
|-----|--------------|
| **G** | Thay placeholder → **đúng 1** trong 6 status: `XAC NHAN`, `LECH`, `MAU THUAN`, `OUTDATED`, `KHONG TIM THAY`, `BO QUA` — **không** ghi giải thích dài vào G (chi tiết → cột M Notes) |
| **H** | URL đầy đủ từ Ref; nhiều URL → **mỗi URL một dòng** trong cùng ô |
| **J, K** | SC, HR (HR thang đảo ngược — mục 2.2 onboarding) |
| **M** | Sửa `DRAFT_SC=` → `SC=`, `DRAFT_HR=` → `HR=`; giữ SF/SQ; đủ **TXT=** (vd. `TXT=OK: Không có lỗi`) |
| **C, D, E** | Kiểm tra Domain / Sub-domain / `sub_domain_id` khớp bảng (tool cảnh báo nếu lệch) |
| **P** | Trích dẫn ngắn từ URL thật (≤200 ký tự) |
| **Q** | `Y` nếu đã mở URL và xác nhận load được; `N` nếu 404/block |
| **R** | Đặt `Y` (hoặc `Y ANT-01 2026-05-29`) khi **đã review xong claim đó** |

**Checklist tối thiểu mỗi bài:**

- [ ] 100% claim có `R = Y`  
- [ ] Mọi `XAC NHAN` đã mở URL cột H  
- [ ] Claim pháp luật/y tế khó — đọc kỹ case SC index (như bài ODA mục 3.2 onboarding)
- [ ] Sheet **Article Evaluation**: Rel/Comp và nhận xét đã khớp nội dung bài (intern có thể sửa tay sau Pre-label)

### Bước 4 — Validate trước nộp

```bash
python validator.py -f outputs/annotation_output.xlsx --strict
```

Chỉ nộp batch khi **0 lỗi**.

### Bước 5 — Nộp (bước 9 onboarding)

Lưu file, compile batch, báo Slack — theo hướng dẫn team.

---

## 4. Cảnh báo rủi ro khi dùng tool

### 4.1 Rủi ro nội dung (quan trọng nhất)

| Rủi ro | Mô tả | Mức |
|--------|--------|-----|
| **Hallucination Claude** | AI ghi Notes/ Evidence nghe hợp lý nhưng không có trên URL | Cao |
| **Tin nhầm draft** | Intern thấy file “đầy cột” → bỏ qua bước mở URL | Cao |
| **SC cao + trang index** | Giống case ODA: nguồn chỉ là danh mục, SC phải hạ xuống ~0.25 | Cao (law) |
| **HR hiểu ngược** | HR cao = an toàn; HR thấp = nguy cơ — dễ nhầm với metric thường | Trung bình |

**Tool không tự phát hiện sai nội dung** — chỉ phát hiện lỗi format, placeholder, URL ngoài Ref, claim lệch, domain/sub-domain ID, status G không chuẩn (kể cả khi `--strict` báo giải thích dài trong cột G).

### 4.2 Rủi ro kỹ thuật

| Rủi ro | Dấu hiệu | Mức |
|--------|----------|-----|
| PDF scan ảnh | 0 claims, tiêu đề Untitled | Cao |
| Chrome/CDP lỗi | “port 9222”, không connect | Trung bình |
| Claude timeout / JSON lỗi | Response rỗng, `debug_screenshot.png` | Trung bình |
| Số claim lệch | Pipeline dừng, không ghi Excel | Trung bình (có chủ đích) |
| Ref PDF không hyperlink | 0 URL, cảnh báo stage 2 | Trung bình |
| URL verify FAIL hàng loạt | Log stage 2b toàn FAIL | Trung bình |
| Excel đang mở | PermissionError khi ghi | Thấp |

### 4.3 Rủi ro quy trình

| Rủi ro | Mô tả |
|--------|--------|
| Nộp khi còn placeholder G | Quên chạy `--strict` |
| Dùng chế độ **Full** mà không review | AI tự điền XAC NHAN — nguy hiểm nếu không kiểm |
| Nhiều intern cùng append 1 file Excel | Lẫn batch — nên tách file theo bài/batch |

---

## 5. Cách khắc phục — bảng tra nhanh

### 5.1 Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách khắc phục |
|-------------|-------------|----------------|
| Không connect Chrome (9222) | Chưa chạy `login_claude.py` hoặc đóng Chrome | Chạy lại `login_claude.py`, giữ cửa sổ mở |
| Claude chưa login | Tab auth | Login claude.ai trong Chrome đó, RUN lại |
| 0 claims | PDF không có text layer | Dùng PDF export text, không dùng scan ảnh |
| Pipeline dừng “Số claim lệch” | Claude trả ≠ số paragraph script | Kiểm tra PDF; chạy lại; nếu lặp — báo mentor |
| JSON parse lỗi | Claude trả text thay JSON | Tool retry 3 lần; xem log + screenshot; RUN lại |
| PermissionError Excel | File đang mở | Đóng Excel; tool lưu file backup có timestamp |
| Ref 0 URL | Ref PDF không có hyperlink | Xuất lại Ref có link; hoặc chấp nhận KHONG TIM THAY nhiều claim |
| URL verify toàn FAIL | Block, 404, paywall | Fact-check tay; cột Q = N; status phù hợp |
| Validator `--strict` fail placeholder | Chưa điền cột G | Hoàn thành fact-check từng claim |
| Validator fail cột R | Chưa đặt Intern Reviewed = Y | Tick review từng claim đã fact-check |
| Validator fail Evidence (P) với XAC NHAN | Thiếu trích dẫn URL | Copy đoạn ngắn từ trang nguồn vào cột P |
| SC/HR = 0.00 khi strict | Chưa điền J/K | Điền điểm sau khi đọc nguồn |
| Validator fail Notes thiếu `TXT=` | Chỉ 4 dòng SF/SC/HR/SQ | Thêm dòng `TXT=OK: ...` hoặc `TXT=LỖI: ...` |
| Validator fail Domain | `sub_domain_id` sai hoặc lệch tên | Tra bảng Domain trong template / file `Domain-Subdomain List.csv` |
| `--strict` báo cột G có text dài | Ghi `LECH — Điều 13...` vào G | Chỉ để `LECH` ở G; phần giải thích chuyển sang Notes |
| Claude trả status dài trong JSON | Full mode | Tool tự tách status → G, chi tiết → đầu Notes — intern vẫn nên rà lại |

### 5.2 Khi nghi ngờ output AI

Làm **5 bước kiểm tra claim**:

1. Mở URL cột **H** (hoặc nguồn [1][2] trong bài).  
2. So sánh với **cột F** (claim) — nội dung có khớp không?  
3. Trang là **văn bản** hay **index/danh mục**? (index → SC thấp, xem mục 3.2 onboarding).  
4. Search thêm nguồn domain ưu tiên → chốt **HR**.  
5. Cập nhật **P, Q, R** — chỉ `XAC NHAN` khi chắc chắn.

### 5.3 Khắc phục rủi ro hallucination (bắt buộc team)

| Biện pháp | Ai | Khi nào |
|-----------|-----|---------|
| Luôn dùng **Pre-label**, không nộp thẳng sau RUN | Intern | Mọi bài |
| Chạy `validator.py --strict` | Intern | Trước mỗi lần nộp |
| Spot-check 100% claim `XAC NHAN` | Intern | Mỗi bài |
| Spot-check 30% claim còn lại | Intern | Mỗi bài |
| Mentor review batch đầu tuần | Mentor | Tuần đầu dùng tool |
| Không dùng output tool làm ground truth training | Team | Luôn |

---

## 6. Chế độ Full — khi nào dùng, cảnh báo gì?

| | Pre-label (khuyến nghị) | Full |
|---|-------------------------|------|
| AI điền G/H/J/K | Không — placeholder | Có |
| Phù hợp onboarding | Có | Chỉ khi mentor cho phép |
| Rủi ro hallucination | Thấp hơn | **Cao hơn** |
| Bắt buộc sau RUN | Fact-check intern | **Review 100%** + `--strict` |

**Không** chuyển sang Full chỉ để “nhanh hơn” mà bỏ review.

---

## 7. Cột Excel — intern cần nhớ

### Sheet Annotation

| Cột | Tên | Sau Pre-label | Sau intern (nộp) |
|-----|-----|---------------|------------------|
| A–F | Identity + Claim | Điền tự động | Claim nguyên văn từ PDF |
| G | Fact-check Status | `[INTERN: chưa fact-check]` | Một trong 6 status (không kèm giải thích dài) |
| H | Fact-check Source URL | Trống | URL Ref; nhiều URL xuống dòng |
| I–L | SF, SC, HR, SQ | SF/SQ có; J/K = 0 | SC, HR sau fact-check |
| M | Annotator Notes | Có `DRAFT_SC`/`DRAFT_HR` | Đủ 5 dòng `SF=` … `TXT=` |
| N–O | Annotator ID, Date | AUTO + ngày | Giữ hoặc sửa ID |
| **P–R** | **Review (tool)** | Evidence draft, Q từ script | P trích URL; Q xác nhận load; **R = Y** |

> **A–O** = template Vivipedia v10 (nộp TA). **P–R** = cột mở rộng của tool để chứng minh review — không có trên file TA gốc nhưng bắt buộc trước nộp nội bộ (`--strict`).

### Sheet Article Evaluation (1 dòng / bài)

| Cột | Nội dung |
|-----|----------|
| Rel, Rel Band | Điểm + band (Excellent … Block) — trả lời đúng tiêu đề? |
| Nhận xét Relevance | 3–5 câu |
| Comp, Comp Band | Điểm + band — bao phủ đủ khía cạnh? |
| Nhận xét Completeness | 3–5 câu, nêu phần thiếu |

Intern có thể **sửa tay** sheet này sau Pre-label nếu AI chấm Rel/Comp chưa đúng.

---

## 8. Lệnh tham khảo nhanh

```bash
# Phiên làm việc
python login_claude.py
python main.py

# Sau fact-check
python validator.py -f outputs/annotation_output.xlsx --strict

# Format Notes thủ công (tùy chọn)
python notes_formatter_cli.py
```

---

## 9. Tóm tắt

**`tool_data_labelling` tối ưu so với onboarding** bằng cách:

- Gom bước 2–6 (extract, prompt, AI, merge Excel) vào một pipeline có kiểm soát.  
- Rubric `prompt.md` / `rule_prelabel.md` căn theo **Vivipedia TA v13.5** (69 sub-domain, Scoring Guide, Notes 5 dòng).  
- Ghi **Annotation + Article Evaluation**; validate domain ID và format status/Notes.  
- Cung cấp draft SF/SQ/Notes và verify URL sớm.  
- Thêm validator và cột P/Q/R để intern **chứng minh đã review**, không chỉ “điền cho đủ cột”.  

**Rủi ro lớn nhất** vẫn là **sai fact-check / tin AI** — khắc phục bằng **Pre-label + fact-check tay + `--strict`**, không bỏ Vòng 2.

**Nguyên tắc một câu:** Tool là bàn làm việc có draft; **intern là người ký chất lượng** trước khi nộp QA.

---

