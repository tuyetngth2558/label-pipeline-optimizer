# Quy trình — tool_data_labelling (có ràng buộc)

## Vòng làm việc

```
PDF + Ref → Tool PRE-LABEL → Excel (G=placeholder, R=N)
         → Intern fact-check (G/H/J/K, P/Q/R)
         → validator.py --strict → Nộp batch → QA 20%
```

## Pipeline tự động (RUN)

1. Validate đầu vào (PDF, Annotator, Chrome CDP)
2. Parse bài viết + Ref URL
3. **Verify URL (script)** — `url_verifier.py`, không tin Claude
4. Build prompt (`rule_prelabel.md` hoặc `prompt.md`)
5. Claude qua Chrome CDP
6. Parse JSON → `process_claims` (allowlist URL, pre-label, evidence)
7. **Chặn ghi Excel** nếu số claim lệch script vs Claude
8. Ghi Excel 18 cột A–R

## Chế độ

| Chế độ | Mô tả |
|--------|--------|
| **Pre-label** (mặc định) | G=placeholder, SC/HR=0, DRAFT trong Notes |
| **Full** | AI điền fact-check — bắt buộc review + `--strict` trước nộp |

## Cột review (P–R)

| Cột | Nội dung |
|-----|----------|
| P | Trích dẫn từ URL (≤200 ký tự) |
| Q | `Y`/`N` — script hoặc intern xác nhận load URL |
| R | `N` khi mới chạy tool; `Y` sau intern review |

## Validator

```bash
python validator.py -f outputs/annotation_output.xlsx          # chuẩn
python validator.py -f outputs/annotation_output.xlsx --strict  # trước nộp
```

`--strict`: không placeholder G, `intern_reviewed=Y`, evidence + url_load khi `XAC NHAN`.

## Ràng buộc URL

- `fact_check_source_url` chỉ được chứa URL có trong Ref PDF
- URL ngoài list → bị loại + cảnh báo log
