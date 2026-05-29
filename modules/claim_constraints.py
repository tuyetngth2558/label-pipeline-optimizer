"""
claim_constraints.py — Ràng buộc claim sau Claude (pre-label, URL allowlist).
"""
from __future__ import annotations

import re

from modules.url_verifier import filter_urls_to_allowlist, url_in_allowlist

PLACEHOLDER_G = "[INTERN: chưa fact-check]"
INTERN_NOT_REVIEWED = "N"
COL_INTERN_REVIEWED = "N"  # giá trị mặc định cột R


def split_urls(url_field: str) -> list[str]:
    if not url_field:
        return []
    parts = re.split(r"[\n\r;]+", str(url_field))
    return [u.strip() for u in parts if u.strip().startswith("http")]


def join_urls(urls: list[str]) -> str:
    return "\n".join(urls)


def sanitize_claim_urls(claim: dict, allowed_urls: list[str], log_fn=print) -> dict:
    """Chặn URL không có trong Ref PDF."""
    raw = claim.get("fact_check_source_url", "") or ""
    urls = split_urls(raw)
    if not urls:
        return claim
    valid = filter_urls_to_allowlist(urls, allowed_urls)
    if len(valid) < len(urls):
        removed = [u for u in urls if u not in valid]
        log_fn(
            f"  ⚠ URL bị loại (không trong Ref): {removed[0][:60]}...",
            "warn",
        )
        claim = dict(claim)
        claim["fact_check_source_url"] = join_urls(valid)
        if not valid and claim.get("fact_check_status") == "XAC NHAN":
            claim["fact_check_status"] = "KHONG TIM THAY"
    return claim


def apply_prelabel_output(claim: dict) -> dict:
    """
    Vòng 1: không cho AI chốt fact-check.
    Giữ SF/SQ/TXT/draft; G/H/J/K để intern.
    """
    c = dict(claim)
    notes = c.get("notes", "") or ""

    # Chuyển SC/HR trong notes thành DRAFT_ nếu chưa có
    notes = re.sub(r"(?m)^SC=", "DRAFT_SC=", notes)
    notes = re.sub(r"(?m)^HR=", "DRAFT_HR=", notes)
    if "DRAFT_SC=" not in notes and c.get("source_coverage"):
        sc = c.get("source_coverage", "")
        notes += f"\nDRAFT_SC={sc}: (AI gợi ý — intern xác nhận)"
    if "DRAFT_HR=" not in notes and c.get("hallucination_rate"):
        hr = c.get("hallucination_rate", "")
        notes += f"\nDRAFT_HR={hr}: (AI gợi ý — intern xác nhận)"

    c["fact_check_status"] = PLACEHOLDER_G
    c["fact_check_source_url"] = ""
    c["source_coverage"] = 0.0
    c["hallucination_rate"] = 0.0
    c["notes"] = notes.strip()
    c["intern_reviewed"] = INTERN_NOT_REVIEWED
    c["ai_confidence"] = c.get("ai_confidence", "unverified")
    return c


def enrich_evidence_fields(claim: dict, allowed_urls: list[str], url_results: list[dict]) -> dict:
    """Gắn evidence_quote, url_load_ok từ Claude + verifier."""
    from modules.url_verifier import normalize_url

    c = dict(claim)
    eq = (c.get("evidence_quote") or "").strip()
    url_field = c.get("fact_check_source_url", "") or ""
    urls = split_urls(url_field)

    by_norm = {normalize_url(r.get("url", "")): r for r in url_results}

    load_ok = False
    page_type = ""
    for u in urls:
        vr = by_norm.get(normalize_url(u))
        if vr and vr.get("load_ok"):
            load_ok = True
            page_type = vr.get("page_type", "")
            if not eq and vr.get("snippet"):
                c["evidence_quote"] = vr["snippet"][:300]
            break

    if urls and not url_in_allowlist(urls[0], allowed_urls):
        load_ok = False

    c["url_load_ok"] = "Y" if load_ok else "N"
    c["page_type"] = page_type or c.get("page_type", "")
    if not c.get("evidence_quote"):
        c["evidence_quote"] = eq
    c.setdefault("intern_reviewed", INTERN_NOT_REVIEWED)
    return c


def validate_claim_for_export(claim: dict, mode: str, allowed_urls: list[str]) -> list[str]:
    """Lỗi nghiêm trọng trước khi ghi Excel (mode=prelabel|full)."""
    issues = []
    status = (claim.get("fact_check_status") or "").strip().upper()
    url = claim.get("fact_check_source_url", "") or ""

    if mode == "prelabel":
        if status == "XAC NHAN":
            issues.append("Pre-label: AI không được gán XAC NHAN")
        if PLACEHOLDER_G not in (claim.get("fact_check_status") or ""):
            if status and status not in ("", "KHONG TIM THAY"):
                pass  # sẽ bị apply_prelabel ghi đè
        if url and not all(url_in_allowlist(u, allowed_urls) for u in split_urls(url)):
            issues.append("URL fact-check không thuộc Ref list")
        return issues

    # full mode
    for u in split_urls(url):
        if not url_in_allowlist(u, allowed_urls):
            issues.append(f"URL ngoài Ref: {u[:50]}")
    if status == "XAC NHAN":
        if not (claim.get("evidence_quote") or "").strip():
            issues.append("XAC NHAN thiếu evidence_quote")
        if claim.get("url_load_ok") != "Y":
            issues.append("XAC NHAN nhưng url_load_ok != Y")
    return issues
