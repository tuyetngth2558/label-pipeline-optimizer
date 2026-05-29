# Vivipedia Annotation Tool (`tool_data_labelling`)

Pipeline pre-label + fact-check support cho dataset RAG Vivipedia (template v10).

**Chi tiết:** [HUONG-DAN-SU-DUNG-VA-RUI-RO.md](HUONG-DAN-SU-DUNG-VA-RUI-RO.md) · [workflow.md](workflow.md) · [prd.md](prd.md)

---

## Yêu cầu

- Python 3.10+
- Google Chrome (desktop)
- Tài khoản Claude.ai đã đăng nhập
- File tham chiếu TA (khuyến nghị): `Domain-Subdomain List.csv` trong thư mục tool — để validate 69 sub-domain

---

## Cài đặt

```bash
cd tool_data_labelling
pip install -r requirements.txt
playwright install chromium
```

---

## Cách chạy

### Bước 1 — Mở Chrome với remote debugging

```bash
python login_claude.py
```

Đăng nhập [claude.ai](https://claude.ai) nếu cần. **Không đóng Chrome** trong suốt phiên làm việc.

### Bước 2 — GUI annotation

```bash
python main.py
```

1. Kéo thả **PDF bài viết** (trái) và **PDF Ref** (phải)
2. Chọn **Chế độ:** Pre-label (Vòng 1, mặc định) hoặc Full
3. Chỉnh Domain / Annotator ID
4. Bấm **▶ RUN PRE-LABEL** (hoặc RUN FULL)

**Kết quả:** `outputs/annotation_output.xlsx` (append mỗi lần chạy), gồm:

| Sheet | Nội dung |
|-------|----------|
| **Annotation** | Claim từng dòng — cột A–O (template TA) + **P–R** (review tool) |
| **Article Evaluation** | 1 dòng/bài — Rel, Comp, band, nhận xét 3–5 câu |

### Bước 3 — Intern fact-check (Vòng 2)

Mở Excel, điền cột **G, H, J, K**, sửa Notes (đủ `SF=` … `TXT=`), cập nhật:

- **P** Evidence Quote (trích từ URL thật, ≤200 ký tự)
- **Q** URL Load OK = `Y` nếu đã mở và xác nhận
- **R** Intern Reviewed = `Y` sau khi review xong claim

**Cột G:** chỉ một trong 6 status — không ghi giải thích dài vào G (chi tiết → Notes).

### Bước 4 — Validate trước khi nộp

```bash
python validator.py -f outputs/annotation_output.xlsx --strict
```

`--strict`: bắt buộc cột R, evidence khi `XAC NHAN`, không placeholder G, kiểm tra domain ID.

---

## Cấu trúc thư mục

```
tool_data_labelling/
├── main.py
├── login_claude.py
├── validator.py
├── notes_formatter_cli.py
├── prompt.md                 # Rubric + JSON schema (Full mode)
├── rule_prelabel.md          # Prompt Vòng 1
├── requirements.txt
├── CHANGELOG.md
├── HUONG-DAN-SU-DUNG-VA-RUI-RO.md
├── workflow.md
├── prd.md
├── outputs/                  # gitignored
└── modules/
    ├── pdf_parser.py
    ├── ref_parser.py
    ├── url_verifier.py
    ├── domain_registry.py    # 69 sub-domain từ CSV TA
    ├── scoring_utils.py      # Band điểm, chuẩn hóa status G
    ├── prompt_builder.py
    ├── claude_automation.py
    ├── response_parser.py
    ├── claim_constraints.py
    ├── notes_formatter.py
    └── excel_writer.py
```

---

## Pipeline

```
PDF Bài viết → pdf_parser → sections/claims + domain hint
PDF Ref      → ref_parser → URLs (+ coverage check)
                          ↓
              url_verifier → load_ok / page_type
                          ↓
              prompt_builder (rule_prelabel.md | prompt.md)
                          ↓
            claude_automation → JSON
                          ↓
     response_parser (+ domain_registry, scoring_utils, notes_formatter)
                          ↓
     excel_writer → Annotation (A–R) + Article Evaluation
```

---

## Cột Excel — Annotation (A–R)

| Cột | Nội dung | Nguồn |
|-----|----------|-------|
| A–F | STT, Title, Domain, Sub-domain, ID, Claim | PDF + Claude |
| G–H | Fact-check Status, URL | **Intern** (pre-label: placeholder) |
| I–L | SF, SC, HR, SQ | AI + intern |
| M | Notes (5 dòng, gồm `TXT=`) | AI draft + intern |
| N–O | Annotator ID, Date | UI |
| **P–R** | Evidence, URL Load OK, Intern Reviewed | Script + intern |

**6 trạng thái G:** XAC NHAN, LECH, MAU THUAN, OUTDATED, KHONG TIM THAY, BO QUA.

---

## Scripts hỗ trợ

| Script | Mô tả |
|--------|-------|
| `python validator.py -f file.xlsx --strict` | Kiểm tra trước nộp |
| `python notes_formatter_cli.py` | Format Notes thủ công |
| `python test_modules.py` | Test parser (cần `data/*.pdf`) |

---

## Lỗi thường gặp

| Lỗi | Cách xử lý |
|-----|------------|
| Port 9222 | Chạy lại `login_claude.py` |
| 0 claims | PDF scan ảnh / không có text layer |
| Claim lệch script vs Claude | Pipeline dừng — không ghi Excel |
| PermissionError Excel | Đóng file Excel đang mở |
| Domain warning trong log | Sửa `sub_domain_id` theo bảng Domain TA |
