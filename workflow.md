# Quy trình — tool_data_labelling (có ràng buộc)

## Vòng làm việc

```
PDF + Ref → Tool PRE-LABEL → Excel (Annotation + Article Evaluation)
         → Intern fact-check (G/H/J/K, P/Q/R, sửa Rel/Comp nếu cần)
         → validator.py --strict → Nộp batch → QA 20%
```

## Pipeline tự động (RUN)

1. Validate đầu vào (PDF, Annotator, Chrome CDP)
2. Parse bài viết + Ref URL
3. **Verify URL (script)** — `url_verifier.py`, không tin Claude
4. Build prompt — `rule_prelabel.md` (Pre-label) hoặc `prompt.md` (Full); gợi ý sub-domain từ `domain_registry`
5. Claude qua Chrome CDP
6. Parse JSON → `process_claims` (allowlist URL, pre-label, evidence)
7. Chuẩn hóa: `normalize_fact_check_status`, `normalize_article_domain`, `score_to_band` cho Rel/Comp
8. **Chặn ghi Excel** nếu số claim lệch script vs Claude
9. Ghi **Annotation** 18 cột A–R
10. Ghi **Article Evaluation** 1 dòng/bài (Rel, Comp, band, lý do)

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
python validator.py -f outputs/annotation_output.xlsx          # chuẩn (pre-label)
python validator.py -f outputs/annotation_output.xlsx --strict  # trước nộp
```

`--strict`: không placeholder G, `intern_reviewed=Y`, evidence + url_load khi `XAC NHAN`, cảnh báo giải thích dài trong cột G, validate `sub_domain_id`.

## Ràng buộc URL

- `fact_check_source_url` chỉ được chứa URL có trong Ref PDF
- URL ngoài list → bị loại + cảnh báo log
- Nhiều URL trong cột H → mỗi URL một dòng

## File tham chiếu TA

Giữ trong thư mục tool (vd. `[Vivipedia] - ... - Domain-Subdomain List.csv`) để `domain_registry` load đủ 69 sub-domain. Rubric chi tiết: `prompt.md` (căn Scoring Guide v6 / template v10).
