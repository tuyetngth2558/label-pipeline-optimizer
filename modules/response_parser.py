import json
import re

from modules.notes_formatter import normalize_notes_block, notes_has_required_keys
from modules.claim_constraints import (
    apply_prelabel_output,
    enrich_evidence_fields,
    sanitize_claim_urls,
    validate_claim_for_export,
)
from modules.prompt_builder import MODE_PRELABEL, MODE_FULL

# Map normalize fact_check_status — underscore → space, typo fix
_STATUS_NORMALIZE = {
    "XAC_NHAN": "XAC NHAN",
    "MAU_THUAN": "MAU THUAN",
    "KHONG_TIM_THAY": "KHONG TIM THAY",
    "BO_QUA": "BO QUA",
    "XAC NHAN": "XAC NHAN",
    "LECH": "LECH",
    "MAU THUAN": "MAU THUAN",
    "OUTDATED": "OUTDATED",
    "KHONG TIM THAY": "KHONG TIM THAY",
    "BO QUA": "BO QUA",
}


def extract_json(raw: str) -> dict:
    """
    Extract JSON từ Claude response — chịu được text thừa trước/sau.
    Strategy theo thứ tự ưu tiên:
      1. Parse trực tiếp
      2. Lấy từ ```json ... ``` fence
      3. Tìm { bắt đầu object đến } cuối cùng (balanced brace scan)
      4. Greedy regex fallback
    """
    raw = raw.strip()

    # Strategy 1: parse trực tiếp
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 2: code fence ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: balanced brace scan — tìm { đầu tiên rồi đếm brace đến khi balanced
    start = raw.find("{")
    if start != -1:
        depth = 0
        in_string = False
        escape_next = False
        for i, ch in enumerate(raw[start:], start):
            if escape_next:
                escape_next = False
                continue
            if in_string and ch == "\\":
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = raw[start:i+1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break  # nếu không parse được thì thử strategy 4

    # Strategy 4: greedy regex — lấy từ { đầu đến } cuối
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Không parse được JSON từ response Claude.\n"
        f"Raw ({len(raw)} chars, hiện 500 đầu):\n{raw[:500]}"
    )


def normalize_data(data: dict) -> dict:
    """
    Post-process data từ Claude:
    - Normalize fact_check_status (underscore → space)
    - Clean source URLs (remove hallucinated paths nếu cần)
    """
    for claim in data.get("claims", []):
        # Normalize status
        raw_status = str(claim.get("fact_check_status", "")).strip().upper()
        claim["fact_check_status"] = _STATUS_NORMALIZE.get(raw_status, raw_status)

        # Ensure numeric fields are float
        for field in ["source_fidelity", "source_coverage", "hallucination_rate", "source_quality"]:
            val = claim.get(field, 0)
            try:
                claim[field] = float(val)
            except (TypeError, ValueError):
                claim[field] = 0.0

        notes = claim.get("notes", "")
        if notes and not notes_has_required_keys(notes):
            claim["notes"] = normalize_notes_block(notes, claim)
        elif not notes:
            claim["notes"] = normalize_notes_block("", claim)

    # Article level float fields
    art = data.get("article", {})
    for field in ["rel", "comp"]:
        val = art.get(field, 0)
        try:
            art[field] = float(val)
        except (TypeError, ValueError):
            art[field] = 0.0

    return data


def process_claims(
    claims: list,
    mode: str,
    allowed_urls: list[str],
    url_results: list[dict],
    log_fn=print,
) -> list:
    """Áp dụng ràng buộc URL allowlist + pre-label + evidence."""
    processed = []
    for i, raw in enumerate(claims, 1):
        c = sanitize_claim_urls(dict(raw), allowed_urls, log_fn)
        c = enrich_evidence_fields(c, allowed_urls, url_results)
        if mode == MODE_PRELABEL:
            c = apply_prelabel_output(c)
        else:
            c.setdefault("intern_reviewed", "N")
            notes = c.get("notes", "")
            if notes and not notes_has_required_keys(notes):
                c["notes"] = normalize_notes_block(notes, c)
            elif not notes:
                c["notes"] = normalize_notes_block("", c)

        errs = validate_claim_for_export(c, mode, allowed_urls)
        for e in errs:
            log_fn(f"  ⚠ Claim {i}: {e}", "warn")
        processed.append(c)
    return processed


def validate_schema(data: dict) -> bool:
    """Kiểm tra schema tối thiểu theo prompt.md."""
    return "article" in data and "claims" in data
