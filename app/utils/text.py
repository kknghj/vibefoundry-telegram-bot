from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {"fbclid", "gclid", "ref", "ref_src"}


def canonicalize_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.startswith("utm_") or key in TRACKING_PARAMS:
            continue
        query.append((key, value))
    path = parsed.path.rstrip("/") or parsed.path
    return urlunparse((parsed.scheme.lower() or "https", netloc, path, "", urlencode(query), ""))


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_key(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^0-9a-zA-Z가-힣]+", "", value).lower()
    return normalized or None


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value or "")


def compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def detect_language(text: str) -> str:
    sample = text or ""
    korean = len(re.findall(r"[가-힣]", sample))
    ascii_letters = len(re.findall(r"[A-Za-z]", sample))
    cjk = len(re.findall(r"[\u4e00-\u9fff]", sample))
    if korean >= 10 and korean >= ascii_letters * 0.2:
        return "ko"
    if cjk >= 10 and cjk > korean:
        return "zh"
    if ascii_letters >= 20:
        return "en"
    return "unknown"
