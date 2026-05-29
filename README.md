# Vivipedia Annotation Tool (`tool_data_labelling`)
---

## Yêu cầu

- Python 3.10+
- Google Chrome (desktop)
- Tài khoản Claude.ai đã đăng nhập

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
2. Chỉnh Domain / Annotator ID
3. Bấm **RUN ANNOTATION**

Kết quả: `outputs/annotation_output.xlsx` (append mỗi lần chạy).

### Bước 3 — Intern fact-check (Vòng 2)

Mở Excel, điền cột **G, H, J, K**, sửa Notes, cập nhật:
- **P** Evidence Quote (trích từ URL thật)
- **Q** URL Load OK = `Y` nếu đã mở và xác nhận
- **R** Intern Reviewed = `Y` (hoặc `Y ANT-01 2026-05-29`)

### Bước 4 — Validate trước khi nộp

```bash
python validator.py -f outputs/annotation_output.xlsx --strict
```

`--strict`: bắt buộc cột R, evidence khi `XAC NHAN`.

---

## Cấu trúc thư mục

```
tool_data_labelling/
├── main.py                 # GUI chính
├── login_claude.py         # Chrome CDP port 9222
├── validator.py            # Pre-submit validator (CLI)
├── prompt.md               # System prompt / rubric (Full mode)
├── requirements.txt
├── CHANGELOG.md
├── outputs/                # Excel kết quả (gitignored)
└── modules/
    ├── pdf_parser.py       # Trích claim từ PDF (flush mỗi block)
    ├── ref_parser.py       # URL từ Ref PDF + check_url_coverage
    ├── prompt_builder.py
    ├── claude_automation.py
    ├── response_parser.py  # JSON + chuẩn hóa Notes
    ├── notes_formatter.py  # Format SF=/SC=/HR=/...
    └── excel_writer.py
```

---

## Pipeline

```
PDF Bài viết → pdf_parser → sections/claims
PDF Ref      → ref_parser → URLs (+ coverage check)
                          ↓
              prompt_builder → prompts
                          ↓
            claude_automation → JSON
                          ↓
            response_parser (+ notes_formatter)
                          ↓
              excel_writer → annotation_output.xlsx
```

---

## Cột Excel (A–R)

| Cột | Nội dung | Nguồn |
|-----|----------|-------|
| A–F | STT, Title, Domain, Sub-domain, ID, Claim | PDF + Claude |
| G–H | Fact-check Status, URL | **Intern** (pre-label: placeholder) |
| I–L | SF, SC, HR, SQ | AI + intern |
| M | Notes | AI draft (`DRAFT_SC`/`DRAFT_HR` ở pre-label) |
| N–O | Annotator ID, Date | UI |
| **P** | Evidence Quote | Script + intern |
| **Q** | URL Load OK (Y/N) | `url_verifier` + intern |
| **R** | Intern Reviewed | `N` → `Y` sau review |

**6 trạng thái G:** XAC NHAN, LECH, MAU THUAN, OUTDATED, KHONG TIM THAY, BO QUA.

---

## Scripts hỗ trợ

| Script | Mô tả |
|--------|-------|
| `python notes_formatter.py` | (module) — dùng trong pipeline |
| `python validator.py -f file.xlsx --strict` | Kiểm tra trước nộp (sau intern review) |
| `python test_modules.py` | Test nhanh parser (cần `data/*.pdf`) |

---

## Lỗi thường gặp

| Lỗi | Cách xử lý |
|-----|------------|
| Port 9222 | Chạy lại `login_claude.py` |
| 0 claims | PDF scan ảnh / không có text layer |
| Claim lệch script vs Claude | Xem log cảnh báo từng dòng |
| PermissionError Excel | Đóng file Excel đang mở |


---

