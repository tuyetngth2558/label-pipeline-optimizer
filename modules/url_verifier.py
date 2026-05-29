"""
url_verifier.py — Fetch URL độc lập (không tin Claude).

Dùng trước khi gửi prompt và khi validate fact_check_source_url.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

try:
    import requests
except ImportError:
    requests = None  # type: ignore

DEFAULT_TIMEOUT = 15
MAX_SNIPPET = 300
INDEX_MAX_CHARS = 800
INDEX_KEYWORDS = (
    "danh mục", "danh muc", "trang chủ", "trang chu", "mục lục",
    "table of contents", "index page", "tất cả văn bản",
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}


def normalize_url(url: str) -> str:
    """Chuẩn hóa URL để so khớp (bỏ fragment, trailing slash)."""
    url = (url or "").strip().rstrip(".,;:")
    if not url:
        return ""
    try:
        p = urlparse(url)
        path = p.path.rstrip("/") or "/"
        return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", p.query, ""))
    except Exception:
        return url.lower()


def url_in_allowlist(url: str, allowed_urls: list[str]) -> bool:
    """URL có trong danh sách Ref (sau normalize) không."""
    if not url or not allowed_urls:
        return False
    nu = normalize_url(url)
    allowed = {normalize_url(u) for u in allowed_urls}
    if nu in allowed:
        return True
    # Khớp cùng host + path prefix (redirect nhẹ)
    for a in allowed:
        if nu.startswith(a) or a.startswith(nu):
            return True
    return False


def _extract_text(html: str) -> str:
  html = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
  html = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", html, flags=re.I)
  text = re.sub(r"<[^>]+>", " ", html)
  text = re.sub(r"\s+", " ", text).strip()
  return text


def _classify_page(text: str, status_code: int) -> str:
    if status_code >= 400 or status_code == 0:
        return "error"
    low = text.lower()
    if len(text) < INDEX_MAX_CHARS:
        return "index"
    if any(kw in low for kw in INDEX_KEYWORDS):
        return "index"
    return "document"


def verify_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """
    Fetch một URL. Trả về:
      url, load_ok, status_code, page_type, text_length, snippet, error
    """
    result = {
        "url": url,
        "load_ok": False,
        "status_code": 0,
        "page_type": "error",
        "text_length": 0,
        "snippet": "",
        "error": "",
    }
    if not url or not url.startswith("http"):
        result["error"] = "URL không hợp lệ"
        return result
    if requests is None:
        result["error"] = "Thiếu thư viện requests (pip install requests)"
        return result

    try:
        resp = requests.get(
            url,
            headers=_HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
        result["status_code"] = resp.status_code
        text = _extract_text(resp.text) if resp.text else ""
        result["text_length"] = len(text)
        result["snippet"] = text[:MAX_SNIPPET]
        result["page_type"] = _classify_page(text, resp.status_code)
        result["load_ok"] = (
            200 <= resp.status_code < 400
            and len(text) > 80
            and result["page_type"] != "error"
        )
        if not result["load_ok"] and not result["error"]:
            result["error"] = f"HTTP {resp.status_code}, type={result['page_type']}"
    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
    except requests.exceptions.RequestException as e:
        result["error"] = str(e)[:120]

    return result


def verify_urls(urls: list[str], timeout: int = DEFAULT_TIMEOUT) -> list[dict]:
    """Verify danh sách URL — giữ thứ tự, dedup."""
    seen: set[str] = set()
    out: list[dict] = []
    for url in urls:
        key = normalize_url(url)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(verify_url(url, timeout=timeout))
    return out


def filter_urls_to_allowlist(urls: list[str], allowed: list[str]) -> list[str]:
    """Chỉ giữ URL có trong Ref list."""
    return [u for u in urls if url_in_allowlist(u, allowed)]


def format_verification_report(results: list[dict]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        flag = "OK" if r.get("load_ok") else "FAIL"
        lines.append(
            f"[{i}] {flag} {r.get('page_type','?')} "
            f"HTTP {r.get('status_code',0)} — {r.get('url','')[:70]}"
        )
        if r.get("error"):
            lines.append(f"     → {r['error']}")
    return "\n".join(lines)
