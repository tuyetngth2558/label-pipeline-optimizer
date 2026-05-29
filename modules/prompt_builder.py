"""
prompt_builder.py — Build prompt gửi Claude.
"""
import os

from modules.domain_registry import subdomain_hint_for_domain

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompt.md")
RULE_PRELABEL_PATH = os.path.join(os.path.dirname(__file__), "..", "rule_prelabel.md")

MODE_PRELABEL = "prelabel"
MODE_FULL = "full"


def load_rules(mode: str = MODE_PRELABEL) -> str:
    path = RULE_PRELABEL_PATH if mode == MODE_PRELABEL else PROMPT_PATH
    with open(path, encoding="utf-8") as f:
        base = f.read()
    if mode == MODE_PRELABEL:
        return base
    return base


def build_system_prompt(mode: str = MODE_PRELABEL) -> str:
    return load_rules(mode)


def build_article_prompt(
    article: dict,
    ref: dict,
    domain_key: str = "",
    subdomain: str = "",
    mode: str = MODE_PRELABEL,
    url_verification: list[dict] | None = None,
) -> str:
    title = article.get("title", "")
    sections = article.get("sections", [])
    d_key = article.get("domain_key") or domain_key or "?"
    d_name = article.get("domain_name") or d_key
    all_urls = ref.get("urls", [])

    cited_indices = set()
    for sec in sections:
        for para in sec.get("paragraphs", []):
            if isinstance(para, dict):
                for c in para.get("citations", []):
                    if 1 <= c <= len(all_urls):
                        cited_indices.add(c - 1)

    if cited_indices:
        urls = [all_urls[i] for i in sorted(cited_indices)][:8]
    else:
        urls = all_urls[:8]

    sub_hint = subdomain_hint_for_domain(d_key) if d_key and d_key != "?" else ""
    domain_hint = (
        f"Script tự detect domain: [{d_key}] {d_name}"
        + (f" | Sub-domain gợi ý: {subdomain}" if subdomain else "")
        + "\n→ Xác nhận hoặc sửa lại trong JSON output (sub_domain_id phải khớp bảng Vivipedia)"
    )
    if sub_hint:
        domain_hint += f"\n{sub_hint}"

    claim_lines = []
    claim_idx = 0
    for sec in sections:
        claim_lines.append(f"\n## {sec['heading']}")
        for para in sec.get("paragraphs", []):
            claim_idx += 1
            text = para["text"] if isinstance(para, dict) else para
            cits = para.get("citations", []) if isinstance(para, dict) else []
            cite_str = f"  [cite: {', '.join(str(c) for c in cits)}]" if cits else ""
            snippet = text[:400] + ("..." if len(text) > 400 else "")
            claim_lines.append(f"[Claim {claim_idx}]{cite_str} {snippet}")

    claims_block = "\n".join(claim_lines) if claim_lines else "(không trích xuất được claim)"
    total_claims = claim_idx

    if urls:
        url_lines = "\n".join(f"[{i+1}] {u}" for i, u in enumerate(urls))
        url_section = f"""URL NGUỒN (đã gửi để đọc — {len(urls)} URL):
Chỉ dùng URL trong danh sách cho fact_check_source_url (mode full) hoặc evidence_quote.

{url_lines}"""
    else:
        url_section = "URL NGUỒN: (không có Ref PDF)"

    verify_block = ""
    if url_verification:
        lines = []
        for i, r in enumerate(url_verification[:12], 1):
            ok = "OK" if r.get("load_ok") else "FAIL"
            lines.append(
                f"  [{i}] {ok} type={r.get('page_type','?')} "
                f"HTTP {r.get('status_code',0)} — {r.get('url','')[:65]}"
            )
        verify_block = (
            "\n---\nKẾT QUẢ SCRIPT VERIFY URL (độc lập — ưu tiên hơn đoán mò):\n"
            + "\n".join(lines)
            + "\nNếu FAIL → url_load_ok=N, không gợi ý XAC NHAN.\n"
        )

    mode_line = (
        "CHẾ ĐỘ: PRE-LABEL (Vòng 1) — fact_check_status="
        '"[INTERN: chưa fact-check]", fact_check_source_url="", SC=0, HR=0.'
        if mode == MODE_PRELABEL
        else "CHẾ ĐỘ: FULL — fact-check đầy đủ; bắt buộc evidence_quote khi XAC NHAN."
    )

    return f"""TIÊU ĐỀ BÀI: {title}

{domain_hint}

{mode_line}

---
DANH SÁCH CLAIM ({total_claims} claim — đúng thứ tự, không thêm/bớt):
{claims_block}

---
{url_section}
{verify_block}
---
Trả JSON thuần — {total_claims} claim. Không markdown."""
