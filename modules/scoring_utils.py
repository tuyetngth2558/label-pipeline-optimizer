"""
scoring_utils.py — Band điểm & chuẩn hóa fact_check_status (template v10).
"""
from __future__ import annotations

VALID_STATUSES = frozenset({
    "XAC NHAN", "LECH", "MAU THUAN", "OUTDATED", "KHONG TIM THAY", "BO QUA",
})

_STATUS_ALIASES = {
    "XAC_NHAN": "XAC NHAN",
    "MAU_THUAN": "MAU THUAN",
    "KHONG_TIM_THAY": "KHONG TIM THAY",
    "BO_QUA": "BO QUA",
}


def score_to_band(score: float | None) -> str:
    """Map 0–1 → Excellent | Good | Borderline | Poor | Block."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return ""
    if s >= 0.90:
        return "Excellent"
    if s >= 0.75:
        return "Good"
    if s >= 0.50:
        return "Borderline"
    if s >= 0.25:
        return "Poor"
    return "Block"


def normalize_fact_check_status(raw: str) -> tuple[str, str]:
    """
    Tách status chuẩn và phần giải thích thừa.
    VD: 'LECH — Điều 13...' → ('LECH', 'Điều 13...')
    """
    if not raw:
        return "", ""
    text = str(raw).strip()
    compact = text.upper().replace(" ", "_")
    if compact in _STATUS_ALIASES:
        return _STATUS_ALIASES[compact], ""
    upper = text.upper()

    for token in sorted(VALID_STATUSES, key=len, reverse=True):
        if upper == token:
            return token, ""
        for sep in (" — ", " - ", ":", " —", "–"):
            prefix = token + sep
            if upper.startswith(prefix.upper()) or text.upper().startswith(prefix.upper()):
                detail = text[len(token) + len(sep):].strip()
                return token, detail
        if upper.startswith(token + " "):
            detail = text[len(token):].strip().lstrip("—-: ")
            return token, detail

    # Token đầu nếu là từ hợp lệ
    first = upper.split()[0] if upper.split() else ""
    if first in VALID_STATUSES:
        detail = text.split(None, 1)[1] if len(text.split(None, 1)) > 1 else ""
        if detail.startswith(("—", "-", ":")):
            detail = detail.lstrip("—-: ").strip()
        return first, detail

    return text.upper(), ""


def apply_article_bands(article: dict) -> dict:
    """Gán rel_band / comp_band nếu thiếu."""
    art = dict(article)
    for score_key, band_key in (("rel", "rel_band"), ("comp", "comp_band")):
        band = (art.get(band_key) or "").strip()
        if band and band in ("Excellent", "Good", "Borderline", "Poor", "Block"):
            continue
        computed = score_to_band(art.get(score_key))
        if computed:
            art[band_key] = computed
    return art
