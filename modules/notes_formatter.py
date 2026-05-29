"""
notes_formatter.py — Chuẩn hóa format Notes (SF=/SC=/HR=/SQ=/TXT=).

Theo spec Vivipedia và de-xuat-build-tool-team.md (Tool 3: Auto Notes Formatter).
"""
import re
from typing import Any

_LINE_KEYS = ("SF", "SC", "HR", "SQ", "TXT", "RISK")


def format_notes(
    sf: Any = None,
    sf_reason: str = "",
    sc: Any = None,
    sc_reason: str = "",
    hr: Any = None,
    hr_reason: str = "",
    sq: Any = None,
    sq_reason: str = "",
    txt: str = "OK",
    txt_reason: str = "",
    risk: Any = None,
    risk_reason: str = "",
) -> str:
    """Tạo block Notes 5–6 dòng đúng chuẩn."""
    lines = []

    def _add(key: str, score: Any, reason: str):
        if score is None and not reason:
            return
        if score is not None:
            try:
                s = f"{float(score):.2f}".rstrip("0").rstrip(".")
            except (TypeError, ValueError):
                s = str(score)
            lines.append(f"{key}={s}: {reason}".rstrip(": ").rstrip())
        elif reason:
            lines.append(f"{key}=: {reason}")

    _add("SF", sf, sf_reason)
    _add("SC", sc, sc_reason)
    _add("HR", hr, hr_reason)
    _add("SQ", sq, sq_reason)
    if risk is not None or risk_reason:
        _add("RISK", risk, risk_reason)
    txt_val = (txt or "OK").strip().upper()
    if txt_reason:
        lines.append(f"TXT={txt_val}: {txt_reason}")
    else:
        lines.append(
            f"TXT={txt_val}: Không có lỗi" if txt_val == "OK" else f"TXT={txt_val}:"
        )

    return "\n".join(lines)


def _parse_line(line: str) -> tuple[str, str, str] | None:
    """Parse một dòng Notes → (KEY, score, reason)."""
    line = line.strip()
    if not line:
        return None
    m = re.match(r"^(SF|SC|HR|SQ|TXT|RISK)\s*[=:]\s*([\d.]+)?\s*:?\s*(.*)$", line, re.I)
    if not m:
        return None
    key = m.group(1).upper()
    score = (m.group(2) or "").strip()
    reason = (m.group(3) or "").strip()
    return key, score, reason


def normalize_notes_block(notes: str, claim: dict | None = None) -> str:
    """
    Chuẩn hóa Notes từ Claude hoặc intern:
    - Sửa SC: → SC=
    - Bổ sung dòng thiếu từ các field score trong claim
    """
    claim = claim or {}
    parsed: dict[str, tuple[str, str]] = {}

    for line in (notes or "").splitlines():
        item = _parse_line(line)
        if item:
            key, score, reason = item
            parsed[key] = (score, reason)

    def _score(field: str, key: str) -> str:
        if key in parsed and parsed[key][0]:
            return parsed[key][0]
        val = claim.get(field)
        if val is None:
            return ""
        try:
            return f"{float(val):.2f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            return str(val)

    def _reason(key: str, default: str = "") -> str:
        if key in parsed:
            return parsed[key][1] or default
        return default

    sf_s = _score("source_fidelity", "SF")
    sc_s = _score("source_coverage", "SC")
    hr_s = _score("hallucination_rate", "HR")
    sq_s = _score("source_quality", "SQ")

    return format_notes(
        sf=sf_s or None,
        sf_reason=_reason("SF", "AI pre-label"),
        sc=sc_s or None,
        sc_reason=_reason("SC"),
        hr=hr_s or None,
        hr_reason=_reason("HR"),
        sq=sq_s or None,
        sq_reason=_reason("SQ", "AI pre-label"),
        txt=_reason("TXT", "OK").split(":")[0] if _reason("TXT") else "OK",
        txt_reason=":".join(_reason("TXT", "").split(":")[1:]).strip(),
    )


def notes_has_required_keys(notes: str) -> bool:
    """Kiểm tra Notes có đủ key tối thiểu."""
    if not notes:
        return False
    upper = notes.upper()
    return all(k in upper for k in ("SF=", "SC=", "HR=", "SQ=", "TXT="))
