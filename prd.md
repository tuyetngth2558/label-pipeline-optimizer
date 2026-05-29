# PRD — Label Pipeline Optimizer  
## Hệ thống hỗ trợ Annotation RAG cho Vivipedia

**Phiên bản:** 1.0  
**Dự án:** Vivipedia AI Annotation — Vinsmart Future (VSF)  

---

# 1. Tổng quan sản phẩm

## 1.1 Tên sản phẩm

**Label Pipeline Optimizer** — công cụ Python + GUI hỗ trợ intern annotation dataset RAG tiếng Việt cho nền tảng Vivipedia.

## 1.2 Bối cảnh

Vivipedia là nền tảng tri thức do VSF xây dựng, trong đó AI tự động tạo bài viết trả lời câu hỏi người dùng từ nhiều nguồn internet. Do AI có thể trích sai nguồn, dùng thông tin cũ hoặc hallucination, dự án cần quy trình **Human–AI Collaboration** để kiểm soát chất lượng trước khi phục vụ người dùng thực.

Hệ thống annotation được thiết kế theo **3 vòng**:

| Vòng | Người thực hiện | Nội dung |
|------|-----------------|----------|
| Vòng 1 | AI | Pre-label: trích claim, chấm SF/SQ/TXT, gợi ý domain |
| Vòng 2 | Intern | Fact-check: điền G, H, J, K; cập nhật Notes SC/HR |
| Vòng 3 | QA | Spot-check ngẫu nhiên ~20% claim/batch |

## 1.3 Vấn đề cần giải quyết

Quy trình thủ công hiện tại (9 bước/bài) gặp các bottleneck:

| # | Vấn đề | Hệ quả |
|---|--------|--------|
| P1 | Extract claim + URL + gửi AI + merge Excel **làm tay** | ~45–90 phút/bài cho phần setup, dễ sai |
| P2 | Bước **Paste Special → Values** vào template | Lệch dòng khi số claim AI ≠ template; lỗi phát hiện muộn ở QA |
| P3 | SC/HR để placeholder `0.00` — intern tính từ đầu | Không baseline; chất lượng không đồng đều giữa intern |
| P4 | Format Notes 5–6 dòng dễ sai | Khó parse dataset; QA mất thời gian sửa format |
| P5 | Fact-check 15–20 phút/claim | Bài 15 claim ≈ 4–5 giờ; annotation fatigue sau claim 8–10 |
| P6 | URL nguồn AI không ổn định (index, 404) | Intern khó đánh giá SC; case điển hình: SC 0.80 → 0.25 khi nguồn chỉ là trang danh mục |
| P7 | Không có feedback loop trước khi nộp | Lỗi format/thiếu cột chỉ phát hiện khi QA |

## 1.4 Mục tiêu sản phẩm

Xây dựng pipeline **semi-automation** giúp intern:

1. **Rút ngắn** bước extract → prompt → Excel (bước 2–6 trong quy trình 9 bước).
2. **Giữ nguyên** trách nhiệm fact-check Vòng 2 — tool không thay intern chốt chất lượng.
3. **Giảm rủi ro** lỗi kỹ thuật (lệch claim, URL bịa, format Notes).
4. **Tăng khả năng kiểm tra** trước nộp batch (validator tự động).

## 1.5 Nguyên tắc thiết kế

- **AI = draft, Intern = chịu trách nhiệm** — không coi output tool là ground truth.
- **Pre-label mặc định** — cột fact-check (G, H) để placeholder cho đến khi intern điền.
- **Verify URL bằng script** — không tin hoàn toàn Claude đã fetch được trang.
- **Fail-safe** — chặn ghi Excel khi số claim script ≠ Claude; validator `--strict` trước nộp.

## 1.6 Out of scope (v1)

