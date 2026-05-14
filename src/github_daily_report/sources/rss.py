from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional

import feedparser
import httpx

from github_daily_report.models import ReportItem, SourceResult


def _entry_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def parse_rss_feed(xml: str, source_name: str, category: str = "developer-news") -> List[ReportItem]:
    parsed = feedparser.parse(xml)
    items: List[ReportItem] = []
    for entry in parsed.entries:
        items.append(
            ReportItem(
                title=entry.get("title", "Untitled"),
                url=entry.get("link", ""),
                source=source_name,
                category=category,
                summary=entry.get("summary", entry.get("description", "")),
                published_at=_entry_datetime(entry.get("published")),
                tags=[],
                score_signals={"feed": 1.0},
            )
        )
    return items


class RssSource:
    def __init__(self, name: str, url: str, limit: int = 5, category: str = "developer-news"):
        self.name = name
        self.url = url
        self.limit = limit
        self.category = category

    def fetch(self) -> SourceResult:
        try:
            response = httpx.get(self.url, timeout=20.0)
            response.raise_for_status()
            return SourceResult(
                source=self.name,
                items=parse_rss_feed(response.text, self.name, self.category)[: self.limit],
            )
        except Exception as exc:
            return SourceResult(source=self.name, warnings=[f"{self.name} failed: {exc}"], error=str(exc))
