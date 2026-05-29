"""
domain_registry.py — 13 domains / 69 sub-domains (Vivipedia Dataset Definition).

Nguồn: reference CSV hoặc file Vivipedia TA export trong thư mục tool.
"""
from __future__ import annotations

import csv
import os
from functools import lru_cache

_PKG = os.path.dirname(__file__)
_ROOT = os.path.join(_PKG, "..")

_CSV_CANDIDATES = [
    os.path.join(_ROOT, "reference", "domain_subdomain_list.csv"),
    os.path.join(
        _ROOT,
        "[Vivipedia] - Annonate Output - TA - 13.5.xlsx - Domain-Subdomain List.csv",
    ),
]

_CODE_TO_KEY = {
    "LAW": "law", "MED": "med", "TRV": "trv", "CUL": "cul", "HIS": "his",
    "EDU": "edu", "FIN": "fin", "BIZ": "biz", "SCI": "sci", "RE": "re",
    "ENV": "env", "GOV": "gov", "ENT": "ent",
}


def _find_csv() -> str | None:
    for p in _CSV_CANDIDATES:
        if os.path.isfile(p):
            return p
    return None


@lru_cache(maxsize=1)
def load_registry() -> dict:
    """
    Returns:
      by_id: sub_domain_id -> {domain_key, domain, sub_domain, code}
      by_domain: domain_key -> list of entries (sorted by id)
      domain_names: domain_key -> display name
    """
    path = _find_csv()
    by_id: dict[str, dict] = {}
    by_domain: dict[str, list] = {}
    domain_names: dict[str, str] = {}

    if not path:
        return {"by_id": by_id, "by_domain": by_domain, "domain_names": domain_names}

    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 4:
                continue
            domain_name = (row[0] or "").strip()
            code = (row[1] or "").strip().upper()
            sub_name = (row[2] or "").strip()
            sub_id = (row[3] or "").strip()
            if not sub_id or not sub_id[0].isalpha() or "_" not in sub_id:
                continue
            if sub_id.endswith("_id") or "dropdown" in domain_name.lower():
                continue

            domain_key = _CODE_TO_KEY.get(code) or sub_id.split("_")[0]
            entry = {
                "domain_key": domain_key,
                "domain": domain_name,
                "sub_domain": sub_name,
                "sub_domain_id": sub_id,
                "code": code,
            }
            by_id[sub_id] = entry
            by_domain.setdefault(domain_key, []).append(entry)
            domain_names[domain_key] = domain_name

    for dk in by_domain:
        by_domain[dk].sort(key=lambda e: e["sub_domain_id"])

    return {"by_id": by_id, "by_domain": by_domain, "domain_names": domain_names}


def get_entry(sub_domain_id: str) -> dict | None:
    return load_registry()["by_id"].get((sub_domain_id or "").strip())


def validate_article_domain(
    domain_key: str,
    domain: str,
    sub_domain: str,
    sub_domain_id: str,
) -> list[str]:
    """Kiểm tra cặp domain / sub-domain khớp bảng chuẩn."""
    issues: list[str] = []
    reg = load_registry()
    if not reg["by_id"]:
        return issues

    sid = (sub_domain_id or "").strip()
    dk = (domain_key or "").strip().lower()
    entry = reg["by_id"].get(sid)

    if not sid:
        issues.append("thiếu sub_domain_id")
        return issues

    if not entry:
        issues.append(f"sub_domain_id không có trong bảng: {sid}")
        return issues

    if dk and entry["domain_key"] != dk:
        issues.append(
            f"domain_key '{dk}' không khớp {sid} (thuộc {entry['domain_key']})"
        )

    if domain and entry["domain"] != domain.strip():
        issues.append(f"domain hiển thị lệch: '{domain}' vs '{entry['domain']}'")

    if sub_domain and entry["sub_domain"] != sub_domain.strip():
        issues.append(f"sub_domain lệch: '{sub_domain}' vs '{entry['sub_domain']}'")

    return issues


_DEFAULT_SUB_BY_DOMAIN = {
    "law": "law_03",  # Hành chính — phổ biến cho NĐ/TT/thủ tục
    "med": "med_01",
    "gov": "gov_04",
    "fin": "fin_05",
}


def normalize_article_domain(article: dict, domain_key_hint: str = "") -> dict:
    """Điền domain/sub_domain từ sub_domain_id; sửa ID bịa của AI nếu không có trong bảng."""
    art = dict(article)
    sid = (art.get("sub_domain_id") or "").strip()
    entry = get_entry(sid)
    if entry:
        art["sub_domain_id"] = entry["sub_domain_id"]
        art["sub_domain"] = entry["sub_domain"]
        art["domain"] = entry["domain"]
        art["domain_key"] = entry["domain_key"]
        return art

    reg = load_registry()
    dk = (art.get("domain_key") or domain_key_hint or "law").strip().lower()
    sub_name = (art.get("sub_domain") or "").strip().lower()

    for e in reg["by_domain"].get(dk, []):
        if sub_name and sub_name in e["sub_domain"].lower():
            art.update({
                "sub_domain_id": e["sub_domain_id"],
                "sub_domain": e["sub_domain"],
                "domain": e["domain"],
                "domain_key": e["domain_key"],
            })
            return art

    fallback_id = _DEFAULT_SUB_BY_DOMAIN.get(dk)
    if fallback_id:
        entry = get_entry(fallback_id)
        if entry:
            art.update({
                "sub_domain_id": entry["sub_domain_id"],
                "sub_domain": entry["sub_domain"],
                "domain": entry["domain"],
                "domain_key": entry["domain_key"],
            })
    return art


def subdomain_hint_for_domain(domain_key: str, max_items: int = 12) -> str:
    """Gợi ý sub-domain cho prompt Claude."""
    reg = load_registry()
    items = reg["by_domain"].get((domain_key or "").lower(), [])
    if not items:
        return ""
    lines = [f"  {e['sub_domain_id']}: {e['sub_domain']}" for e in items[:max_items]]
    if len(items) > max_items:
        lines.append(f"  ... (+{len(items) - max_items} sub-domain khác)")
    return "Sub-domain hợp lệ cho domain này:\n" + "\n".join(lines)
