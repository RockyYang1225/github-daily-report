from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
import re
from typing import Any, Dict, List, Optional

import httpx

from github_daily_report.models import ReportItem, SourceResult


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_github_search(data: Dict[str, Any], source_name: str) -> List[ReportItem]:
    items: List[ReportItem] = []
    for entry in data.get("items", []):
        items.append(
            ReportItem(
                title=entry.get("full_name", entry.get("name", "Untitled repository")),
                url=entry.get("html_url", ""),
                source=source_name,
                category="github",
                summary=entry.get("description") or "",
                published_at=_parse_datetime(entry.get("updated_at")),
                tags=entry.get("topics") or [],
                score_signals={"stars": float(entry.get("stargazers_count") or 0)},
            )
        )
    return items


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _number_from_text(value: str) -> float:
    match = re.search(r"([\d,]+)", value)
    if not match:
        return 0.0
    return float(match.group(1).replace(",", ""))


class _TrendingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items: List[Dict[str, Any]] = []
        self.current: Optional[Dict[str, Any]] = None
        self.capture: Optional[str] = None
        self.buffer: List[str] = []
        self.in_h2 = False

    def handle_starttag(self, tag: str, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "")
        if tag == "article" and "Box-row" in classes:
            self.current = {"stars_text": [], "period_text": []}
        if self.current is None:
            return
        if tag == "h2":
            self.in_h2 = True
        if tag == "a":
            href = attrs_dict.get("href", "")
            if self.in_h2 and href.count("/") >= 2:
                self.current["href"] = href
                self.capture = "title"
                self.buffer = []
            elif href.endswith("/stargazers"):
                self.capture = "stars"
                self.buffer = []
        if tag == "p":
            self.capture = "description"
            self.buffer = []
        if tag == "span" and attrs_dict.get("itemprop") == "programmingLanguage":
            self.capture = "language"
            self.buffer = []
        if tag == "span" and "float-sm-right" in classes:
            self.capture = "period_stars"
            self.buffer = []

    def handle_data(self, data: str):
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag: str):
        if self.current is None:
            return
        if self.capture and tag in {"a", "p", "span"}:
            text = _compact_text("".join(self.buffer))
            if self.capture == "title":
                self.current["title"] = text.replace(" / ", "/")
            elif self.capture == "stars":
                self.current["stars"] = _number_from_text(text)
            elif self.capture == "period_stars":
                self.current["period_stars"] = _number_from_text(text)
            else:
                self.current[self.capture] = text
            self.capture = None
            self.buffer = []
        if tag == "h2":
            self.in_h2 = False
        if tag == "article":
            if self.current.get("title") and self.current.get("href"):
                self.items.append(self.current)
            self.current = None


def parse_github_trending(html: str, period: str) -> List[ReportItem]:
    parser = _TrendingParser()
    parser.feed(html)
    source_name = f"GitHub Trending {period.title()}"
    items: List[ReportItem] = []
    for entry in parser.items:
        href = entry.get("href", "")
        language = entry.get("language")
        tags = [f"trending:{period}"]
        if language:
            tags.insert(0, language)
        items.append(
            ReportItem(
                title=entry.get("title", "Untitled repository"),
                url=f"https://github.com{href}",
                source=source_name,
                category="github",
                summary=entry.get("description", ""),
                published_at=datetime.now(timezone.utc),
                tags=tags,
                score_signals={
                    "stars": float(entry.get("stars") or 0),
                    "period_stars": float(entry.get("period_stars") or 0),
                },
                metadata={"period": period},
            )
        )
    return items


class GitHubSearchSource:
    def __init__(self, query: str, limit: int = 5, source_name: str = "GitHub AI Search"):
        self.query = query
        self.limit = limit
        self.name = source_name

    def fetch(self) -> SourceResult:
        try:
            response = httpx.get(
                "https://api.github.com/search/repositories",
                params={"q": self.query, "sort": "stars", "order": "desc", "per_page": self.limit},
                timeout=20.0,
            )
            response.raise_for_status()
            return SourceResult(source=self.name, items=parse_github_search(response.json(), self.name))
        except Exception as exc:
            return SourceResult(source=self.name, warnings=[f"{self.name} failed: {exc}"], error=str(exc))


class GitHubTrendingSource:
    def __init__(self, period: str = "daily", language: str = "", limit: int = 10):
        self.period = period
        self.language = language.strip("/")
        self.limit = limit
        self.name = f"GitHub Trending {period.title()}"

    def fetch(self) -> SourceResult:
        try:
            path = f"/trending/{self.language}" if self.language else "/trending"
            response = httpx.get(
                f"https://github.com{path}",
                params={"since": self.period},
                timeout=20.0,
                headers={"User-Agent": "github-daily-report"},
            )
            response.raise_for_status()
            return SourceResult(source=self.name, items=parse_github_trending(response.text, self.period)[: self.limit])
        except Exception as exc:
            return SourceResult(source=self.name, warnings=[f"{self.name} failed: {exc}"], error=str(exc))


def fixture_items() -> List[ReportItem]:
    return [
        ReportItem(
            title="acme/agent-kit",
            url="https://github.com/acme/agent-kit",
            source="GitHub Fixture",
            category="github",
            summary="Toolkit for building AI agents",
            published_at=datetime.now(timezone.utc),
            tags=["ai", "agents"],
            score_signals={"stars": 1234},
        )
    ]
