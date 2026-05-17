from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Set
from urllib.parse import urlparse, urlunparse


MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)\s]+)\)")


@dataclass
class SeenUrls:
    urls: Set[str] = field(default_factory=set)
    files_read: int = 0
    warnings: list = field(default_factory=list)


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def extract_markdown_links(text: str) -> Set[str]:
    return {normalize_url(match.group(1)) for match in MARKDOWN_LINK_RE.finditer(text)}


def _report_date(path: Path) -> date:
    return datetime.strptime(path.stem, "%Y-%m-%d").date()


def load_seen_urls(reports_dir: Path, today: date, lookback_days: int = 14) -> SeenUrls:
    result = SeenUrls()
    if not reports_dir.exists():
        return result

    for path in sorted(reports_dir.glob("*.md")):
        try:
            report_date = _report_date(path)
        except ValueError:
            continue
        age_days = (today - report_date).days
        if age_days < 0 or age_days > lookback_days:
            continue
        try:
            result.urls.update(extract_markdown_links(path.read_text(encoding="utf-8")))
            result.files_read += 1
        except OSError as exc:
            result.warnings.append(f"Failed to read history report {path.name}: {exc}")
    return result