- Web dashboard thay Excel
- Multi-user / database / queue
- Cloud deployment
- AI fact-check hoàn toàn không cần intern
- Inter-annotator agreement tự động (Cohen's Kappa)
- API Claude trả phí (dùng Claude Web qua browser)

---

# 2. Người dùng & use case

## 2.1 Personas

| Persona | Nhu cầu |
|---------|---------|
| **Intern annotator (Vòng 2)** | Làm nhanh phần setup; tập trung fact-check G/H/J/K; file Excel đúng format |
| **QA** | Nhận batch ít lỗi format/lệch dòng; có cột evidence + intern reviewed |
| **Mentor / Lead** | Tool không phá mô hình 3 vòng; có log và validator để audit |

## 2.2 Use case chính

### UC-01 — Pre-label một bài (happy path)

**Actor:** Intern  
**Precondition:** Đã cài Python, Chrome, login Claude  
**Flow:**

1. Intern lưu PDF bài viết + PDF Ref từ Vivipedia platform.
2. Chạy `login_claude.py` → mở Chrome CDP.
3. Mở GUI → kéo 2 PDF → chọn **Pre-label** → RUN.
4. Tool parse claim, verify URL, gửi Claude, ghi Excel (Annotation A–R + Article Evaluation).
5. Intern fact-check từng claim → điền G/H/J/K, P/Q/R.
6. Chạy `validator.py --strict` → nộp batch.

**Postcondition:** File Excel sẵn sàng QA; mọi claim có `intern_reviewed = Y`.

### UC-02 — Validator bắt lỗi trước nộp

**Actor:** Intern  
**Flow:** Intern chạy `--strict` → nhận danh sách claim thiếu SC/HR, placeholder G, thiếu evidence → sửa → chạy lại đến khi pass.

### UC-03 — Pipeline dừng khi claim lệch

**Actor:** Hệ thống  
**Trigger:** Số claim Claude trả về ≠ số paragraph script trích xuất  
**Kết quả:** Không ghi Excel; log cảnh báo; intern kiểm tra PDF hoặc chạy lại.

---

# 3. Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────────┐
│                     GUI (Tkinter) — main.py                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
┌─────────────┐      ┌───────────────┐       ┌─────────────────┐
│ pdf_parser  │      │  ref_parser   │       │  url_verifier   │
│ (PyMuPDF)   │      │  (hyperlinks) │       │  (requests)     │
└──────┬──────┘      └───────┬───────┘       └────────┬────────┘
       │                     │                          │
       └─────────────────────┼──────────────────────────┘
                             ▼
                   ┌──────────────────┐
                   │  prompt_builder  │
                   │ rule_prelabel.md │
                   │    prompt.md     │
                   └────────┬─────────┘
                            ▼
                   ┌──────────────────┐
                   │claude_automation │
                   │ Playwright CDP   │
                   └────────┬─────────┘
                            ▼
                   ┌──────────────────┐
                   │ response_parser  │
                   │ claim_constraints│
                   │ notes_formatter  │
                   └────────┬─────────┘
                            ▼
                   ┌──────────────────┐
                   │  excel_writer    │
                   │  (openpyxl)      │
                   └────────┬─────────┘
                            ▼
                   ┌──────────────────┐
                   │   validator.py   │
                   │  (--strict)      │
                   └──────────────────┘
```

---

# 4. Yêu cầu chức năng (Functional Requirements)

## FR-01 — Nhập liệu PDF

| ID | Mô tả | Priority |
|----|--------|----------|
| FR-01.1 | GUI hỗ trợ kéo-thả hoặc chọn file PDF bài viết | P0 |
| FR-01.2 | GUI hỗ trợ PDF Ref (hyperlink URL nguồn) — tùy chọn có cảnh báo | P0 |
| FR-01.3 | Validate: đúng định dạng PDF, không mã hóa, không rỗng, không trùng 2 ô | P0 |
| FR-01.4 | Hiển thị preview tiêu đề + số claim ngay khi drop bài viết | P1 |

## FR-02 — Trích xuất nội dung bài viết

| ID | Mô tả | Priority |
|----|--------|----------|
| FR-02.1 | Detect heading size tự động (tần suất font PyMuPDF) | P0 |
| FR-02.2 | Bỏ qua nội dung trước "Tóm tắt nhanh"; dừng ở footer Vivipedia | P0 |
| FR-02.3 | **1 block text = 1 claim** (flush sau mỗi block, không chờ citation) | P0 |
| FR-02.4 | Giữ nguyên văn claim; ghi nhận citation `[n]` nếu có | P0 |
| FR-02.5 | Detect domain gợi ý từ keyword (law/med/trv/…) — intern override được | P1 |
| FR-02.6 | Lọc heading giả (watermark, text > 120 ký tự) | P1 |

## FR-03 — Trích xuất URL từ Ref PDF

| ID | Mô tả | Priority |
|----|--------|----------|
| FR-03.1 | Chỉ dùng `page.get_links()` — hyperlink annotation thật | P0 |
| FR-03.2 | Loại domain nội bộ / mạng xã hội (vivipedia.vn, facebook, …) | P0 |
| FR-03.3 | Dedup URL, giữ thứ tự | P0 |
| FR-03.4 | `check_url_coverage`: cảnh báo nếu URL < claims/3 | P1 |

## FR-04 — Verify URL độc lập (không tin Claude)

| ID | Mô tả | Priority |
|----|--------|----------|
| FR-04.1 | Fetch URL qua `requests` trước khi gửi Claude | P0 |
| FR-04.2 | Phân loại `document` / `index` / `error` | P0 |
| FR-04.3 | Báo cáo load_ok, status HTTP, snippet text vào log + prompt | P0 |
| FR-04.4 | Đưa kết quả verify vào article prompt cho Claude | P1 |

## FR-05 — Build prompt & gửi Claude

| ID | Mô tả | Priority |
|----|--------|----------|
| FR-05.1 | System prompt từ `rule_prelabel.md` (Pre-label) hoặc `prompt.md` (Full) | P0 |
| FR-05.2 | Article prompt: title, domain, danh sách claim script, URL (tối đa 8) | P0 |
| FR-05.3 | Gửi URL riêng trước article prompt để trigger web fetch Claude UI | P0 |
| FR-05.4 | Connect Chrome qua CDP port 9222 (`login_claude.py`) | P0 |
| FR-05.5 | Paste qua clipboard (UTF-8) — trigger URL detection Claude | P0 |
| FR-05.6 | Retry tối đa 3 lần; phân biệt lỗi setup (no-retry) vs lỗi runtime | P0 |
| FR-05.7 | Cảnh báo nếu ack fetch URL không xác nhận đọc được | P1 |

## FR-06 — Parse & ràng buộc output Claude

| ID | Mô tả | Priority |
|----|--------|----------|
| FR-06.1 | Extract JSON — 4 strategy (direct, fence, balanced brace, regex) | P0 |
| FR-06.2 | Normalize status, ép float SF/SC/HR/SQ | P0 |
| FR-06.3 | **Pre-label:** ghi đè G = `[INTERN: chưa fact-check]`, H trống, J/K = 0 | P0 |
| FR-06.4 | **Pre-label:** Notes dùng `DRAFT_SC=` / `DRAFT_HR=` | P0 |
| FR-06.5 | Chặn `fact_check_source_url` ngoài danh sách Ref | P0 |
| FR-06.6 | Gắn `evidence_quote`, `url_load_ok`, `intern_reviewed = N` | P0 |
| FR-06.7 | **Chặn ghi Excel** nếu số claim Claude ≠ script | P0 |
| FR-06.8 | Chuẩn hóa Notes (`notes_formatter`) khi thiếu key | P1 |
| FR-06.9 | Chuẩn hóa status G (tách `LECH — ...` → G + Notes) | P1 |
| FR-06.10 | `normalize_article_domain` + `apply_article_bands` từ registry/scoring | P1 |

## FR-07 — Ghi Excel

| ID | Mô tả | Priority |
|----|--------|----------|
| FR-07.1 | Template v10: 4 dòng header, freeze C5, màu FF-prefix | P0 |
| FR-07.2 | **18 cột A–R** (thêm P Evidence, Q URL Load, R Intern Reviewed) | P0 |
| FR-07.3 | Append mode — STT tự tăng; không ghi đè dòng có data cột F | P0 |
| FR-07.4 | PermissionError → lưu file backup timestamp | P1 |
| FR-07.5 | Sheet **Article Evaluation** — Rel/Comp, band, lý do 3–5 câu / bài | P0 |
| FR-07.6 | Nâng cấp file Excel cũ 15 cột → 18 cột | P1 |

## FR-08 — Pre-Submit Validator

| ID | Mô tả | Priority |
|----|--------|----------|
| FR-08.1 | CLI scan file Excel — báo lỗi từng claim | P0 |
| FR-08.2 | Kiểm tra: status hợp lệ, URL đầy đủ, SC/HR ≠ 0, Notes format | P0 |
| FR-08.3 | **`--strict`:** cấm placeholder G; bắt buộc R = Y | P0 |
| FR-08.4 | **`--strict`:** XAC NHAN → bắt buộc P (evidence) + Q = Y | P0 |
| FR-08.5 | Logic cảnh báo: XAC NHAN + HR thấp; LECH + H trống | P1 |
| FR-08.6 | Validate `sub_domain_id` + tên domain/sub-domain khớp registry | P1 |
| FR-08.7 | **`--strict`:** cảnh báo giải thích dài trong cột G (chỉ 6 status) | P1 |
| FR-08.8 | Kiểm tra từng URL khi cột H có nhiều dòng | P1 |

## FR-09 — Notes Formatter (CLI)

| ID | Mô tả | Priority |
|----|--------|----------|
| FR-09.1 | Intern nhập SC/HR + lý do → output block Notes chuẩn | P2 |
| FR-09.2 | Format bắt buộc: `SF=` / `SC=` / `HR=` / `SQ=` / `TXT=` | P2 |

## FR-10 — Chế độ vận hành

| Chế độ | Mô tả | Mặc định |
|--------|--------|----------|
| **Pre-label** | AI: SF/SQ/TXT + draft; intern: G/H/J/K | ✅ |
| **Full** | AI điền fact-check đầy đủ — bắt buộc review + `--strict` | ❌ |

---

# 5. Schema dữ liệu

## 5.1 Excel — Sheet Annotation (18 cột)

| Cột | Tên | Vòng 1 (Pre-label) | Vòng 2 (Intern) |
|-----|-----|--------------------|-----------------|
| A | STT | Auto | — |
| B | Article Title | Script + Claude | — |
| C | Domain | Claude xác nhận | — |
| D | Sub-domain | Claude | — |
| E | Sub-domain ID | Claude | — |
| F | Claim | Script (nguyên văn) | — |
| G | Fact-check Status | `[INTERN: chưa fact-check]` | **Intern điền** |
| H | Fact-check Source URL | Trống | **Intern điền** |
| I | SF | Claude | Review |
| J | SC | 0 | **Intern điền** |
| K | HR | 0 | **Intern điền** |
| L | SQ | Claude | Review |
| M | Notes | SF/SQ/TXT + DRAFT_SC/HR | **Intern sửa SC/HR** |
| N | Annotator ID | UI | — |
| O | Date | Auto | — |
| P | Evidence Quote | Draft | **Intern xác nhận** |
| Q | URL Load OK | Script Y/N | Intern xác nhận |
| R | Intern Reviewed | `N` | **`Y` bắt buộc trước nộp** |

> Cột **A–O** khớp template Vivipedia v10 (nộp TA). **P–R** là mở rộng tool — bắt buộc nội bộ qua `validator --strict`.

## 5.1b Excel — Sheet Article Evaluation

| Cột | Nội dung |
|-----|----------|
| Tên bài, Domain, Sub-domain | Từ article JSON |
| Rel, Rel Band | Holistic — trả lời đúng tiêu đề |
| Nhận xét Relevance | 3–5 câu |
| Comp, Comp Band | Holistic — bao phủ khía cạnh |
| Nhận xét Completeness | 3–5 câu |
| Annotator ID, Ngày | UI / auto |

Band tự tính (`Excellent` … `Block`) nếu Claude thiếu `rel_band` / `comp_band`.

## 5.2 Trạng thái Fact-check (cột G)

| Status | Khi dùng |
|--------|----------|
| XAC NHAN | Nguồn xác nhận khớp claim |
| LECH | Sai lệch nhỏ |
| MAU THUAN | Mâu thuẫn nguồn chính thức |
| OUTDATED | Thông tin đã cũ |
| KHONG TIM THAY | Không tìm được nguồn |
| BO QUA | Claim chung chung, không verify |

## 5.3 JSON claim (output Claude)

```json
{
  "article": {
    "title": "",
    "domain_key": "law",
    "domain": "Pháp luật",
    "sub_domain": "Hành chính",
    "sub_domain_id": "law_03",
    "rel": 0.85,
    "comp": 0.75
  },
  "claims": [
    {
      "claim": "nguyên văn paragraph",
      "fact_check_status": "[INTERN: chưa fact-check]",
      "fact_check_source_url": "",
      "source_fidelity": 0.90,
      "source_coverage": 0.00,
      "hallucination_rate": 0.00,
      "source_quality": 0.85,
      "evidence_quote": "trích từ URL ≤200 ký tự",
      "url_load_ok": "Y",
      "intern_reviewed": "N",
      "notes": "SF=0.90: ...\nDRAFT_SC=0.75: ...\nDRAFT_HR=0.85: ...\nSQ=0.85: ...\nTXT=OK: ..."
    }
  ]
}
```

---

# 6. Luồng nghiệp vụ end-to-end

```
[Nhận bài Vivipedia]
        │
        ▼
[PDF bài + PDF Ref]
        │
        ▼
┌───────────────────┐
│  VÒNG 1 — TOOL    │  RUN PRE-LABEL
│  • parse claim    │
│  • verify URL     │
│  • Claude draft   │
│  • Excel A–R      │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  VÒNG 2 — INTERN  │  Fact-check G/H/J/K
│  • mở URL thật    │  P/Q/R = evidence + Y
│  • sửa Notes      │
└─────────┬─────────┘
          │
          ▼
   validator --strict
          │
          ▼
┌───────────────────┐
│  VÒNG 3 — QA      │  Spot-check ~20%
└───────────────────┘
```

---

# 7. Yêu cầu phi chức năng (NFR)

| ID | Hạng mục | Target v1 |
|----|----------|-----------|
| NFR-01 | Parse PDF 1 bài | < 10 giây |
| NFR-02 | Claude response (1 bài ~15 claim) | < 5 phút (phụ thuộc Claude Web) |
| NFR-03 | Ghi Excel | < 5 giây |
| NFR-04 | Độ tin cậy pipeline | Retry 3 lần; block claim lệch |
| NFR-05 | Bảo mật | Không commit `.env`, profile Chrome, output Excel vào git |
| NFR-06 | Môi trường | Windows 10+, Python 3.10+, Chrome desktop |
| NFR-07 | Khả năng bảo trì | Module tách biệt trong `modules/` |
| NFR-08 | Ngôn ngữ UI/log | Tiếng Việt |

---

# 8. Rủi ro sản phẩm & giảm thiểu

| Rủi ro | Mức | Giảm thiểu trong sản phẩm |
|--------|-----|---------------------------|
| Claude hallucination (XAC NHAN sai) | Cao | Pre-label mặc định; intern bắt buộc fact-check; cột P/Q/R |
| Intern tin nhầm draft AI | Cao | Placeholder G; validator `--strict`; SOP review 100% XAC NHAN |
| URL index → SC cao sai | Cao | url_verifier phân loại index; training case ODA trong onboarding |
| PDF scan ảnh → 0 claim | Trung bình | Validate + cảnh báo rõ; yêu cầu PDF text layer |
| Claude timeout / JSON lỗi | Trung bình | Retry; debug_screenshot; log preview |
| Chrome CDP mất kết nối | Trung bình | Ping port 9222 trước RUN; hướng dẫn login_claude.py |
| Nhiều intern append 1 file | Thấp | Khuyến nghị tách file theo batch |

---

# 9. Tech stack

| Thành phần | Công nghệ |
|------------|-----------|
| Ngôn ngữ | Python 3.10+ |
| PDF | PyMuPDF (`fitz`) |
| Browser automation | Playwright (CDP connect Chrome) |
| AI | Claude.ai Web (session người dùng) |
| HTTP verify URL | `requests` |
| Excel | openpyxl |
| GUI | Tkinter (+ tkinterdnd2 nếu có) |

---

# 10. Cấu trúc repository

```
label-pipeline-optimizer/
├── main.py                      # GUI orchestration
├── login_claude.py              # Chrome remote debug :9222
├── validator.py                 # Pre-submit validator CLI
├── notes_formatter_cli.py       # Notes helper CLI
├── prompt.md                    # Rubric + schema (Full mode)
├── rule_prelabel.md             # Prompt Vòng 1
├── requirements.txt
├── README.md
├── workflow.md
├── HUONG-DAN-SU-DUNG-VA-RUI-RO.md
├── outputs/                     # gitignored
└── modules/
    ├── pdf_parser.py
    ├── ref_parser.py
    ├── url_verifier.py
    ├── prompt_builder.py
    ├── claude_automation.py
    ├── response_parser.py
    ├── claim_constraints.py
    ├── domain_registry.py
    ├── scoring_utils.py
    ├── notes_formatter.py
    └── excel_writer.py
```

**Tham chiếu TA (không bắt buộc commit):** export CSV Domain list, Scoring Guide, Annotation mẫu — dùng cho `domain_registry` và căn `prompt.md`.

---

# 11. MVP scope & tiêu chí thành công

## 11.1 MVP (v1.0) — Included

- [x] GUI upload PDF + Ref
- [x] Parse claim + URL
- [x] URL verifier độc lập
- [x] Claude automation (Pre-label + Full)
- [x] Excel 18 cột append + sheet Article Evaluation
- [x] Validator + `--strict` (+ domain / status G)
- [x] `domain_registry` + `scoring_utils`
- [x] Notes formatter
- [x] Block ghi Excel khi claim lệch

## 11.2 Excluded (v1)

- Batch multi-PDF queue
- Web dashboard
- Database / multi-user
- API Claude trả phí
- Auto inter-annotator metrics

## 11.3 Success metrics

| Metric | Target |
|--------|--------|
| Giảm thời gian setup/bài (bước 2–6) | ≥ 50% so với thủ công |
| Lỗi merge Excel / lệch dòng | ≈ 0 (không còn bước paste) |
| File pass `validator --strict` trước QA | ≥ 90% batch (sau 2 tuần onboarding tool) |
| URL Ref extract thành công | ≥ 90% bài có Ref hyperlink |
| Claim count script = output Excel | 100% (block nếu lệch) |
| Intern vẫn hoàn thành fact-check Vòng 2 | 100% claim trước nộp |

---

# 12. Roadmap

## v1.0 — MVP (hiện tại)

Pre-label, url_verifier, validator strict, Excel A–R + Article Evaluation, `prompt.md` TA v13.5, GUI.

## v1.1 — Cải thiện chất lượng

- URL helper: cosine similarity claim ↔ đoạn trang (gợi ý SC, không auto chốt)
- Flag claim “index page” tự động trong Excel (màu / cột phụ)
- Export batch riêng theo annotator (tránh append lẫn)

## v1.2 — Team scale

- Inter-annotator sample 10% batch + báo cáo MAE SC/HR
- Template prompt few-shot theo domain (law/med/trv)

## v2.0 — Tùy chọn dài hạn

- Prompt + API có web search (nếu mentor approve)
- Dashboard đọc-only cho QA
- Batch queue headless (không GUI)

---

# 13. Phụ lục 

| Đề xuất | FR / Module |
|---------|-------------|
| Pre-Submit Validator | `validator.py`, FR-08 |
| URL Content Fetcher | `url_verifier.py`, FR-04 |
| Auto Notes Formatter | `notes_formatter.py`, FR-09 |
| Bỏ merge Excel thủ công | `excel_writer.py`, FR-07 |
| Giữ intern fact-check | Pre-label mode, FR-06.3, FR-10 |

---

*PRD v1.0 — Label Pipeline Optimizer — Vivipedia Annotation VSF*
*Tham khảo file kết quả .xlsx*